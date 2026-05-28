"""
Unit tests for agent/graph.py — LangGraph StateGraph topology (SKELETON §C).

Tests verify the 10-node topology, entry point, terminal nodes, and conditional
routing logic. Full graph invocation is covered in the Task 6 integration tests.
"""
from __future__ import annotations

import pytest

from agent.graph import GRAPH, build_graph
from agent.policies import MAX_REGENERATE_ATTEMPTS
from agent.schemas import RefusalResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_state(**overrides) -> dict:
    state = {
        "question": "What is the issue size?",
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": False,
        "gate1_max_score": 0.0,
        "sub_questions": ["What is the issue size?"],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_build_graph_returns_compiled_graph():
    """build_graph() returns a compiled graph with .invoke() method."""
    g = build_graph()
    assert hasattr(g, "invoke"), "build_graph() must return a compiled graph with .invoke()"


def test_graph_node_set_matches_skeleton():
    """Compiled graph has exactly the 10 nodes from SKELETON §C (plus __start__/__end__)."""
    g = build_graph()
    nodes = set(g.get_graph().nodes)
    expected_business_nodes = {
        "intake", "retrieve", "rerank", "gate1_check", "decompose",
        "generate", "scrub", "cite_check", "refuse_with_reformulation", "emit",
    }
    expected_with_internal = expected_business_nodes | {"__start__", "__end__"}
    assert expected_with_internal.issubset(nodes), (
        f"Missing nodes: {expected_with_internal - nodes}"
    )
    # No extra nodes beyond expected
    extra = nodes - expected_with_internal
    assert extra == set(), f"Unexpected extra nodes: {extra}"


def test_graph_entry_point_is_intake():
    """The entry point is intake."""
    g = build_graph()
    graph_def = g.get_graph()
    # LangGraph: __start__ → first real node = intake
    edges = list(graph_def.edges)
    start_targets = [e[1] for e in edges if e[0] == "__start__"]
    assert "intake" in start_targets, f"Entry point is not intake: {start_targets}"


def test_graph_terminal_nodes_are_emit_and_refuse():
    """Both emit and refuse_with_reformulation route to __end__."""
    g = build_graph()
    graph_def = g.get_graph()
    edges = list(graph_def.edges)
    terminal_sources = {e[0] for e in edges if e[1] == "__end__"}
    assert "emit" in terminal_sources, "emit must route to END"
    assert "refuse_with_reformulation" in terminal_sources, (
        "refuse_with_reformulation must route to END"
    )


def test_graph_gate1_branch():
    """_route_gate1 routing: gate1_passed=False → refuse; True → decompose."""
    from agent.graph import _route_gate1

    assert _route_gate1(_base_state(gate1_passed=False)) == "refuse_with_reformulation"
    assert _route_gate1(_base_state(gate1_passed=True)) == "decompose"


def test_graph_scrub_branch_first_failure_loops_to_generate():
    """scrub_passed=False, attempts=1 (≤ MAX), no refusal → back to generate."""
    from agent.graph import _route_scrub

    state = _base_state(
        scrub_passed=False,
        regenerate_attempts=1,
        refusal=None,
    )
    assert _route_scrub(state) == "generate"


def test_graph_scrub_branch_second_failure_to_refuse():
    """scrub_passed=False, attempts=2 (> MAX=1), refusal set → refuse."""
    from agent.graph import _route_scrub

    state = _base_state(
        scrub_passed=False,
        regenerate_attempts=2,
        refusal=RefusalResponse(
            reason="banned_token",
            explanation="banned",
            reformulation_suggestions=[],
        ),
    )
    assert _route_scrub(state) == "refuse_with_reformulation"


def test_graph_cite_check_branch():
    """all_claims_grounded=True → emit; False → refuse."""
    from agent.graph import _route_cite_check

    assert _route_cite_check(_base_state(all_claims_grounded=True)) == "emit"
    assert _route_cite_check(_base_state(all_claims_grounded=False)) == "refuse_with_reformulation"


def test_graph_compiles_with_memory_checkpointer():
    """build_graph() with MemorySaver produces a graph that accepts thread_id invocation."""
    from langgraph.checkpoint.memory import MemorySaver

    g = build_graph(MemorySaver())
    assert hasattr(g, "invoke"), "Graph with MemorySaver must have .invoke()"
    # Verify the graph can at least call get_graph() without error
    nodes = set(g.get_graph().nodes)
    assert "intake" in nodes
