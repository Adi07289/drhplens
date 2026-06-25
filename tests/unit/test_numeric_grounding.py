"""
Unit test — per-number source-grounding (D3-10): lakh/crore reconciliation,
rupee-symbol tolerance, and blocking of an ungrounded number. Extends the
non-LLM cite_check numeric antibody.

Requirement: EVAL-03. Plan 02 extends agent/nodes/cite_check.py
(_numbers_subset gains unit normalization + NUMERIC_GROUNDING_REL_TOLERANCE).
Function names are LOCKED.
"""
from __future__ import annotations

from agent.nodes.cite_check import cite_check
from agent.schemas import Claim, GroundedAnswer, RetrievedChunkRef


def _make_claim(
    text: str,
    claim_id: str = "c_num001",
    chunk_id: str = "chunk_001",
    span_offsets: tuple[int, int] = (0, 200),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        text=text,
        source_chunk_id=chunk_id,
        drhp_page=42,
        section="Issue Details",
        verbatim_span=text,
        span_offsets=span_offsets,
        sources=[
            RetrievedChunkRef(
                chunk_id=chunk_id,
                page_start=42,
                page_end=42,
                section="Issue Details",
                span_offsets=span_offsets,
            )
        ],
    )


def _answer(claim: Claim) -> GroundedAnswer:
    prose = f"{claim.text} {{{{{claim.claim_id}}}}}"
    return GroundedAnswer(answer_prose=prose, claims=[claim])


def test_lakh_crore_reconciles() -> None:
    """'₹11,247 crore' grounds against '1,12,470 lakh' after unit normalization.

    11,247 crore = 1,12,470 lakh (11247e7 == 112470e5). The exact-string subset
    check would false-fail; unit reconciliation within tolerance must ground it.
    """
    claim = _make_claim("Revenue from operations was ₹11,247 crore in FY2024")
    retrieved = {
        "chunk_001": "Revenue from operations was 1,12,470 lakh in FY2024."
    }
    all_grounded, failures = cite_check(_answer(claim), retrieved)
    assert all_grounded is True, failures
    assert failures == []


def test_rupee_symbol_tolerance() -> None:
    """A rupee-symbol/format variant of the same number still grounds.

    '₹11,247 crore' vs a window writing the same magnitude as '11247.0 crore'
    (decimal + symbol formatting, plus a within-tolerance rounding) grounds.
    """
    claim = _make_claim("The fresh issue is ₹4,499 crore")
    retrieved = {"chunk_001": "The fresh issue is 4499.0 crore as disclosed."}
    all_grounded, failures = cite_check(_answer(claim), retrieved)
    assert all_grounded is True, failures

    # And a genuinely different magnitude (beyond tolerance) must NOT ground.
    claim_far = _make_claim(
        "The fresh issue is ₹4,499 crore", claim_id="c_num002"
    )
    retrieved_far = {"chunk_001": "The fresh issue is 9500 crore as disclosed."}
    far_grounded, far_failures = cite_check(_answer(claim_far), retrieved_far)
    assert far_grounded is False
    assert any("c_num002" in f for f in far_failures)


def test_ungrounded_number_blocked() -> None:
    """A number with no matching cited-span source fails the grounding check.

    The claim asserts a magnitude that reconciles at NO unit scale within
    tolerance against any window number -> ungrounded -> blockable (T-03-03).
    """
    claim = _make_claim(
        "Promoter pledge stands at 73 percent of holding", claim_id="c_num003"
    )
    # Window shares enough tokens to pass the fuzzy gate, but its only number (12)
    # reconciles with the claim's 73 at NO unit scale within tolerance.
    retrieved = {
        "chunk_001": "Promoter pledge stands at 12 percent of holding currently."
    }
    all_grounded, failures = cite_check(_answer(claim), retrieved)
    assert all_grounded is False
    assert any("c_num003" in f for f in failures)
