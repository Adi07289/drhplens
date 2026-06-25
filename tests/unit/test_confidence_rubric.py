"""
Unit test — the deterministic confidence rubric (D3-01): verbatim -> high,
light parse/aggregation -> medium, cross-section inference -> low, absence ->
no tier.

Requirement: EXTRACT-02. Plan 02 implements pipelines/confidence.py
(classify_confidence + a RefusalResponse-aware wrapper). Function names are LOCKED.
"""
from __future__ import annotations

from agent.schemas import Claim, GroundedAnswer, RefusalResponse, RetrievedChunkRef
from pipelines.confidence import classify_confidence, confidence_for_field


def _source(
    chunk_id: str = "chunk_001",
    section: str = "Issue Details",
    verbatim_span: str = "",
) -> RetrievedChunkRef:
    return RetrievedChunkRef(
        chunk_id=chunk_id,
        page_start=1,
        page_end=1,
        section=section,
        verbatim_span=verbatim_span or None,
    )


def _claim(
    text: str,
    verbatim_span: str,
    sources: list[RetrievedChunkRef],
    claim_id: str = "c_conf01",
) -> Claim:
    return Claim(
        claim_id=claim_id,
        text=text,
        source_chunk_id=sources[0].chunk_id,
        drhp_page=1,
        section=sources[0].section,
        verbatim_span=verbatim_span,
        span_offsets=(0, len(verbatim_span)),
        sources=sources,
    )


def _answer(claim: Claim) -> GroundedAnswer:
    return GroundedAnswer(
        answer_prose=f"{claim.text} {{{{{claim.claim_id}}}}}", claims=[claim]
    )


def test_verbatim_is_high() -> None:
    """A value stated verbatim in the cited span classifies as high."""
    span = "The offer for sale comprises 4,499 crore of equity shares."
    claim = _claim(
        text="The OFS is 4,499 crore",
        verbatim_span=span,
        sources=[_source(verbatim_span=span)],
    )
    tier, score = classify_confidence(_answer(claim))
    assert tier == "high"
    assert 0.0 <= score <= 1.0


def test_light_parse_is_medium() -> None:
    """A value that is a numeric transformation/aggregation of source numbers
    (reconcilable but not a verbatim substring) classifies as medium."""
    # The emitted value 4499 reconciles with the source's 4499 crore magnitude,
    # but the emitted string "44.99%" does not appear verbatim in the span.
    span = "Fresh issue is 4,499 crore out of a total issue size of 10,000 crore."
    claim = _claim(
        text="Related-party transactions are 44.99% of total",
        verbatim_span=span,
        sources=[_source(verbatim_span=span)],
    )
    tier, score = classify_confidence(_answer(claim))
    assert tier == "medium"
    assert 0.0 <= score <= 1.0


def test_cross_section_is_low() -> None:
    """Support spanning multiple sources with different .section values
    classifies as low."""
    claim = _claim(
        text="Debt rose while revenue grew",
        verbatim_span="An inference drawn across two sections of the prospectus.",
        sources=[
            _source(chunk_id="chunk_a", section="Financial Statements"),
            _source(chunk_id="chunk_b", section="Risk Factors"),
        ],
    )
    tier, score = classify_confidence(_answer(claim))
    assert tier == "low"
    assert 0.0 <= score <= 1.0


def test_absence_has_no_tier() -> None:
    """A not-disclosed (RefusalResponse) field carries no confidence tier (D3-03)."""
    refusal = RefusalResponse(
        reason="unsupported_claim",
        explanation="Not disclosed in DRHP",
    )
    tier, score = confidence_for_field(refusal)
    assert tier is None
    assert score is None
