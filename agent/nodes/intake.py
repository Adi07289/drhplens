"""
agent/nodes/intake.py — Normalizes the incoming user question and initializes
all mutable GraphState counters.

Pure Python: no external calls, no I/O, no LLM.
"""
from __future__ import annotations

from agent.policies import DRHP_ID_DEFAULT
from agent.state import GraphState


def run(state: GraphState) -> GraphState:
    """Normalize question and initialize per-invocation counters.

    - Strip leading/trailing whitespace from the question.
    - Default state["drhp_id"] to DRHP_ID_DEFAULT when absent or falsy — this
      is the back-compat anchor that keeps the Phase 1 baseline green when a
      caller invokes the graph without a drhp_id key (Phase 2 Pattern 1).
    - Initialize regenerate_attempts = 0 (D-09 counter starts fresh).
    - Initialize all mutable state keys to safe defaults so downstream
      nodes can read without KeyError.

    Args:
        state: Incoming GraphState from the LangGraph entry point.

    Returns:
        Updated GraphState with normalized question, resolved drhp_id, and
        initialized counters.
    """
    question = state.get("question", "").strip()
    drhp_id = state.get("drhp_id") or DRHP_ID_DEFAULT

    return {
        **state,
        "question": question,
        "drhp_id": drhp_id,
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": False,
        "gate1_max_score": 0.0,
        "sub_questions": [question],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
    }
