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
    """A value that is a numeric transformation of source numbers (reconcilable
    in magnitude but not a verbatim digit-string) classifies as medium."""
    # Claim writes "4,499 crore"; the span states the SAME magnitude as
    # "44,990 million" (4499 crore == 44990 million == 4.499e10). The digit
    # string "4499" is NOT verbatim in the span, but the magnitude reconciles.
    span = "The fresh issue component is 44,990 million as disclosed."
    claim = _claim(
        text="The fresh issue is 4,499 crore",
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
