"""
Unit tests for agent/nodes/decompose.py — multi-part question decomposer (D-06).

Uses unittest.mock to avoid real Gemini API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.policies import MAX_SUB_QUESTIONS


def _base_state(question: str) -> dict:
    return {
        "question": question,
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": True,
        "gate1_max_score": 0.85,
        "sub_questions": [question],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
    }


def test_multipart_question_splits_into_subquestions():
    """Wave 0 xfail flip: compound question with 'and' splits into >= 2 sub-questions."""
    from agent.nodes import decompose
    from agent.nodes.decompose import SubQuestions

    mock_result = SubQuestions(
        questions=["What is the issue size?", "What is the listing-day return?"],
        original_is_single_clause=False,
    )

    with patch("agent.nodes.decompose._call_llm", return_value=mock_result):
        state = _base_state("What is the issue size and what is the listing-day return?")
        result = decompose.run(state)

    assert len(result["sub_questions"]) >= 2


def test_decompose_single_question_passthrough():
    """Short single-clause question returns [original_question] without LLM call."""
    from agent.nodes import decompose

    question = "What is the issue size?"
    state = _base_state(question)

    # Should NOT call LLM for a short single-clause question
    with patch("agent.nodes.decompose._call_llm") as mock_call:
        result = decompose.run(state)
        mock_call.assert_not_called()

    assert result["sub_questions"] == [question]


def test_decompose_multipart_splits():
    """Compound question splits into >= 2 entries."""
    from agent.nodes import decompose
    from agent.nodes.decompose import SubQuestions

    mock_result = SubQuestions(
        questions=["What is the issue size?", "What is the listing-day return?"],
        original_is_single_clause=False,
    )

    with patch("agent.nodes.decompose._call_llm", return_value=mock_result):
        question = "What is the issue size and what is the listing-day return?"
        state = _base_state(question)
        result = decompose.run(state)

    assert len(result["sub_questions"]) >= 2
    texts = " ".join(result["sub_questions"]).lower()
    assert "issue size" in texts or "issue" in texts


def test_decompose_max_subquestions_4():
    """SubQuestions schema rejects > MAX_SUB_QUESTIONS questions (Instructor enforces)."""
    from agent.nodes.decompose import SubQuestions
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SubQuestions(
            questions=["Q1", "Q2", "Q3", "Q4", "Q5"],  # 5 > MAX_SUB_QUESTIONS (4)
            original_is_single_clause=False,
        )


def test_decompose_fallback_on_llm_error():
    """If LLM raises, decompose falls back to [original_question]."""
    from agent.nodes import decompose

    question = "What is the issue size and what is the use of proceeds?"
    state = _base_state(question)

    with patch("agent.nodes.decompose._call_llm", side_effect=RuntimeError("API error")):
        result = decompose.run(state)

    assert result["sub_questions"] == [question]


def test_decompose_max_sub_questions_constant():
    """MAX_SUB_QUESTIONS constant is 4 per RESEARCH Open Question 4."""
    assert MAX_SUB_QUESTIONS == 4
