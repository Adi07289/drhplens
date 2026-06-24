"""
Unit test — 6 field blocks computed via agent; "not disclosed" stored
honestly when DRHP silent (esp. SNAP-07 pledging) (no threat).

Requirement: SNAP-02..07. Threat: none (honesty-first correctness invariant,
not a STRIDE threat).
Secure behavior: each of the 6 snapshot field blocks is computed via the
existing agent pipeline; when the DRHP is silent on a field, a RefusalResponse
is stored instead of a fabricated GroundedAnswer.

Wave 3 implementation (02-04-PLAN.md Task 2). All GRAPH.invoke calls are
monkeypatched — no live LLM/Qdrant call happens in this test module.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agent.schemas import Claim, GroundedAnswer, RefusalResponse, RetrievedChunkRef
from pipelines.snapshot import precompute
from pipelines.snapshot_queries import SNAPSHOT_QUERIES


def _make_chunk_ref(chunk_id: str = "chunk_001") -> RetrievedChunkRef:
    return RetrievedChunkRef(
        chunk_id=chunk_id,
        page_start=5,
        page_end=6,
        printed_page_label="5",
        section="Issue Details",
        score=0.92,
        verbatim_span="Some verbatim DRHP text",
        span_offsets=(0, 23),
    )


def _make_grounded_answer(claim_id: str = "c_abc123", prose: str | None = None) -> GroundedAnswer:
    return GroundedAnswer(
        answer_prose=prose or f"Some grounded fact {{{{{claim_id}}}}}.",
        claims=[
            Claim(
                claim_id=claim_id,
                text="Some grounded fact",
                source_chunk_id="chunk_001",
                drhp_page=5,
                section="Issue Details",
                verbatim_span="Some verbatim DRHP text",
                span_offsets=(0, 23),
                sources=[_make_chunk_ref()],
            )
        ],
        sub_question_addressed=[],
        sub_question_unaddressed=[],
    )


def _make_refusal(reason: str = "low_retrieval_score") -> RefusalResponse:
    return RefusalResponse(
        reason=reason,  # type: ignore[arg-type]
        explanation="This DRHP does not disclose this.",
        reformulation_suggestions=[],
    )


def test_precompute_calls_graph_invoke_once_per_snapshot_query() -> None:
    """precompute(drhp_id) calls GRAPH.invoke once per SNAPSHOT_QUERIES key
    with {"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0}."""
    calls: list[dict] = []

    def fake_invoke(state: dict) -> dict:
        calls.append(state)
        return {
            "grounded_answer": _make_grounded_answer(claim_id="c_aaaaaa", prose="x {{c_aaaaaa}}"),
            "refusal": None,
        }

    with patch("agent.graph.GRAPH") as mock_graph:
        mock_graph.invoke.side_effect = fake_invoke
        precompute("test_ipo_2026_01", write=False)

    assert mock_graph.invoke.call_count == len(SNAPSHOT_QUERIES)
    called_questions = {c["question"] for c in calls}
    assert called_questions == set(SNAPSHOT_QUERIES.values())
    for call_state in calls:
        assert call_state["drhp_id"] == "test_ipo_2026_01"
        assert call_state["regenerate_attempts"] == 0


def test_precompute_stores_grounded_answer_when_present() -> None:
    """When GRAPH returns a grounded_answer, that field is stored as the
    GroundedAnswer."""
    ga = _make_grounded_answer(claim_id="c_aaaaaa", prose="Issue size is X {{c_aaaaaa}}.")

    with patch("agent.graph.GRAPH") as mock_graph:
        mock_graph.invoke.return_value = {"grounded_answer": ga, "refusal": None}
        record = precompute("test_ipo_2026_01", write=False)

    assert isinstance(record.fields["metadata"], GroundedAnswer)
    assert record.fields["metadata"].answer_prose == ga.answer_prose
    assert record.fields["metadata"].claims[0].claim_id == "c_aaaaaa"


def test_precompute_stores_refusal_when_drhp_silent_on_promoter_pledging() -> None:
    """When GRAPH returns only a refusal (DRHP silent), the field is stored
    as the RefusalResponse — honest "not disclosed" — exercised for the
    promoter/pledging field (SNAP-07)."""
    refusal = _make_refusal(reason="unsupported_claim")

    def fake_invoke(state: dict) -> dict:
        if state["question"] == SNAPSHOT_QUERIES["promoter"]:
            return {"grounded_answer": None, "refusal": refusal}
        return {
            "grounded_answer": _make_grounded_answer(claim_id="c_bbbbbb", prose="x {{c_bbbbbb}}."),
            "refusal": None,
        }

    with patch("agent.graph.GRAPH") as mock_graph:
        mock_graph.invoke.side_effect = fake_invoke
        record = precompute("test_ipo_2026_01", write=False)

    assert isinstance(record.fields["promoter"], RefusalResponse)
    assert record.fields["promoter"].reason == "unsupported_claim"
    assert "not disclose" in record.fields["promoter"].explanation.lower()


def test_precompute_never_commits_banned_token_prose() -> None:
    """Every stored answer_prose has passed compliance.scrubber.scrub — a
    fixture answer containing a banned token causes precompute to refuse
    that field, never commit it."""
    banned_ga = _make_grounded_answer(
        claim_id="c_cccccc", prose="We recommend you subscribe {{c_cccccc}}."
    )

    with patch("agent.graph.GRAPH") as mock_graph:
        mock_graph.invoke.return_value = {"grounded_answer": banned_ga, "refusal": None}
        record = precompute("test_ipo_2026_01", write=False)

    for key, value in record.fields.items():
        if isinstance(value, GroundedAnswer):
            assert "recommend" not in value.answer_prose.lower()
            assert "subscribe" not in value.answer_prose.lower()
        else:
            assert isinstance(value, RefusalResponse)
            assert value.reason == "banned_token"
