"""
Stub: integration test — LangGraph agent end-to-end grounded answer (RAG-01, RAG-02, RAG-03, TRUST-04).

Validates the full agent loop:
- ask "What is Swiggy's issue size?" → GroundedAnswer with >= 1 claim, all claims cite-checked
- ask "What does Swiggy say about Mars?" → RefusalResponse with reformulation suggestions
- Every claim in the grounded answer has claim_id matching ^c_[a-z0-9]{6,16}$

Wave 3 owns this implementation (RAG-01, RAG-02, RAG-03, TRUST-04; T-1-01, T-1-02 mitigation).
"""
from __future__ import annotations

import pytest

pytest.importorskip("agent.graph", reason="agent/graph.py ships in Wave 3")


@pytest.mark.xfail(reason="Wave 3 owns this — implements full LangGraph agent and e2e test", strict=False)
def test_grounded_question_returns_cited_answer(mock_qdrant_client, mock_llm) -> None:
    """Agent invoked with 'What is Swiggy's issue size?' must return a GroundedAnswer
    where every claim passes cite_check and has a valid claim_id."""
    assert False, "Wave 3 must implement: build graph, invoke with fixture question, assert GroundedAnswer"
