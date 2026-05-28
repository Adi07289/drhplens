"""
agent/nodes/cite_check.py — Deterministic non-LLM cite-check (TRUST-04).

Implements RESEARCH Pattern 3 verbatim:
- NFKC normalize + whitespace collapse + lowercase
- token_set_ratio >= CITE_CHECK_TOKEN_RATIO (rapidfuzz)
- numeric-subset check (PITFALL P2 antibody: wrong numbers → ungrounded)
- span_offsets ±CITE_CHECK_SPAN_TOLERANCE_CHARS window

SKELETON §D invariant: NO LLM client imports anywhere in this module.
Verified by test_no_llm_judge_fallback (inspect.getsource substring check).

DO NOT add any import for openai, genai, instructor, or groq to this file.
"""
from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

from agent.policies import CITE_CHECK_SPAN_TOLERANCE_CHARS, CITE_CHECK_TOKEN_RATIO
from agent.schemas import GroundedAnswer, RefusalResponse
from agent.state import GraphState


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """NFKC normalize → collapse whitespace → lowercase → strip non-word chars.

    Per RESEARCH Pattern 3 lines 470-474. Preserves digits (for numeric check),
    currency symbols, commas, and hyphens that appear in financial text.
    """
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.lower()
    # Keep: word chars, spaces, period, comma, currency, percent, hyphen
    s = re.sub(r"[^\w\s.,₹%\-]", "", s)
    return s


# ---------------------------------------------------------------------------
# Numeric subset check (PITFALL P2 antibody)
# ---------------------------------------------------------------------------


def _extract_numbers(s: str) -> set[str]:
    """Extract all numeric tokens (integers and decimals) from a string.

    Returns a set of normalized numeric strings for subset comparison.
    Strips commas from Indian number formatting (e.g., "11,300" → "11300").
    """
    # Remove commas used as thousand separators before matching
    s_no_commas = re.sub(r"(\d),(\d)", r"\1\2", s)
    return set(re.findall(r"\d+(?:\.\d+)?", s_no_commas))


def _numbers_subset(claim_numbers: set[str], window_numbers: set[str]) -> bool:
    """Return True iff every number in the claim appears in the window.

    If the claim has no numbers, trivially True (non-numeric claims can't fail P2).
    """
    if not claim_numbers:
        return True
    return claim_numbers.issubset(window_numbers)


# ---------------------------------------------------------------------------
# Core cite-check pure function
# ---------------------------------------------------------------------------


def cite_check(
    answer: GroundedAnswer,
    retrieved_chunks: dict[str, str],
) -> tuple[bool, list[str]]:
    """Check every claim in the answer against the cited chunk windows.

    For each claim:
    1. Iterate sources; for each source:
       a. Build window = chunk_text[max(0, start-TOL) : min(len, end+TOL)]
       b. Normalize claim text and window text
       c. Check token_set_ratio >= CITE_CHECK_TOKEN_RATIO
       d. Check claim numbers ⊆ window numbers (PITFALL P2)
    2. First source that passes both checks → claim is grounded.
    3. If no source passes → claim is ungrounded; add to failures.

    Args:
        answer: GroundedAnswer with claims to validate.
        retrieved_chunks: dict mapping chunk_id → chunk_text (from reranked_top_k).

    Returns:
        (all_grounded: bool, failure_reasons: list[str])
    """
    failures: list[str] = []

    for claim in answer.claims:
        grounded = False
        failure_reason: str | None = None

        # Check if any cited chunk_id is in the retrieved set
        has_any_chunk = any(
            src.chunk_id in retrieved_chunks for src in claim.sources
        )
        if not has_any_chunk:
            failures.append(
                f"claim {claim.claim_id!r}: chunk_id not in retrieved set "
                f"(sources: {[s.chunk_id for s in claim.sources]})"
            )
            continue

        for src in claim.sources:
            chunk_text = retrieved_chunks.get(src.chunk_id)
            if chunk_text is None:
                continue  # chunk_id not in retrieved set; try next source

            # Build window with tolerance around span_offsets
            if src.span_offsets is not None:
                start, end = src.span_offsets
            else:
                start, end = 0, len(chunk_text)

            tol = CITE_CHECK_SPAN_TOLERANCE_CHARS
            window_start = max(0, start - tol)
            window_end = min(len(chunk_text), end + tol)
            window = chunk_text[window_start:window_end]

            claim_norm = _normalize(claim.text)
            window_norm = _normalize(window)

            # Fuzzy token overlap check
            ratio = fuzz.token_set_ratio(claim_norm, window_norm)
            if ratio < CITE_CHECK_TOKEN_RATIO:
                failure_reason = (
                    f"claim {claim.claim_id!r}: token_set_ratio={ratio} < "
                    f"{CITE_CHECK_TOKEN_RATIO} (claim={claim.text!r})"
                )
                continue  # Try next source

            # Numeric subset check (PITFALL P2 antibody)
            claim_numbers = _extract_numbers(claim_norm)
            window_numbers = _extract_numbers(window_norm)
            if not _numbers_subset(claim_numbers, window_numbers):
                failure_reason = (
                    f"claim {claim.claim_id!r}: numeric subset failed — "
                    f"claim has {claim_numbers} but window has {window_numbers} "
                    f"(PITFALL P2: number swap detected)"
                )
                continue  # Try next source

            # Both checks passed — claim is grounded
            grounded = True
            break

        if not grounded:
            failures.append(
                failure_reason or f"claim {claim.claim_id!r}: no source passed cite-check"
            )

    all_grounded = len(failures) == 0
    return all_grounded, failures


# ---------------------------------------------------------------------------
# Node entry point
# ---------------------------------------------------------------------------


def run(state: GraphState) -> GraphState:
    """Wrap cite_check() as a LangGraph node.

    Builds retrieved_chunks dict from state["reranked_top_k"], calls cite_check(),
    sets state["all_claims_grounded"] and state["cite_check_failures"].

    If not all grounded, stages a refusal shell (reason="unsupported_claim").
    The message and reformulation_suggestions are filled by refuse_with_reformulation
    (Task 4), which has access to relaxed retrieval data.

    Args:
        state: GraphState with grounded_answer and reranked_top_k.

    Returns:
        Updated GraphState with all_claims_grounded, cite_check_failures, and
        optionally refusal.
    """
    grounded_answer = state.get("grounded_answer")
    if grounded_answer is None:
        # No answer to check (refusal already set upstream)
        return {**state, "all_claims_grounded": False, "cite_check_failures": []}

    # Build chunk_id → chunk_text map from reranked_top_k
    retrieved_chunks: dict[str, str] = {}
    for chunk in state.get("reranked_top_k", []):
        payload = chunk.get("payload", {})
        chunk_id = payload.get("chunk_id", chunk.get("id", ""))
        chunk_text = payload.get("chunk_text", "")
        if chunk_id:
            retrieved_chunks[chunk_id] = chunk_text

    all_grounded, failures = cite_check(grounded_answer, retrieved_chunks)

    updated = {
        **state,
        "all_claims_grounded": all_grounded,
        "cite_check_failures": failures,
    }

    if not all_grounded:
        updated["refusal"] = RefusalResponse(
            reason="unsupported_claim",
            explanation="",  # filled by refuse_with_reformulation
            reformulation_suggestions=[],  # filled by refuse_with_reformulation
        )

    return updated
