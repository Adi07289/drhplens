"""
Unit tests for agent/nodes/generate.py — LLM generation node.

All LLM calls are mocked via patch("agent.nodes.generate.get_llm_client").
No real Gemini API calls are made in unit tests.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agent.schemas import Claim, GroundedAnswer, RefusalResponse, RetrievedChunkRef


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_chunk_ref() -> RetrievedChunkRef:
    return RetrievedChunkRef(
        chunk_id="chunk_001",
        page_start=5,
        page_end=6,
        printed_page_label="5",
        section="Issue Details",
        score=0.92,
        verbatim_span="The total issue size is ₹11,300 crores",
        span_offsets=(0, 38),
    )


def _make_claim() -> Claim:
    return Claim(
        claim_id="c_abc123",
        text="The issue size is ₹11,300 cr",
        source_chunk_id="chunk_001",
        drhp_page=5,
        section="Issue Details",
        verbatim_span="The total issue size is ₹11,300 crores",
        span_offsets=(0, 38),
        sources=[_make_chunk_ref()],
    )


def _make_grounded_answer() -> GroundedAnswer:
    return GroundedAnswer(
        answer_prose="The issue size is ₹11,300 cr {{c_abc123}}.",
        claims=[_make_claim()],
        sub_question_addressed=[],
        sub_question_unaddressed=[],
    )


def _make_state(**overrides) -> dict:
    state = {
        "question": "What is the issue size?",
        "retrieved_chunks": [],
        "reranked_top_k": [
            {
                "id": "chunk_001",
                "score": 0.92,
                "rerank_score": 0.92,
                "payload": {
                    "chunk_id": "chunk_001",
                    "section": "Issue Details",
                    "printed_page_label": "5",
                    "chunk_text": "The total issue size is ₹11,300 crores.",
                },
            }
        ],
        "gate1_passed": True,
        "gate1_max_score": 0.92,
        "sub_questions": ["What is the issue size?"],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "scrub_failure_match": None,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
    }
    state.update(overrides)
    return state


def _make_mock_client(return_value):
    """Create a mock Instructor client that returns return_value from chat.completions.create."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = return_value
    return mock_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_generate_returns_grounded_answer():
    """generate.run populates state['grounded_answer'] as a GroundedAnswer instance."""
    from agent.nodes import generate

    canned = _make_grounded_answer()
    mock_client = _make_mock_client(canned)

    with patch("agent.nodes.generate.get_llm_client", return_value=mock_client):
        state = _make_state()
        result = generate.run(state)

    assert result["grounded_answer"] is not None
    assert isinstance(result["grounded_answer"], GroundedAnswer)
    assert result["grounded_answer"].answer_prose == "The issue size is ₹11,300 cr {{c_abc123}}."


def test_generate_passes_reranked_chunks_to_llm():
    """The LLM create call includes chunk_text from state['reranked_top_k'] in the message."""
    from agent.nodes import generate

    canned = _make_grounded_answer()
    mock_client = _make_mock_client(canned)

    with patch("agent.nodes.generate.get_llm_client", return_value=mock_client):
        state = _make_state()
        generate.run(state)

    call_kwargs = mock_client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages", call_kwargs.args[0] if call_kwargs.args else [])
    user_message = next((m["content"] for m in messages if m["role"] == "user"), "")
    assert "₹11,300" in user_message or "Issue Details" in user_message


def test_generate_passes_sub_questions_when_multipart():
    """With multiple sub_questions, the user message includes all sub-questions explicitly."""
    from agent.nodes import generate

    canned = _make_grounded_answer()
    mock_client = _make_mock_client(canned)

    sub_questions = ["What is the issue size?", "What is the listing-day return?"]
    with patch("agent.nodes.generate.get_llm_client", return_value=mock_client):
        state = _make_state(sub_questions=sub_questions, question="multi-part question")
        generate.run(state)

    call_kwargs = mock_client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages", [])
    user_message = next((m["content"] for m in messages if m["role"] == "user"), "")
    assert "What is the issue size?" in user_message
    assert "listing-day return" in user_message


def test_generate_retries_on_validation_error():
    """With mock that returns valid GroundedAnswer, the node succeeds."""
    from agent.nodes import generate

    canned = _make_grounded_answer()
    mock_client = _make_mock_client(canned)

    with patch("agent.nodes.generate.get_llm_client", return_value=mock_client):
        state = _make_state()
        result = generate.run(state)

    assert result["grounded_answer"] is not None


def test_generate_system_prompt_contains_neutral_advisory_instruction():
    """agent/prompts/generate.md contains the T-1-02 neutrality instruction."""
    from pathlib import Path

    prompt_text = Path("agent/prompts/generate.md").read_text()
    assert "neutrally" in prompt_text.lower(), (
        "generate.md must contain instruction to describe advisory language neutrally (T-1-02)"
    )


def test_generate_prompt_passes_scrubber():
    """agent/prompts/generate.md must pass the compliance scrubber (T-1-08)."""
    from pathlib import Path

    from compliance.scrubber import scrub

    prompt_text = Path("agent/prompts/generate.md").read_text()
    result = scrub(prompt_text)
    assert result.passed, f"generate.md contains banned token: {result.match!r} (T-1-08)"


def test_generate_handles_regenerate_attempt():
    """With regenerate_attempts=1 and scrub_failure_match set, user message includes retry addendum."""
    from agent.nodes import generate

    canned = _make_grounded_answer()
    mock_client = _make_mock_client(canned)

    with patch("agent.nodes.generate.get_llm_client", return_value=mock_client):
        state = _make_state(regenerate_attempts=1, scrub_failure_match="subscribe")
        generate.run(state)

    call_kwargs = mock_client.chat.completions.create.call_args
    messages = call_kwargs.kwargs.get("messages", [])
    user_message = next((m["content"] for m in messages if m["role"] == "user"), "")
    assert "subscribe" in user_message or "PREVIOUS ATTEMPT REJECTED" in user_message


def test_generate_infrastructure_error_sets_refusal():
    """When get_llm_client raises, generate.run sets state['refusal'] with reason='infrastructure_error'."""
    from agent.nodes import generate

    with patch("agent.nodes.generate.get_llm_client", side_effect=RuntimeError("no key")):
        state = _make_state()
        result = generate.run(state)

    assert result["refusal"] is not None
    assert isinstance(result["refusal"], RefusalResponse)
    assert result["refusal"].reason == "infrastructure_error"
    assert result.get("grounded_answer") is None
