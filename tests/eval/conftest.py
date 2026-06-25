"""
tests/eval/conftest.py — shared Phase 3 fixtures (LOCKED at Wave 0, 03-01-PLAN Task 2).

Fixture names and signatures are LOCKED — downstream Phase 3 plans (02-06) import
these names directly; renaming causes collection failures. Bodies are filled NOW
because each only needs Task 1's RedFlagRecord schema + stdlib.

Fixtures:
- synthetic_redflag_record: a RedFlagRecord with >=1 GroundedAnswer field,
  >=1 RefusalResponse field, and >=2 RankedRisk items — round-trips through
  to_json/from_json. Used by schema + precompute + methodology-pane tests.
- tiny_extraction_labels: a small in-memory list of label dicts covering one
  numeric, one boolean, one set field, and one not-disclosed field. Used by the
  extraction-F1 eval tests (Plan 04).
- idf_corpus_3doc: 3 fake risk-section strings — 2 share a boilerplate phrase,
  1 is unique. Used by the risk-IDF tests (Plan 03).
"""
from __future__ import annotations

import pytest

from agent.redflag_schema import RankedRisk, RedFlagField, RedFlagRecord
from agent.schemas import (
    Claim,
    GroundedAnswer,
    RefusalResponse,
    RetrievedChunkRef,
)


def _grounded_answer(claim_id: str = "c_rpt001") -> GroundedAnswer:
    """A minimal but valid cited GroundedAnswer for a numeric red-flag field."""
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


@pytest.fixture
def synthetic_redflag_record() -> RedFlagRecord:
    """A RedFlagRecord with one GroundedAnswer field (rpt_pct, tier=high),
    one RefusalResponse field (promoter_pledge_pct, not-disclosed, no tier),
    and two RankedRisk items ordered by descending idf_score.

    Shape:
        RedFlagRecord(
          drhp_id, computed_at,
          fields={
            "rpt_pct": RedFlagField(value=GroundedAnswer, confidence_tier="high",
                                    confidence_score=0.9),
            "promoter_pledge_pct": RedFlagField(value=RefusalResponse,
                                                confidence_tier=None,
                                                confidence_score=None),
          },
          ranked_risks=[RankedRisk(issuer_specific), RankedRisk(industry_standard)],
        )
    """
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


@pytest.fixture
def tiny_extraction_labels() -> list[dict]:
    """A tiny in-memory gold-label list covering one of each scored field type.

    Each dict: {drhp_id, field, field_type, gold, confidence_bucket}. The
    not-disclosed row carries gold=None with field_type "boolean" absence,
    exercising D3-03 (a refusal where gold says absent is correct, not dropped).
    """
    return [
        {
            "drhp_id": "synthetic_2026_01",
            "field": "rpt_pct",
            "field_type": "numeric",
            "gold": 3.4,
            "confidence_bucket": "high",
        },
        {
            "drhp_id": "synthetic_2026_01",
            "field": "going_concern",
            "field_type": "boolean",
            "gold": False,
            "confidence_bucket": "high",
        },
        {
            "drhp_id": "synthetic_2026_01",
            "field": "customer_concentration",
            "field_type": "set",
            "gold": ["Customer A", "Customer B"],
            "confidence_bucket": "medium",
        },
        {
            "drhp_id": "synthetic_2026_01",
            "field": "promoter_pledge_pct",
            "field_type": "numeric",
            "gold": None,  # not disclosed — refusal expected, scored not dropped
            "confidence_bucket": None,
        },
    ]


@pytest.fixture
def idf_corpus_3doc() -> list[str]:
    """Three fake risk-section strings for in-corpus IDF tests.

    Docs 0 and 1 share a boilerplate phrase ("our business is subject to
    extensive government regulation"); doc 2 is issuer-unique. A term appearing
    in 2 of 3 docs has lower IDF than the unique term in doc 2.
    """
    boilerplate = "Our business is subject to extensive government regulation."
    return [
        f"{boilerplate} We may be unable to obtain or renew required licences.",
        f"{boilerplate} Changes in tax law could adversely affect operations.",
        (
            "A single anchor customer accounted for 62% of fiscal 2024 revenue, "
            "and the loss of this customer would materially harm our business."
        ),
    ]
