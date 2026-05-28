"""
Unit tests for agent/nodes/retrieve.py, agent/nodes/rerank.py, and
agent/nodes/gate1_check.py — read-side of the LangGraph pipeline.

All external calls (Qdrant, embedder, reranker) are mocked.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.policies import DRHP_ID_DEFAULT, GATE1_THRESHOLD, RERANK_TOP_K


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_synthetic_chunks() -> list[dict]:
    fixture = Path(__file__).parent.parent / "fixtures" / "synthetic_chunks.jsonl"
    return [json.loads(line) for line in fixture.read_text().splitlines() if line.strip()]


def _make_search_hits(chunks: list[dict]) -> list[dict]:
    """Convert synthetic chunk records to the shape returned by storage.vector.search()."""
    return [
        {
            "id": c["chunk_id"],
            "score": 0.85 - i * 0.01,
            "payload": c,
        }
        for i, c in enumerate(chunks)
    ]


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


# ---------------------------------------------------------------------------
# retrieve node tests
# ---------------------------------------------------------------------------

@patch("agent.nodes.retrieve.embed_query", return_value=[0.1] * 1024)
@patch("agent.nodes.retrieve.search")
def test_retrieve_returns_topk_with_scores(mock_search, mock_embed):
    """retrieve.run returns state with 50 chunk entries (limit from policies)."""
    from agent.nodes import retrieve

    chunks = _load_synthetic_chunks()
    # Simulate 50 hits by repeating the 10 synthetic chunks 5 times
    fifty_hits = _make_search_hits(chunks * 5)
    mock_search.return_value = fifty_hits

    state = _base_state()
    result = retrieve.run(state)

    assert len(result["retrieved_chunks"]) == 50
    for chunk in result["retrieved_chunks"]:
        assert "id" in chunk or "chunk_id" in chunk.get("payload", {})
        assert "score" in chunk
        assert "payload" in chunk


@patch("agent.nodes.retrieve.embed_query", return_value=[0.1] * 1024)
@patch("agent.nodes.retrieve.search")
def test_retrieve_includes_drhp_id_filter(mock_search, mock_embed):
    """retrieve.run calls storage.vector.search with drhp_id=DRHP_ID_DEFAULT."""
    from agent.nodes import retrieve

    mock_search.return_value = []
    state = _base_state()
    retrieve.run(state)

    mock_search.assert_called_once()
    call_kwargs = mock_search.call_args
    # Accept both positional and keyword args
    kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
    args = call_kwargs.args if call_kwargs.args else ()
    # drhp_id should be passed; check kwargs or positional arg index 1
    if "drhp_id" in kwargs:
        assert kwargs["drhp_id"] == DRHP_ID_DEFAULT
    else:
        # positional: search(query_vector, drhp_id, limit)
        assert args[1] == DRHP_ID_DEFAULT


# ---------------------------------------------------------------------------
# rerank node tests
# ---------------------------------------------------------------------------

@patch("agent.nodes.rerank.rerank")
def test_rerank_reduces_to_top_k(mock_rerank):
    """rerank.run reduces 50 retrieved chunks to RERANK_TOP_K entries."""
    from agent.nodes import rerank

    chunks = _load_synthetic_chunks()
    fifty_hits = _make_search_hits(chunks * 5)

    # Mock reranker returns top-5 indices with scores
    mock_rerank.return_value = [(i, 0.9 - i * 0.05) for i in range(RERANK_TOP_K)]

    state = {**_base_state(), "retrieved_chunks": fifty_hits}
    result = rerank.run(state)

    assert len(result["reranked_top_k"]) == RERANK_TOP_K
    # Scores should be descending
    scores = [c["rerank_score"] for c in result["reranked_top_k"]]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# gate1_check node tests
# ---------------------------------------------------------------------------

def test_gate1_passes_when_top_score_above_threshold():
    """gate1_check.run sets gate1_passed=True when top score >= GATE1_THRESHOLD."""
    from agent.nodes import gate1_check

    state = {
        **_base_state(),
        "reranked_top_k": [{"chunk_id": "c1", "rerank_score": 0.85}],
    }
    result = gate1_check.run(state)
    assert result["gate1_passed"] is True


def test_gate1_fails_when_top_score_below_threshold():
    """gate1_check.run sets gate1_passed=False when max score < GATE1_THRESHOLD."""
    from agent.nodes import gate1_check

    state = {
        **_base_state(),
        "reranked_top_k": [{"chunk_id": "c1", "rerank_score": -1.0}],
    }
    result = gate1_check.run(state)
    assert result["gate1_passed"] is False


def test_gate1_stores_max_score():
    """gate1_check.run stores gate1_max_score for Langfuse trace consumers (Wave 5)."""
    from agent.nodes import gate1_check

    state = {
        **_base_state(),
        "reranked_top_k": [
            {"chunk_id": "c1", "rerank_score": 0.7},
            {"chunk_id": "c2", "rerank_score": 0.85},
            {"chunk_id": "c3", "rerank_score": 0.6},
        ],
    }
    result = gate1_check.run(state)
    assert result["gate1_max_score"] == pytest.approx(0.85)
