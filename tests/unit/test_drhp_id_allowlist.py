"""
Unit test — drhp_id validated against catalogue allow-list (V5).

Requirement: SNAP-01. Threat: V5 (input validation — an unknown/unvalidated
drhp_id from session/query-param must never reach the Qdrant filter).
Secure behavior: drhp_id is validated against catalogue.json keys before
reaching search(); unknown ids are rejected.

Wave 1 implementation (02-VALIDATION.md row "2-drhp_id-allowlist").
"""
from __future__ import annotations

from unittest.mock import patch

from data.catalogue_loader import is_known_drhp_id, load_catalogue


def test_known_drhp_id_is_accepted() -> None:
    """is_known_drhp_id returns True for a catalogue-listed drhp_id."""
    load_catalogue.cache_clear()
    assert is_known_drhp_id("swiggy_2024_11") is True


def test_injection_attempt_is_rejected() -> None:
    """is_known_drhp_id returns False for an injection-style string."""
    load_catalogue.cache_clear()
    assert is_known_drhp_id("'; DROP--") is False


def test_unknown_drhp_id_is_rejected() -> None:
    """is_known_drhp_id returns False for an unrelated/unknown string."""
    load_catalogue.cache_clear()
    assert is_known_drhp_id("unknown_x") is False


def test_unknown_drhp_id_rejected_by_allowlist() -> None:
    """retrieve.run with an unknown drhp_id refuses before calling search()."""
    from agent.nodes import retrieve

    state = {
        "question": "What is the issue size?",
        "drhp_id": "unknown_x",
        "retrieved_chunks": [],
        "reranked_top_k": [],
        "gate1_passed": False,
        "gate1_max_score": 0.0,
        "sub_questions": ["What is the issue size?"],
        "grounded_answer": None,
        "scrub_passed": False,
        "regenerate_attempts": 0,
        "all_claims_grounded": False,
        "cite_check_failures": [],
        "refusal": None,
    }

    with patch("agent.nodes.retrieve.search") as mock_search:
        mock_search.side_effect = AssertionError(
            "search() must not be called for an unknown drhp_id (V5 violation)"
        )
        result = retrieve.run(state)

    mock_search.assert_not_called()
    assert result["retrieved_chunks"] == []
    assert result["refusal"] is not None
    assert result["refusal"].reason == "infrastructure_error"
