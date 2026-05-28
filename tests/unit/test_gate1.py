"""
Unit tests for agent/nodes/gate1_check.py — pre-LLM retrieval-score gate.

These tests are imported from test_retrieve.py but also stand alone here for
the Wave 0 xfail stub flip. The test_below_threshold_routes_to_refusal test
is the canonical Wave 0 stub.
"""
from __future__ import annotations

import pytest

from agent.policies import GATE1_THRESHOLD


def _base_state(question: str = "What is the issue size?") -> dict:
    return {
        "question": question,
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


def test_below_threshold_routes_to_refusal():
    """Wave 0 xfail flip: gate1_check with max_reranker_score below τ sets gate1_passed=False."""
    from agent.nodes import gate1_check

    state = {
        **_base_state(),
        "reranked_top_k": [{"chunk_id": "c1", "rerank_score": -1.0}],
    }
    result = gate1_check.run(state)
    assert result["gate1_passed"] is False
    assert result["gate1_max_score"] == pytest.approx(-1.0)


def test_gate1_threshold_value_is_zero():
    """Confirm GATE1_THRESHOLD is 0.0 per RESEARCH Open Question 1."""
    assert GATE1_THRESHOLD == 0.0


def test_gate1_empty_reranked_fails():
    """gate1_check with no reranked chunks sets gate1_passed=False (no positive score)."""
    from agent.nodes import gate1_check

    state = {**_base_state(), "reranked_top_k": []}
    result = gate1_check.run(state)
    assert result["gate1_passed"] is False
