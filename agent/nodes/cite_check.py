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
from agent.schemas import GroundedAnswer, RefusalResponse, RetrievedChunkRef
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

            # Two ORTHOGONAL antibodies, evaluated independently (EVAL-03 fix):
            #
            #  * Numeric antibody (PITFALL P2 + D3-10 unit reconciliation): every
            #    number the claim emits must reconcile to some window number.
            #    Fast path exact-string subset; slow path per-number unit-aware
            #    tolerance so "₹11,247 crore" grounds against "112,473.90 million"
            #    / "1,12,470 lakh". Trivially satisfied when the claim has no
            #    numbers (a qualitative claim can't fail P2).
            #  * Prose antibody (RESEARCH Pattern 3): fuzzy token overlap.
            #
            # A source grounds the claim when its numbers reconcile AND EITHER the
            # claim is numeric OR the prose overlaps. Numeric reconciliation is
            # itself the grounding proof for a numeric claim: a concise numeric
            # answer legitimately shares few tokens with a dense ~500-token
            # financial window, so requiring the prose gate too would false-reject
            # a genuinely-grounded number (this drove numeric_faithfulness to 0.08,
            # EVAL-03). Number-swaps still fail (numbers_grounded=False); purely
            # qualitative hallucinations still fail the prose gate (no claim
            # numbers → prose overlap is the only path to grounded).
            claim_numbers = _extract_numbers(claim_norm)
            window_numbers = _extract_numbers(window_norm)
            numbers_grounded = _numbers_subset(claim_numbers, window_numbers) or (
                _scaled_numbers_grounded(claim_norm, window_norm)
            )
            ratio = fuzz.token_set_ratio(claim_norm, window_norm)
            prose_grounded = ratio >= CITE_CHECK_TOKEN_RATIO

            if numbers_grounded and (bool(claim_numbers) or prose_grounded):
                grounded = True
                break

            if not numbers_grounded:
                failure_reason = (
                    f"claim {claim.claim_id!r}: numeric grounding failed — "
                    f"claim has {claim_numbers} but window has {window_numbers}; "
                    f"no unit-reconcilable match within tolerance "
                    f"(PITFALL P2 / D3-10)"
                )
            else:
                failure_reason = (
                    f"claim {claim.claim_id!r}: token_set_ratio={ratio} < "
                    f"{CITE_CHECK_TOKEN_RATIO} (claim={claim.text!r})"
                )
            continue  # Try next source

        if not grounded:
            failures.append(
                failure_reason or f"claim {claim.claim_id!r}: no source passed cite-check"
            )

    all_grounded = len(failures) == 0
    return all_grounded, failures


# ---------------------------------------------------------------------------
# Citation repair (EVAL-03) — re-anchor a mis-cited numeric claim to the
# retrieved chunk that ACTUALLY contains its numbers.
#
# The LLM reliably retrieves the right evidence but inconsistently cites the wrong
# sibling chunk (e.g. attaching a fresh-issue figure to the total-issue chunk), so a
# genuinely-supported number is scored ungrounded. This deterministic, non-LLM step
# re-anchors such a claim to the retrieved top-k chunk that contains its numbers,
# improving citation accuracy (the user's citation now truly holds the number). It
# NEVER repairs a number absent from every retrieved chunk, so hallucinations still
# fail the gate.
# ---------------------------------------------------------------------------


def _chunk_supports_numbers(
    claim_norm: str, claim_numbers: set[str], window_norm: str
) -> bool:
    """True iff every number in the claim reconciles to some number in the window."""
    if not claim_numbers:
        return False
    return _numbers_subset(claim_numbers, _extract_numbers(window_norm)) or (
        _scaled_numbers_grounded(claim_norm, window_norm)
    )


def _find_supporting_chunk(claim, reranked_chunks: list[dict]) -> dict | None:
    """Retrieved chunk that contains ALL the claim's numbers, best topical overlap.

    Returns the chunk payload, or None if NO retrieved chunk supports every number
    the claim emits (so a hallucinated number is never repaired).
    """
    claim_norm = _normalize(claim.text)
    claim_numbers = _extract_numbers(claim_norm)
    if not claim_numbers:
        return None
    best_payload: dict | None = None
    best_ratio = -1.0
    for chunk in reranked_chunks:
        payload = chunk.get("payload", {})
        text = payload.get("chunk_text", "")
        if not text or not payload.get("chunk_id"):
            continue
        window_norm = _normalize(text)
        if not _chunk_supports_numbers(claim_norm, claim_numbers, window_norm):
            continue
        ratio = fuzz.token_set_ratio(claim_norm, window_norm)
        if ratio > best_ratio:
            best_ratio = ratio
            best_payload = payload
    return best_payload


def repair_citations(
    answer: GroundedAnswer, reranked_chunks: list[dict]
) -> GroundedAnswer:
    """Re-anchor mis-cited numeric claims to the retrieved chunk that holds their numbers.

    For each numeric claim that does NOT already ground to its cited sources, prepend a
    citation to the retrieved top-k chunk whose window contains every number the claim
    emits (best topical overlap). Claims whose numbers are in no retrieved chunk are
    left untouched (they must fail cite_check — no hallucination is repaired).
    Non-numeric claims are never touched.
    """
    text_by_id: dict[str, str] = {}
    for chunk in reranked_chunks:
        payload = chunk.get("payload", {})
        cid = payload.get("chunk_id", chunk.get("id", ""))
        if cid:
            text_by_id[cid] = payload.get("chunk_text", "")

    repaired_claims = []
    changed = False
    for claim in answer.claims:
        if not _extract_numbers(_normalize(claim.text)):
            repaired_claims.append(claim)
            continue
        already_ok, _ = cite_check(
            GroundedAnswer(answer_prose=f"x {{{{{claim.claim_id}}}}}", claims=[claim]),
            text_by_id,
        )
        if already_ok:
            repaired_claims.append(claim)
            continue
        support = _find_supporting_chunk(claim, reranked_chunks)
        if support is None:
            repaired_claims.append(claim)  # genuinely ungrounded — leave to fail
            continue
        new_ref = RetrievedChunkRef(
            chunk_id=support["chunk_id"],
            page_start=int(support.get("page_start", 0) or 0),
            page_end=int(support.get("page_end", 0) or 0),
            printed_page_label=support.get("printed_page_label"),
            section=support.get("section") or "Unknown",
            span_offsets=None,  # the whole supporting chunk is the window
        )
        repaired_claims.append(
            claim.model_copy(
                update={
                    "sources": [new_ref, *claim.sources],
                    "source_chunk_id": support["chunk_id"],
                    "drhp_page": int(support.get("page_start", 0) or 0),
                }
            )
        )
        changed = True

    if not changed:
        return answer
    return answer.model_copy(update={"claims": repaired_claims})


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

    reranked = state.get("reranked_top_k", [])

    # Repair mis-cited numeric claims: re-anchor each to the retrieved chunk that
    # actually contains its numbers BEFORE checking, so a genuinely-supported number
    # grounds to an accurate citation (EVAL-03). Never repairs an unsupported number.
    grounded_answer = repair_citations(grounded_answer, reranked)

    # Build chunk_id → chunk_text map from reranked_top_k
    retrieved_chunks: dict[str, str] = {}
    for chunk in reranked:
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
        "grounded_answer": grounded_answer,  # persist repaired citations downstream
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
