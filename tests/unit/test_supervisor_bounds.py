"""
tests/unit/test_supervisor_bounds.py — the bounded supervisor's P8 + honest-partial
contract (06.3-05, D-02/D-05/D-06/D-08).

Two lanes, all OFFLINE (no live LLM, no Qdrant):

  Task 1 — ``route`` trips to ``synthesize`` on each of the three budget bounds
  (hops / tool-calls / wall-clock) and dispatches otherwise; ``invoke_supervisor``
  mints a fresh ``thread_id`` per run and converts a ``GraphRecursionError`` crash
  backstop into an honest partial (``is_partial=True``) with no exception escaping;
  the existing DRHP-RAG graph is embedded UNCHANGED (``build_graph(checkpointer=None)``).

  Task 2 — the terminal ``synthesize`` node: a DRHP-only end-to-end run (subgraph
  stubbed to a grounded answer) returns a scrubbed, disclaimered answer with
  ``is_partial=False``; a banned-token grounded answer yields the refusal; a
  budget-trip run sets ``is_partial=True``.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from langgraph.errors import GraphRecursionError

import agent.supervisor as sup
from agent.policies import MAX_SUPERVISOR_HOPS, MAX_TOOL_CALLS, WALL_CLOCK_S
from agent.schemas import Claim, GroundedAnswer, RetrievedChunkRef
from compliance.disclaimer_text import PER_ANSWER_FOOTER
from compliance.scrubber import scrub


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _route_state(**overrides) -> dict:
    state = {
        "hops": 0,
        "tool_calls": 0,
        "tool_plan": ["drhp_rag"],
        "started_at": time.monotonic(),
    }
    state.update(overrides)
    return state


def _grounded_answer(prose: str = "The issue size is ₹11,300 crore {{c_issue01}}.") -> GroundedAnswer:
    span = "The total issue size is ₹11,300 crore comprising fresh issue and OFS."
    source = RetrievedChunkRef(
        chunk_id="chunk_issue_001",
        page_start=42,
        page_end=42,
        section="The Offer",
        verbatim_span=span,
        span_offsets=[0, len(span)],
    )
    claim = Claim(
        claim_id="c_issue01",
        text="The issue size is ₹11,300 crore",
        source_chunk_id="chunk_issue_001",
        drhp_page=42,
        section="The Offer",
        verbatim_span=span,
        span_offsets=[0, len(span)],
        sources=[source],
    )
    return GroundedAnswer(answer_prose=prose, claims=[claim])


# ===========================================================================
# Task 1 — route() budget bounds (the real P8 guard, D-06)
# ===========================================================================


def test_route_dispatches_first_tool_when_in_budget():
    """In budget with a non-empty plan → dispatch the first pending tool."""
    assert sup.route(_route_state(tool_plan=["drhp_rag", "query_peers"])) == "drhp_rag"


def test_route_trips_to_synthesize_on_hops_over_budget():
    """hops > MAX_SUPERVISOR_HOPS → halt to synthesize (D-06)."""
    state = _route_state(hops=MAX_SUPERVISOR_HOPS + 1)
    assert sup.route(state) == "synthesize"


def test_route_trips_to_synthesize_on_tool_calls_over_budget():
    """tool_calls >= MAX_TOOL_CALLS → halt to synthesize (D-06)."""
    state = _route_state(tool_calls=MAX_TOOL_CALLS)
    assert sup.route(state) == "synthesize"


def test_route_trips_to_synthesize_on_wall_clock_backstop(monkeypatch):
    """Wall-clock elapsed > WALL_CLOCK_S → halt to synthesize (D-06 backstop)."""
    started = 1000.0
    # monotonic jumps far past the wall-clock budget since started_at.
    monkeypatch.setattr(sup.time, "monotonic", lambda: started + WALL_CLOCK_S + 5.0)
    state = _route_state(started_at=started)
    assert sup.route(state) == "synthesize"


def test_route_trips_to_synthesize_on_empty_plan():
    """An empty tool_plan (out-of-scope / advice-bait) → synthesize (refuses)."""
    assert sup.route(_route_state(tool_plan=[])) == "synthesize"


# ===========================================================================
# Task 1 — subgraph embedded UNCHANGED (D-02)
# ===========================================================================


def test_drhp_rag_subgraph_embedded_unchanged():
    """The embedded DRHP-RAG subgraph is the existing 10-node graph, byte-for-byte."""
    nodes = set(sup.DRHP_RAG_SUBGRAPH.get_graph().nodes)
    expected = {
        "intake", "retrieve", "rerank", "gate1_check", "decompose",
        "generate", "scrub", "cite_check", "refuse_with_reformulation", "emit",
    }
    assert expected.issubset(nodes), f"subgraph topology changed: missing {expected - nodes}"


def test_supervisor_graph_has_all_nodes():
    """The compiled supervisor wires classify + drhp_rag + the 3 tools + synthesize."""
    nodes = set(sup.SUPERVISOR.get_graph().nodes)
    expected = {
        "classify", "drhp_rag", "query_peers", "query_forecast",
        "query_redflags", "synthesize",
    }
    assert expected.issubset(nodes), f"supervisor missing nodes: {expected - nodes}"


# ===========================================================================
# Task 1 — invoke_supervisor: GraphRecursionError → honest partial, fresh thread_id
# ===========================================================================


def test_invoke_supervisor_converts_recursion_error_to_honest_partial():
    """A GraphRecursionError (recursion_limit backstop) becomes an honest partial —
    is_partial=True, no exception escapes (D-08, caveat d)."""
    fake = MagicMock()
    fake.invoke.side_effect = GraphRecursionError("recursion_limit hit")
    with patch.object(sup, "SUPERVISOR", fake):
        final = sup.invoke_supervisor("loop forever", drhp_id="swiggy_2024_11")
    assert final["is_partial"] is True
    assert final.get("refusal") is None
    # The honest partial is scrubber-clean and carries the disclaimer.
    assert scrub(final["fused_answer"].answer_prose).passed
    assert PER_ANSWER_FOOTER in final["disclaimer"]


def test_invoke_supervisor_mints_fresh_thread_id_per_run():
    """Each invoke uses a fresh thread_id (mandatory once a checkpointer is attached)
    and sets recursion_limit as a backstop only."""
    seen_thread_ids: list[str] = []

    def _record(init, config):
        seen_thread_ids.append(config["configurable"]["thread_id"])
        assert config["recursion_limit"] == 50  # backstop only (~2× legal hops)
        return {**init, "is_partial": False, "refusal": None}

    fake = MagicMock()
    fake.invoke.side_effect = _record
    with patch.object(sup, "SUPERVISOR", fake):
        sup.invoke_supervisor("q1", drhp_id="swiggy_2024_11")
        sup.invoke_supervisor("q2", drhp_id="swiggy_2024_11")

    assert len(seen_thread_ids) == 2
    assert seen_thread_ids[0] != seen_thread_ids[1]
    assert all(tid.startswith("run-") for tid in seen_thread_ids)


def test_invoke_supervisor_seeds_p8_counters():
    """The initial state seeds the SupervisorState P8 counters (hops/tool_calls/…)."""
    captured: dict = {}

    def _capture(init, config):
        captured.update(init)
        return {**init, "is_partial": False, "refusal": None}

    fake = MagicMock()
    fake.invoke.side_effect = _capture
    with patch.object(sup, "SUPERVISOR", fake):
        sup.invoke_supervisor("q", drhp_id="swiggy_2024_11")

    assert captured["hops"] == 0
    assert captured["tool_calls"] == 0
    assert captured["tool_plan"] == []
    assert captured["tool_results"] == []
    assert captured["is_partial"] is False
    assert captured["regenerate_attempts"] == 0
    assert isinstance(captured["started_at"], float)


# ===========================================================================
# Task 2 — synthesize node: DRHP-only end-to-end, banned-token, budget-trip
# ===========================================================================


def _run_supervisor_drhp_only(subgraph_out: dict, question: str = "What is the issue size?"):
    """Run the real supervisor with classify stubbed to route to drhp_rag and the
    embedded subgraph stubbed to return ``subgraph_out`` — a fully offline DRHP-only
    end-to-end run (no live LLM, no Qdrant)."""
    from agent.nodes.classify import RoutingDecision

    fake_sub = MagicMock()
    fake_sub.invoke.return_value = subgraph_out
    routing = RoutingDecision(tools=["drhp_rag"], is_advice_seeking=False, is_out_of_scope=False)
    with patch("agent.nodes.classify._llm_classify", return_value=routing), \
         patch.object(sup, "DRHP_RAG_SUBGRAPH", fake_sub):
        return sup.invoke_supervisor(question, drhp_id="swiggy_2024_11")


def test_drhp_only_end_to_end_returns_scrubbed_disclaimered_answer():
    """classify → drhp_rag → synthesize: a grounded DRHP answer flows to one
    scrubbed, disclaimered answer with is_partial=False (the thin vertical slice)."""
    ga = _grounded_answer()
    final = _run_supervisor_drhp_only(
        {"grounded_answer": ga, "all_claims_grounded": True, "refusal": None}
    )
    assert final["is_partial"] is False
    assert final.get("refusal") is None
    assert final["grounded_answer"] is not None
    assert scrub(final["grounded_answer"].answer_prose).passed
    assert PER_ANSWER_FOOTER in final["disclaimer"]
    # The bounded counter halted deterministically: one classify hop, one tool call.
    assert final["hops"] == 1
    assert final["tool_calls"] == 1


def test_drhp_only_banned_token_answer_yields_refusal():
    """A banned token surviving to synthesize BLOCKS to the refusal (never a
    fabricated rewrite — no live LLM to regenerate on this path)."""
    ga = _grounded_answer(prose="You should subscribe to this issue {{c_issue01}}.")
    final = _run_supervisor_drhp_only(
        {"grounded_answer": ga, "all_claims_grounded": True, "refusal": None}
    )
    assert final.get("refusal") is not None
    assert final["refusal"].reason == "banned_token"
    # The refusal explanation is itself scrubber-clean + carries the disclaimer.
    assert scrub(final["refusal"].explanation).passed
    assert PER_ANSWER_FOOTER in final["disclaimer"]


def test_synthesize_budget_trip_sets_is_partial():
    """Reaching synthesize with an UNFINISHED tool_plan (budget trip) → honest
    labelled partial (is_partial=True), scrubber-clean, no fabrication (D-06/D-08)."""
    from agent.nodes import synthesize

    state = {
        "tool_plan": ["query_peers", "query_forecast"],  # unfinished → budget trip
        "tool_results": [],
        "grounded_answer": None,
        "hops": 1,
        "tool_calls": 0,
    }
    out = synthesize.run(state)
    assert out["is_partial"] is True
    assert out.get("refusal") is None
    assert out["fused_answer"].is_partial is True
    assert scrub(out["fused_answer"].answer_prose).passed
    assert PER_ANSWER_FOOTER in out["disclaimer"]


def test_synthesize_empty_plan_nothing_grounded_refuses():
    """Empty plan + nothing grounded + no tools → the educational refusal (D-07)."""
    from agent.nodes import synthesize

    out = synthesize.run(
        {"tool_plan": [], "tool_results": [], "grounded_answer": None, "hops": 1, "tool_calls": 0}
    )
    assert out.get("refusal") is not None
    assert out["is_partial"] is False
    assert scrub(out["refusal"].explanation).passed
    assert PER_ANSWER_FOOTER in out["disclaimer"]
