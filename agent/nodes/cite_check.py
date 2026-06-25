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

from agent.policies import (
    CITE_CHECK_SPAN_TOLERANCE_CHARS,
    CITE_CHECK_TOKEN_RATIO,
    NUMERIC_GROUNDING_REL_TOLERANCE,
)
from agent.schemas import GroundedAnswer, RefusalResponse
from agent.state import GraphState
from app.observability.cite_check_metric import score_cite_check
from app.observability.trace_decorators import attach_claim_ids_to_span


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


# Indian/international magnitude words → multiplier (D3-10 unit reconciliation).
# Matched as whole tokens immediately following an extracted number so
# "₹11,247 crore" canonicalizes to 1.1247e11 and reconciles with "1,12,470 lakh"
# (1.1247e11) instead of false-failing the exact-string subset check.
_UNIT_SCALES: dict[str, float] = {
    "lakh": 1e5,
    "lakhs": 1e5,
    "lac": 1e5,
    "lacs": 1e5,
    "crore": 1e7,
    "crores": 1e7,
    "cr": 1e7,
    "million": 1e6,
    "mn": 1e6,
    "billion": 1e9,
    "bn": 1e9,
}

# A number optionally preceded by ₹, optionally followed by a magnitude word.
# Operates on _normalize()d text (lowercase; commas already collapsible).
_SCALED_NUMBER_RE = re.compile(
    r"₹?\s*(\d+(?:\.\d+)?)\s*"
    r"(lakhs?|lacs?|crores?|cr|million|mn|billion|bn|%)?",
    re.IGNORECASE,
)


def _extract_scaled_numbers(s: str) -> list[float]:
    """Extract numbers as CANONICAL float magnitudes, honouring adjacent units.

    Strips Indian thousands commas (mirroring `_extract_numbers`), then maps each
    number to its magnitude using a neighbouring lakh/crore/million/billion token
    (or ₹/% markers, which carry no scale). Returns a list (not a set) so repeated
    values still participate in reconciliation. This is the unit-aware sibling of
    `_extract_numbers`; both share the same comma-stripping normalization path.
    """
    s_no_commas = re.sub(r"(\d),(\d)", r"\1\2", s)
    magnitudes: list[float] = []
    for match in _SCALED_NUMBER_RE.finditer(s_no_commas):
        raw = match.group(1)
        if raw is None:
            continue
        value = float(raw)
        unit = (match.group(2) or "").lower()
        scale = _UNIT_SCALES.get(unit, 1.0)  # ₹/%/no-unit → ×1
        magnitudes.append(value * scale)
    return magnitudes


def _number_reconciles(claim_val: float, window_val: float) -> bool:
    """True iff two canonical magnitudes match within the policy rel-tolerance.

    abs(claim - window) / max(window, 1) <= NUMERIC_GROUNDING_REL_TOLERANCE.
    The max(window, 1) floor mirrors the policy docstring and avoids a divide-by-
    zero when a disclosed figure is exactly 0.
    """
    return abs(claim_val - window_val) / max(abs(window_val), 1.0) <= (
        NUMERIC_GROUNDING_REL_TOLERANCE
    )


def _numbers_subset(claim_numbers: set[str], window_numbers: set[str]) -> bool:
    """Return True iff every number in the claim appears in the window.

    Fast path: exact-string subset (preserves existing green cite-check behavior,
    no regression). This is intentionally a backward-compatible signature; the
    unit-aware + tolerance reconciliation lives in `_scaled_numbers_grounded`,
    which the cite_check loop calls when the exact-string check fails.

    If the claim has no numbers, trivially True (non-numeric claims can't fail P2).
    """
    if not claim_numbers:
        return True
    return claim_numbers.issubset(window_numbers)


def _scaled_numbers_grounded(
    claim_norm: str, window_norm: str
) -> bool:
    """Per-number unit-aware + tolerance grounding over normalized texts (D3-10).

    Each canonical claim magnitude must reconcile (same OR a reconcilable unit
    scale, within NUMERIC_GROUNDING_REL_TOLERANCE) with SOME canonical window
    magnitude. A claim with no numbers is trivially grounded. A claim whose every
    emitted number fails reconciliation is ungrounded → downstream blocks it as a
    RefusalResponse (T-03-03).
    """
    claim_mags = _extract_scaled_numbers(claim_norm)
    if not claim_mags:
        return True
    window_mags = _extract_scaled_numbers(window_norm)
    return all(
        any(_number_reconciles(c, w) for w in window_mags) for c in claim_mags
    )


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

            # Numeric grounding (PITFALL P2 antibody + D3-10 unit reconciliation).
            # Fast path: exact-string subset short-circuits to grounded (no
            # regression to existing cite-check tests). Slow path: per-number
            # unit-aware + tolerance reconciliation so "₹11,247 crore" grounds
            # against "1,12,470 lakh" instead of false-failing the 0.95 gate.
            claim_numbers = _extract_numbers(claim_norm)
            window_numbers = _extract_numbers(window_norm)
            if not _numbers_subset(claim_numbers, window_numbers) and not (
                _scaled_numbers_grounded(claim_norm, window_norm)
            ):
                failure_reason = (
                    f"claim {claim.claim_id!r}: numeric grounding failed — "
                    f"claim has {claim_numbers} but window has {window_numbers}; "
                    f"no unit-reconcilable match within tolerance "
                    f"(PITFALL P2 / D3-10)"
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

    # Attach claim_ids to cite_check span (idempotent — ensures span carries them
    # even if generate's span lost context; Phase 3 METHOD-01 consumer contract).
    attach_claim_ids_to_span([c.claim_id for c in grounded_answer.claims])

    # Log faithfulness_via_cite_check custom score to Langfuse.
    per_claim_results = [
        {"claim_id": c.claim_id, "grounded": c.claim_id not in " ".join(failures)}
        for c in grounded_answer.claims
    ]
    trace_id = state.get("langfuse_trace_id", "")
    score_cite_check(
        trace_id=trace_id,
        all_grounded=all_grounded,
        per_claim_results=per_claim_results,
    )

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
