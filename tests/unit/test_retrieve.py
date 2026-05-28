"""
Stub: tools/retriever.py + tools/reranker.py — retrieve + rerank pipeline.

Validates that:
- retrieve() returns top-k chunks with cosine similarity scores
- rerank() applies bge-reranker-v2-m3 and the output order correlates with reranker scores
- Retrieved chunks have required payload fields: drhp_id, section, page_start, page_end

Wave 3 owns this implementation (RAG-01).
"""
from __future__ import annotations

import pytest

pytest.importorskip("tools.retriever", reason="tools/retriever.py ships in Wave 3")


@pytest.mark.xfail(reason="Wave 3 owns this — implements tools/retriever.py and reranker", strict=False)
def test_retrieve_returns_topk_with_scores() -> None:
    """retrieve(query, drhp_id, limit=10) must return exactly 10 ScoredPoints,
    each with a positive float score and payload containing drhp_id, section, page_start."""
    assert False, "Wave 3 must implement: mock Qdrant, call retrieve, assert result shape"
