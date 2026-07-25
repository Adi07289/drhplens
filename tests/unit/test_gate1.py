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
    """gate1_check with max_reranker_score below τ (garbage retrieval) sets gate1_passed=False."""
    from agent.nodes import gate1_check

    state = {
        **_base_state(),
        "reranked_top_k": [{"chunk_id": "c1", "rerank_score": -5.0}],  # below -3.0
    }
    result = gate1_check.run(state)
    assert result["gate1_passed"] is False
    assert result["gate1_max_score"] == pytest.approx(-5.0)


def test_relevant_negative_logit_passes_gate1():
    """EVAL-03 calibration: a relevant DRHP passage with a negative-but-above-τ reranker
    logit (the bge-reranker norm) must PASS gate1 rather than be refused pre-LLM."""
    from agent.nodes import gate1_check

    state = {
        **_base_state(),
        "reranked_top_k": [{"chunk_id": "c1", "rerank_score": -2.0}],  # above -3.0
    }
    result = gate1_check.run(state)
    assert result["gate1_passed"] is True


def test_gate1_threshold_calibrated():
    """GATE1_THRESHOLD calibrated 2026-07-24 (EVAL-03): screens garbage only, admits
    relevant negative reranker logits; refusal is the LLM + cite_check job."""
    assert GATE1_THRESHOLD == pytest.approx(-3.0)


def test_gate1_empty_reranked_fails():
    """No reranked chunks → gate1_passed=False regardless of threshold (score = -inf)."""
    from agent.nodes import gate1_check

    state = {**_base_state(), "reranked_top_k": []}
    result = gate1_check.run(state)
    assert result["gate1_passed"] is False
    assert result["gate1_max_score"] == float("-inf")


def test_out_of_scope_question_refused_despite_high_score():
    """TRUST-04: a post-listing/real-time question refuses even with a HIGH reranker
    score (the reranker can't gate topical out-of-scope — swiggy-012 scored +1.23)."""
    from agent.nodes import gate1_check

    state = {
        **_base_state("How did Swiggy's share price perform compared to Zomato on listing day?"),
        "reranked_top_k": [{"chunk_id": "c1", "rerank_score": 4.0}],  # high, would pass score gate
    }
    result = gate1_check.run(state)
    assert result["gate1_passed"] is False


def test_in_scope_question_with_good_score_still_passes():
    """A normal DRHP question with a passing score is unaffected by the OOS screen."""
    from agent.nodes import gate1_check

    state = {
        **_base_state("What is the total issue size of the Swiggy IPO?"),
        "reranked_top_k": [{"chunk_id": "c1", "rerank_score": 4.0}],
    }
    result = gate1_check.run(state)
    assert result["gate1_passed"] is True


def test_is_out_of_scope_precision():
    """The OOS screen flags post-listing/real-time Qs but not legitimate DRHP Qs."""
    from agent.nodes.gate1_check import is_out_of_scope

    assert is_out_of_scope("What is Swiggy's current market capitalization today?") is True
    assert is_out_of_scope("How did the stock perform on listing day?") is True
    # legitimate DRHP questions must NOT trigger
    assert is_out_of_scope("On which stock exchanges is Swiggy proposed to be listed?") is False
    assert is_out_of_scope("What is the expected listing date of the Swiggy IPO?") is False
    assert is_out_of_scope("How did Swiggy's revenue perform in FY2024?") is False
    assert is_out_of_scope("What was the total issue size of the Swiggy IPO?") is False
