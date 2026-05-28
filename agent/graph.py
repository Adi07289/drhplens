"""
agent/graph.py — LangGraph StateGraph compilation matching SKELETON §C topology.

10 nodes: intake → retrieve → rerank → gate1_check → decompose → generate →
          scrub → cite_check → refuse_with_reformulation → emit

3 refusal branches (all route to END via refuse_with_reformulation):
  1. Gate 1 (pre-LLM): gate1_check → refuse_with_reformulation → END
  2. Gate 2 (post-LLM): cite_check → refuse_with_reformulation → END
  3. Scrub exhausted (D-09): scrub → refuse_with_reformulation → END

Zero LangGraph cycles: the scrubber-retry "loop" is a counter-bounded
conditional edge (reads regenerate_attempts), not a graph cycle. SKELETON §C.

build_graph(checkpointer=None) returns a compiled graph.
GRAPH = build_graph(MemorySaver()) — module-level singleton for agent.demo
and Wave 4 Streamlit. Wave 6 swaps MemorySaver for SqliteSaver.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.nodes import (
    cite_check,
    decompose,
    emit,
    gate1_check,
    generate,
    intake,
    rerank,
    refuse_with_reformulation,
    retrieve,
    scrub,
)
from agent.policies import MAX_REGENERATE_ATTEMPTS
from agent.state import GraphState


# ---------------------------------------------------------------------------
# Conditional routing functions
# ---------------------------------------------------------------------------


def _route_gate1(state: GraphState) -> str:
    """Route after gate1_check: pass → decompose; fail → refuse."""
    if state.get("gate1_passed"):
        return "decompose"
    return "refuse_with_reformulation"


def _route_scrub(state: GraphState) -> str:
    """Route after scrub: D-09 counter-bounded retry or refuse.

    - scrub_passed=True → cite_check (happy path)
    - scrub_passed=False AND attempts <= MAX AND no refusal → generate (retry)
    - scrub_passed=False AND (attempts > MAX OR refusal set) → refuse
    """
    if state.get("scrub_passed"):
        return "cite_check"
    if (
        not state.get("scrub_passed")
        and state.get("regenerate_attempts", 0) <= MAX_REGENERATE_ATTEMPTS
        and not state.get("refusal")
    ):
        return "generate"
    return "refuse_with_reformulation"


def _route_cite_check(state: GraphState) -> str:
    """Route after cite_check: grounded → emit; not grounded → refuse."""
    if state.get("all_claims_grounded"):
        return "emit"
    return "refuse_with_reformulation"


def _route_after_generate(state: GraphState) -> str:
    """Route after generate: infrastructure error sets refusal → emit directly."""
    if state.get("refusal") and not state.get("grounded_answer"):
        return "emit"
    return "scrub"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(checkpointer=None):
    """Build and compile the LangGraph StateGraph per SKELETON §C topology.

    Args:
        checkpointer: Optional LangGraph checkpointer (MemorySaver for Phase 1;
                      SqliteSaver/PostgresSaver for Phase 6). If None, the graph
                      compiles without checkpointing (useful for unit tests).

    Returns:
        A compiled LangGraph graph with `.invoke()` method.
    """
    g = StateGraph(GraphState)

    # Add all 10 nodes
    g.add_node("intake", intake.run)
    g.add_node("retrieve", retrieve.run)
    g.add_node("rerank", rerank.run)
    g.add_node("gate1_check", gate1_check.run)
    g.add_node("decompose", decompose.run)
    g.add_node("generate", generate.run)
    g.add_node("scrub", scrub.run)
    g.add_node("cite_check", cite_check.run)
    g.add_node("refuse_with_reformulation", refuse_with_reformulation.run)
    g.add_node("emit", emit.run)

    # Entry point
    g.set_entry_point("intake")

    # Linear edges: intake → retrieve → rerank → gate1_check
    g.add_edge("intake", "retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "gate1_check")

    # Conditional from gate1_check: pass → decompose; fail → refuse
    g.add_conditional_edges(
        "gate1_check",
        _route_gate1,
        {"decompose": "decompose", "refuse_with_reformulation": "refuse_with_reformulation"},
    )

    # Linear: decompose → generate
    g.add_edge("decompose", "generate")

    # After generate: infrastructure error goes straight to emit; otherwise → scrub
    g.add_conditional_edges(
        "generate",
        _route_after_generate,
        {"scrub": "scrub", "emit": "emit"},
    )

    # Conditional from scrub: passed → cite_check; retry → generate; exhausted → refuse
    g.add_conditional_edges(
        "scrub",
        _route_scrub,
        {
            "cite_check": "cite_check",
            "generate": "generate",
            "refuse_with_reformulation": "refuse_with_reformulation",
        },
    )

    # Conditional from cite_check: grounded → emit; not grounded → refuse
    g.add_conditional_edges(
        "cite_check",
        _route_cite_check,
        {"emit": "emit", "refuse_with_reformulation": "refuse_with_reformulation"},
    )

    # Terminal edges: both emit and refuse_with_reformulation route to END
    g.add_edge("emit", END)
    g.add_edge("refuse_with_reformulation", END)

    return g.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

GRAPH = build_graph(MemorySaver())
"""Module-level compiled graph singleton.

Used by agent.demo (Walking Skeleton CLI) and Wave 4 Streamlit app.
Both callers do: from agent.graph import GRAPH; result = GRAPH.invoke(...)
"""
