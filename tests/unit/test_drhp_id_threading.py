"""
Unit test — drhp_id threads through GraphState -> intake -> retrieve -> search (V5).

Requirement: SNAP-01. Threat: V5 (input validation — drhp_id must reach search()
as a validated value, not bypass the catalogue allow-list).
Secure behavior: drhp_id flows through GraphState -> retrieve -> search; the
intake node's default preserves Phase 1 behavior when drhp_id is absent.

Wave 1 implementation (02-VALIDATION.md row "2-drhp_id-thread").
"""
from __future__ import annotations

from unittest.mock import patch

from agent.policies import DRHP_ID_DEFAULT


def _base_state(question: str = "What is the issue size?", **overrides) -> dict:
    state = {
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
    state.update(overrides)
    return state


@patch("agent.nodes.retrieve.embed_query", return_value=[0.1] * 1024)
@patch("agent.nodes.retrieve.search")
def test_drhp_id_threads_through_graph_state_to_search(mock_search, mock_embed) -> None:
    """retrieve.run invoked with an explicit drhp_id calls search() with that id."""
    from agent.nodes import retrieve

    mock_search.return_value = []
    state = _base_state(drhp_id="hyundai_2024_10")
    retrieve.run(state)

    mock_search.assert_called_once()
    call_kwargs = mock_search.call_args.kwargs
    assert call_kwargs["drhp_id"] == "hyundai_2024_10"


@patch("agent.nodes.retrieve.embed_query", return_value=[0.1] * 1024)
@patch("agent.nodes.retrieve.search")
def test_retrieve_without_drhp_id_key_falls_back_to_default(mock_search, mock_embed) -> None:
    """Phase 1 call shape {question, regenerate_attempts} still routes to DRHP_ID_DEFAULT."""
    from agent.nodes import retrieve

    mock_search.return_value = []
    # Phase 1 call shape: no drhp_id key at all.
    state = {"question": "What is the issue size?", "regenerate_attempts": 0}
    retrieve.run(state)

    mock_search.assert_called_once()
    call_kwargs = mock_search.call_args.kwargs
    assert call_kwargs["drhp_id"] == DRHP_ID_DEFAULT


def test_intake_propagates_explicit_drhp_id() -> None:
    """intake.run passes through an explicit drhp_id unchanged."""
    from agent.nodes import intake

    state = _base_state(question="  What is the issue size?  ", drhp_id="zomato_2021_07")
    result = intake.run(state)

    assert result["drhp_id"] == "zomato_2021_07"
    assert result["question"] == "What is the issue size?"


def test_intake_defaults_missing_drhp_id_to_default() -> None:
    """intake.run defaults drhp_id to DRHP_ID_DEFAULT when absent (back-compat)."""
    from agent.nodes import intake

    state = {"question": "What is the issue size?"}
    result = intake.run(state)

    assert result["drhp_id"] == DRHP_ID_DEFAULT


@patch("agent.nodes.refuse_with_reformulation.embed_query", return_value=[0.1] * 1024)
@patch("agent.nodes.refuse_with_reformulation.search_relaxed")
def test_refuse_with_reformulation_uses_state_drhp_id(mock_search_relaxed, mock_embed) -> None:
    """refuse_with_reformulation's search_relaxed call uses state['drhp_id']."""
    from agent.nodes import refuse_with_reformulation

    mock_search_relaxed.return_value = []
    state = _base_state(drhp_id="nykaa_2021_10", refusal=None)
    refuse_with_reformulation.run(state)

    mock_search_relaxed.assert_called_once()
    call_kwargs = mock_search_relaxed.call_args.kwargs
    assert call_kwargs["drhp_id"] == "nykaa_2021_10"
