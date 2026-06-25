"""
Unit test — RedFlagRecord round-trips with the {"refusal": ...} discriminator;
locks the 7-key allow-list; refusal fields carry no confidence (D3-03).

Requirement: EXTRACT-01. This is the Phase 3 INTERFACE GATE — it asserts against
Task 1's real schema NOW (no skip). Downstream plans build against this contract.
"""
from __future__ import annotations

import pytest

from agent.redflag_schema import (
    REDFLAG_FIELD_KEYS,
    RankedRisk,
    RedFlagField,
    RedFlagRecord,
)
from agent.schemas import (
    Claim,
    GroundedAnswer,
    RefusalResponse,
    RetrievedChunkRef,
)


def _grounded_answer(claim_id: str = "c_rpt001") -> GroundedAnswer:
    """A minimal valid cited GroundedAnswer (self-contained — this unit test does
    not depend on the eval-scoped synthetic_redflag_record fixture)."""
    span = "Related-party transactions were ₹120 crore, 3.4% of revenue"
    source = RetrievedChunkRef(
        chunk_id="chunk_rpt_001",
        page_start=212,
        page_end=212,
        printed_page_label="212",
        section="Related Party Transactions",
        score=0.88,
        verbatim_span=span,
        span_offsets=(0, len(span)),
    )
    claim = Claim(
        claim_id=claim_id,
        text="Related-party transactions were 3.4% of revenue",
        source_chunk_id="chunk_rpt_001",
        drhp_page=212,
        section="Related Party Transactions",
        verbatim_span=span,
        span_offsets=(0, len(span)),
        sources=[source],
    )
    return GroundedAnswer(
        answer_prose=f"Related-party transactions were 3.4% of revenue {{{{{claim_id}}}}}.",
        claims=[claim],
        sub_question_addressed=[],
        sub_question_unaddressed=[],
    )


def _record() -> RedFlagRecord:
    return RedFlagRecord(
        drhp_id="synthetic_2026_01",
        computed_at="2026-06-25T00:00:00Z",
        fields={
            "rpt_pct": RedFlagField(
                value=_grounded_answer("c_rpt001"),
                confidence_tier="high",
                confidence_score=0.9,
            ),
            "promoter_pledge_pct": RedFlagField(
                value=RefusalResponse(
                    reason="unsupported_claim",
                    explanation="Not disclosed in DRHP",
                ),
                confidence_tier=None,
                confidence_score=None,
            ),
        },
        ranked_risks=[
            RankedRisk(
                claim_id="c_risk01",
                idf_score=4.7,
                specificity_band="issuer_specific",
            ),
            RankedRisk(
                claim_id="c_risk02",
                idf_score=0.6,
                specificity_band="industry_standard",
            ),
        ],
    )


def test_redflag_record_roundtrip() -> None:
    """A RedFlagRecord with a GroundedAnswer field and a RefusalResponse field
    survives from_json(to_json()) with the union reconstructed correctly."""
    rec = _record()
    restored = RedFlagRecord.from_json(rec.to_json())

    assert restored.drhp_id == rec.drhp_id
    assert set(restored.fields) == set(rec.fields)

    grounded = restored.fields["rpt_pct"]
    assert isinstance(grounded.value, GroundedAnswer)
    assert grounded.value.claims[0].claim_id == "c_rpt001"
    assert grounded.confidence_tier == "high"
    assert grounded.confidence_score == 0.9

    refusal = restored.fields["promoter_pledge_pct"]
    assert isinstance(refusal.value, RefusalResponse)
    assert refusal.value.explanation == "Not disclosed in DRHP"

    # ranked_risks survive in descending idf order
    assert [r.claim_id for r in restored.ranked_risks] == ["c_risk01", "c_risk02"]
    assert isinstance(restored.ranked_risks[0], RankedRisk)
    assert restored.ranked_risks[0].specificity_band == "issuer_specific"


def test_unknown_field_key_rejected() -> None:
    """RedFlagRecord with a key outside the locked 7-key allow-list raises."""
    with pytest.raises(ValueError):
        RedFlagRecord(
            drhp_id="x",
            computed_at="t",
            fields={
                "bogus_key": RedFlagField(
                    value=RefusalResponse(
                        reason="unsupported_claim", explanation="nd"
                    )
                )
            },
        )

    # the allow-list is exactly the 7 canonical keys
    assert REDFLAG_FIELD_KEYS == {
        "rpt_pct",
        "ofs_vs_fresh",
        "promoter_pledge_pct",
        "customer_concentration",
        "auditor_history",
        "debt_trajectory",
        "going_concern",
    }


def test_refusal_field_has_no_confidence() -> None:
    """A not-disclosed (RefusalResponse) field carries no confidence tier/score
    (D3-03: absence is honest signal, never conflated with low-confidence)."""
    refusal_field = _record().fields["promoter_pledge_pct"]
    assert isinstance(refusal_field.value, RefusalResponse)
    assert refusal_field.confidence_tier is None
    assert refusal_field.confidence_score is None
