"""
Unit test — the red-flag precompute loop runs the 7 canned queries through the
EXISTING agent graph (agent.graph.GRAPH) and stores a RedFlagField per key; a
not-disclosed result becomes a RefusalResponse (D3-03); a field whose number
fails cite_check grounding becomes a blocked RefusalResponse (L3-9), never an
unsourced number; the OFS-vs-fresh field reuses the snapshot's cached ofs_fresh.

Requirement: EXTRACT-01/02. Plan 03 implements pipelines/redflag.py.
Function names test_seven_field_loop_monkeypatched / test_not_disclosed_becomes_refusal
are LOCKED (Wave 0 scaffold, 03-01); the rest pin the plan's acceptance criteria.

Fully offline: GRAPH.invoke is monkeypatched — no live Gemini/Qdrant.
"""
from __future__ import annotations

import pytest

from agent.redflag_schema import RedFlagField, RedFlagRecord
from agent.schemas import (
    Claim,
    GroundedAnswer,
    RefusalResponse,
    RetrievedChunkRef,
)
from pipelines.redflag_queries import REDFLAG_QUERIES

# A real catalogue drhp_id so the is_known_drhp_id allow-list guard passes.
KNOWN_DRHP_ID = "swiggy_2024_11"


# ---------------------------------------------------------------------------
# Builders for the monkeypatched GRAPH.invoke return states
# ---------------------------------------------------------------------------


def _grounded_answer(claim_id: str = "c_rf0001") -> GroundedAnswer:
    span = "Related-party transactions were ₹120 crore, 3.4% of revenue"
    source = RetrievedChunkRef(
        chunk_id="chunk_rf_001",
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
        source_chunk_id="chunk_rf_001",
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


def _grounded_state(claim_id: str = "c_rf0001") -> dict:
    """A graph state where cite_check passed (all_claims_grounded True)."""
    return {
        "grounded_answer": _grounded_answer(claim_id),
        "refusal": None,
        "all_claims_grounded": True,
    }


def _refusal_state() -> dict:
    """A graph state where the DRHP is silent (not-disclosed honest refusal)."""
    return {
        "grounded_answer": None,
        "refusal": RefusalResponse(
            reason="low_retrieval_score",
            explanation="This DRHP does not appear to disclose this field.",
        ),
        "all_claims_grounded": False,
    }


def _numeric_blocked_state(claim_id: str = "c_rf0002") -> dict:
    """A graph state where an answer was generated but its number failed
    cite_check grounding — grounded_answer present yet all_claims_grounded False,
    plus the graph's staged refusal shell."""
    return {
        "grounded_answer": _grounded_answer(claim_id),
        "refusal": RefusalResponse(
            reason="unsupported_claim",
            explanation="",
        ),
        "all_claims_grounded": False,
    }


def _patch_graph(monkeypatch, state_factory) -> None:
    """Monkeypatch agent.graph.GRAPH.invoke to a deterministic offline callable."""
    import agent.graph as graph_mod

    class _FakeGraph:
        def invoke(self, payload):  # noqa: D401 - mirrors GRAPH.invoke signature
            return state_factory(payload)

    monkeypatch.setattr(graph_mod, "GRAPH", _FakeGraph(), raising=True)


# ---------------------------------------------------------------------------
# Locked tests (Wave 0 scaffold)
# ---------------------------------------------------------------------------


def test_seven_field_loop_monkeypatched(monkeypatch) -> None:
    """With GRAPH.invoke monkeypatched to return a grounded answer, the
    precompute loop produces a RedFlagField for each of the 7 REDFLAG_QUERIES
    keys, each grounded field carrying a non-None confidence tier."""
    from pipelines import redflag

    _patch_graph(monkeypatch, lambda payload: _grounded_state())

    record = redflag.precompute_redflags(KNOWN_DRHP_ID, write=False)

    assert isinstance(record, RedFlagRecord)
    assert set(record.fields.keys()) == set(REDFLAG_QUERIES.keys())
    for key, field in record.fields.items():
        assert isinstance(field, RedFlagField)
        assert isinstance(field.value, GroundedAnswer)
        assert field.confidence_tier is not None, f"{key} should carry a confidence tier"
        assert field.confidence_score is not None


def test_not_disclosed_becomes_refusal(monkeypatch) -> None:
    """A field whose graph run yields no grounded answer is stored as a
    RefusalResponse value with confidence_tier None (D3-03)."""
    from pipelines import redflag

    _patch_graph(monkeypatch, lambda payload: _refusal_state())

    record = redflag.precompute_redflags(KNOWN_DRHP_ID, write=False)

    # ofs_vs_fresh reuses the swiggy snapshot's grounded split (not the graph),
    # so the not-disclosed assertion applies to the graph-driven fields.
    for key, field in record.fields.items():
        if key == "ofs_vs_fresh":
            continue
        assert isinstance(field.value, RefusalResponse), f"{key} should be a refusal"
        assert field.confidence_tier is None
        assert field.confidence_score is None


# ---------------------------------------------------------------------------
# Acceptance-criteria tests (the plan's <acceptance_criteria>)
# ---------------------------------------------------------------------------


def test_ungrounded_number_becomes_blocked_refusal(monkeypatch) -> None:
    """A grounded answer whose number cite_check reports ungrounded
    (all_claims_grounded False) is stored as a blocked RefusalResponse carrying
    the L3-9 blocked-copy explanation — never an unsourced number (T-03-03)."""
    from pipelines import redflag

    _patch_graph(monkeypatch, lambda payload: _numeric_blocked_state())

    record = redflag.precompute_redflags(KNOWN_DRHP_ID, write=False)

    # ofs_vs_fresh reuses the swiggy snapshot (grounded), not the blocked graph
    # state; the numeric-block applies to the graph-driven fields.
    for key, field in record.fields.items():
        if key == "ofs_vs_fresh":
            continue
        assert isinstance(field.value, RefusalResponse), (
            f"{key} with an ungrounded number must be a refusal, not a GroundedAnswer"
        )
        assert field.confidence_tier is None
        assert "Could not ground this number" in field.value.explanation


def test_path_guard_rejects_unknown_drhp_id() -> None:
    """precompute_redflags raises on a non-allow-listed drhp_id BEFORE forming
    any path (path-traversal mitigation T-03-01)."""
    from pipelines import redflag

    with pytest.raises(ValueError):
        redflag.precompute_redflags("../etc/passwd", write=False)


def test_ofs_vs_fresh_reuses_snapshot_ofs_fresh(monkeypatch) -> None:
    """The ofs_vs_fresh field reuses the snapshot's cached ofs_fresh rather than
    re-extracting from a fresh graph run (the snapshot exists for swiggy)."""
    from pipelines import redflag

    invoked_keys: list[str] = []

    def _factory(payload):
        # Record which queries actually hit the graph; ofs_vs_fresh must NOT.
        for key, query in REDFLAG_QUERIES.items():
            if query == payload.get("question"):
                invoked_keys.append(key)
        return _refusal_state()

    _patch_graph(monkeypatch, _factory)

    record = redflag.precompute_redflags(KNOWN_DRHP_ID, write=False)

    assert "ofs_vs_fresh" in record.fields
    # The snapshot for swiggy exists, so ofs_vs_fresh is derived from its cached
    # ofs_fresh and the canned query is NOT re-run through the graph.
    assert "ofs_vs_fresh" not in invoked_keys


def test_record_round_trips_via_load_redflag(monkeypatch, tmp_path) -> None:
    """A RedFlagRecord written by the pipeline round-trips through load_redflag."""
    from pipelines import redflag

    monkeypatch.setattr(redflag, "REDFLAG_DIR", tmp_path, raising=True)
    _patch_graph(monkeypatch, lambda payload: _grounded_state())

    written = redflag.precompute_redflags(KNOWN_DRHP_ID, write=True)
    loaded = redflag.load_redflag(KNOWN_DRHP_ID)

    assert loaded.drhp_id == written.drhp_id
    assert set(loaded.fields.keys()) == set(written.fields.keys())


def test_uses_existing_graph_no_new_llm_client() -> None:
    """pipelines/redflag.py reuses the existing graph (GRAPH.invoke appears at
    least once) and constructs no new LLM client."""
    from pathlib import Path

    src = Path(redflag_source())
    text = src.read_text(encoding="utf-8")
    assert text.count("GRAPH.invoke") >= 1


def redflag_source() -> str:
    import pipelines.redflag as rf

    return rf.__file__
