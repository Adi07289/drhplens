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


# ===========================================================================
# Phase 6.3 (06.3-04) — shared deterministic fakes for the OFFLINE stress suite (D-09)
#
# These power tests/eval/test_stress_suite.py: it stubs the two LLM hops (classify +
# synthesize) with these per-fixture builders so every gated assertion is pure Python —
# fast, free, reproducible, asserting on the FINAL validated supervisor state, never a
# live LLM. The builders construct their schema objects LAZILY (import inside the body)
# so conftest import never hard-fails; the whole stress module importorskips until
# agent/supervisor.py lands (Wave 3), then auto-activates.
# ===========================================================================

_STRESS_ALLOWED_TOOLS = frozenset(
    {"drhp_rag", "query_peers", "query_forecast", "query_redflags"}
)


@pytest.fixture
def fake_routing():
    """Return a builder ``fake_routing(case) -> RoutingDecision`` driven by the fixture category.

    Category → routing (D-05/D-07):
      - compliance_bait      → is_advice_seeking=True,  tools=[]  → educational refusal (D-07a)
      - jailbreak / offtopic → is_out_of_scope=True,    tools=[]  → graceful refusal (D-07b/c)
      - cross_ipo redirect   → is_out_of_scope=True,    tools=[]  → single-IPO redirect (D-07d)
      - cross_ipo fabricated_precision → tools=["drhp_rag"] (answers the single IPO; the
        'not disclosed' honesty is the synthesis node's job — no fabricated precision)
      - partial_and_provenance → the row's relevant tool set (clamped to the allow-list)

    RoutingDecision is imported lazily (Plan 01 landed it in agent/nodes/classify.py).
    """

    def _build(case: dict):
        from agent.nodes.classify import RoutingDecision  # lazy: no hard-fail at conftest import

        category = case["category"]
        if category == "compliance_bait":
            return RoutingDecision(tools=[], is_advice_seeking=True, is_out_of_scope=False)
        if category in ("jailbreak", "offtopic"):
            return RoutingDecision(tools=[], is_advice_seeking=False, is_out_of_scope=True)
        if category == "cross_ipo":
            if case.get("mode") == "fabricated_precision":
                return RoutingDecision(
                    tools=["drhp_rag"], is_advice_seeking=False, is_out_of_scope=False
                )
            return RoutingDecision(tools=[], is_advice_seeking=False, is_out_of_scope=True)
        if category == "partial_and_provenance":
            proposed = [t for t in case.get("tools", ["drhp_rag"]) if t in _STRESS_ALLOWED_TOOLS]
            return RoutingDecision(
                tools=proposed, is_advice_seeking=False, is_out_of_scope=False
            )
        return RoutingDecision(tools=[], is_advice_seeking=False, is_out_of_scope=True)

    return _build


@pytest.fixture
def fake_fuse():
    """Return a builder ``fake_fuse(case) -> FusedAnswer`` — scrubber-clean, no fabricated numbers.

    The fused prose DESCRIBES context and never concludes (posture, D-07a). A provenance case
    attaches a ToolClaim whose ``source_record_id`` traces to a committed ``data/*.json`` record
    (D-03). An ``expect_partial`` case carries ``is_partial=True`` + an unaddressed flag (D-08).

    FusedAnswer / ToolClaim are imported lazily (Plan 01 landed them in agent/schemas.py).
    """

    def _build(case: dict):
        from agent.schemas import FusedAnswer, ToolClaim  # lazy: no hard-fail at conftest import

        category = case["category"]
        expect_partial = bool(case.get("expect_partial"))
        claims: list = []
        prose = (
            "Here is what the prospectus discloses and how comparable IPOs have behaved, "
            "for your own assessment."
        )
        if category == "partial_and_provenance" and not expect_partial:
            drhp_id = case["drhp_id"]
            claims = [
                ToolClaim(
                    claim_id="c_prov01",
                    text="peer revenue multiple",
                    value="see source record",
                    source_tool="query_peers",
                    source_record_id=f"data/peers/{drhp_id}.json#revenue_multiple",
                )
            ]
            prose = (
                "The peer and forecast context are summarized here {{c_prov01}}, "
                "each number traced to its source record."
            )
        unaddressed = ["ran out of steps before finishing"] if expect_partial else []
        return FusedAnswer(
            answer_prose=prose,
            claims=claims,
            is_partial=expect_partial,
            unaddressed=unaddressed,
        )

    return _build


@pytest.fixture
def budget_trip(monkeypatch):
    """Return ``budget_trip()`` — forces the P8 counter over budget → route() halts (D-06/D-08).

    The three bounds (MAX_SUPERVISOR_HOPS / MAX_TOOL_CALLS) are imported by value into
    agent/supervisor at module load, so the injector patches them AS BOUND ON THE SUPERVISOR
    MODULE. ``raising=False`` no-ops safely while agent/supervisor.py is absent (this whole
    suite importorskips until Wave 3); the activation plan confirms the exact binding.
    """

    def _apply():
        monkeypatch.setattr("agent.supervisor.MAX_SUPERVISOR_HOPS", 0, raising=False)
        monkeypatch.setattr("agent.supervisor.MAX_TOOL_CALLS", 0, raising=False)

    return _apply


@pytest.fixture
def tool_abstain(monkeypatch):
    """Return ``tool_abstain(tool='query_forecast')`` — makes a read-only tool honestly abstain.

    Forces the committed loader to raise ``FileNotFoundError``, which ``query_forecast.run``
    already converts into the honest ``abstain=True, record=None`` no-band state (P14) — never a
    fabricated band. The synthesis node then returns the honest labelled partial (D-08).
    """

    def _apply(tool: str = "query_forecast"):
        def _raise(*args, **kwargs):
            raise FileNotFoundError(
                "stubbed abstain: no committed record for this field (honest no-band, D-08)"
            )

        if tool == "query_forecast":
            monkeypatch.setattr("pipelines.forecast.load_forecast", _raise, raising=False)
        else:
            monkeypatch.setattr(f"agent.tools.{tool}.load_record", _raise, raising=False)

    return _apply
