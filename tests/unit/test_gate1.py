"""
Stub: agent/nodes/gate1_check.py — pre-LLM retrieval-score gate (D-05 Gate 1).

Validates that:
- When max reranker score < threshold τ, gate1_check returns gate1_passed=False
- The graph then routes to refuse_with_reformulation (never reaches LLM generate node)
- When max reranker score >= threshold τ, gate1_passed=True and graph continues to decompose

Wave 3 owns this implementation (RAG-03; D-05 Gate 1).
"""
from __future__ import annotations

import pytest

pytest.importorskip("agent.nodes.gate1_check", reason="agent/nodes/gate1_check.py ships in Wave 3")


@pytest.mark.xfail(reason="Wave 3 owns this — implements agent/nodes/gate1_check.py", strict=False)
def test_below_threshold_routes_to_refusal() -> None:
    """gate1_check node with max_reranker_score below τ must set gate1_passed=False
    so the graph routes to refuse_with_reformulation and never calls the LLM."""
    assert False, "Wave 3 must implement: build mock GraphState with low score, assert gate1_passed=False"
