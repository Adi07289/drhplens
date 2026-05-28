"""
agent/nodes/gate1_check.py — Pre-LLM retrieval-score gate (D-05 Gate 1).

Reads the maximum reranker score from reranked_top_k and compares it against
GATE1_THRESHOLD. If the score is below the threshold, the graph routes to
refuse_with_reformulation without ever calling the LLM.

Pure Python: no external calls. Wave 5 adds a Langfuse span around this node.
"""
from __future__ import annotations

from agent.policies import GATE1_THRESHOLD
from agent.state import GraphState


def run(state: GraphState) -> GraphState:
    """Compute max reranker score and set gate1_passed.

    state["gate1_max_score"] is stored for Langfuse trace consumers (Wave 5)
    and for threshold calibration against the gold eval set (Wave 5).

    Args:
        state: GraphState with state["reranked_top_k"] populated by rerank node.

    Returns:
        Updated GraphState with:
          - gate1_max_score: float — the highest reranker score seen
          - gate1_passed: bool — True iff max_score >= GATE1_THRESHOLD
    """
    reranked = state.get("reranked_top_k", [])

    if not reranked:
        max_score = -1.0
    else:
        max_score = max(c.get("rerank_score", -1.0) for c in reranked)

    gate1_passed = max_score >= GATE1_THRESHOLD

    return {
        **state,
        "gate1_max_score": max_score,
        "gate1_passed": gate1_passed,
    }
