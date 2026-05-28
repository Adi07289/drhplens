"""
Unit tests for agent/nodes/scrub.py — banned-token scrubber node (D-09).

Distinct from test_scrubber.py which tests the pure compliance/scrubber.py function.
This file tests the LangGraph node wrapper and its D-09 retry-budget logic.
"""
from __future__ import annotations

import pytest

from agent.schemas import Claim, GroundedAnswer, RefusalResponse, RetrievedChunkRef


def _make_claim(text: str = "The issue size is ₹11,300 crores.") -> Claim:
    return Claim(
        claim_id="c_abc123",
        text=text,
        source_chunk_id="chunk_001",
        drhp_page=5,
        section="Issue Details",
        verbatim_span=text,
        span_offsets=(0, len(text)),
        sources=[
            RetrievedChunkRef(
                chunk_id="chunk_001",
                page_start=5,
                page_end=6,
                section="Issue Details",
            )
        ],
    )


def _make_grounded_answer(prose: str) -> GroundedAnswer:
    return GroundedAnswer(
        answer_prose=prose,
        claims=[_make_claim(prose[:40])],
    )


def _base_state(**overrides) -> dict:
    state = {
        "question": "What is the issue size?",
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": True,
        "gate1_max_score": 0.85,
        "sub_questions": ["What is the issue size?"],
        "grounded_answer": None,
        "scrub_passed": False,
        "scrub_failure_match": None,
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


def test_scrub_node_clean_output_passes():
    """Clean answer_prose (no banned tokens) → scrub_passed=True."""
    from agent.nodes import scrub

    state = _base_state(
        grounded_answer=_make_grounded_answer("The issue size is ₹11,300 crores."),
        regenerate_attempts=0,
    )
    result = scrub.run(state)
    assert result["scrub_passed"] is True
    assert result.get("scrub_failure_match") is None


def test_scrub_node_first_failure_increments_counter():
    """First banned-token hit: scrub_passed=False, regenerate_attempts=1."""
    from agent.nodes import scrub

    # "subscribe" is a banned token
    state = _base_state(
        grounded_answer=_make_grounded_answer("You should subscribe to this IPO."),
        regenerate_attempts=0,
    )
    result = scrub.run(state)
    assert result["scrub_passed"] is False
    assert result["regenerate_attempts"] == 1
    assert result["scrub_failure_match"] is not None
    # No refusal yet (still within retry budget)
    assert result.get("refusal") is None


def test_scrub_node_second_failure_routes_to_refusal():
    """Second banned-token hit (regenerate_attempts already 1) → refusal set."""
    from agent.nodes import scrub

    state = _base_state(
        grounded_answer=_make_grounded_answer("Investors should subscribe to this IPO."),
        regenerate_attempts=1,  # already had first failure
    )
    result = scrub.run(state)
    assert result["scrub_passed"] is False
    assert result["regenerate_attempts"] == 2
    assert result["refusal"] is not None
    assert isinstance(result["refusal"], RefusalResponse)
    assert result["refusal"].reason == "banned_token"


def test_scrub_node_calls_scrubber_on_answer_prose_only():
    """Scrub node operates on answer_prose, not on individual claim texts."""
    from agent.nodes import scrub
    from unittest.mock import patch

    state = _base_state(
        grounded_answer=_make_grounded_answer("The issue size is ₹11,300 crores."),
        regenerate_attempts=0,
    )

    with patch("agent.nodes.scrub.scrub") as mock_scrub:
        from compliance.scrubber import ScrubResult
        mock_scrub.return_value = ScrubResult(passed=True, match=None, matched_token=None)
        result = scrub.run(state)

    # Scrubber called exactly once with the answer_prose
    mock_scrub.assert_called_once_with("The issue size is ₹11,300 crores.")
