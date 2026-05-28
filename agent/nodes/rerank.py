"""
agent/nodes/rerank.py — Cross-encoder reranking of dense retrieval results.

Calls tools.reranker.rerank() to reduce retrieved_chunks from RETRIEVE_LIMIT
(50) to RERANK_TOP_K (5) sorted by cross-encoder relevance score.
"""
from __future__ import annotations

from agent.policies import RERANK_TOP_K
from agent.state import GraphState
from tools.reranker import rerank


def run(state: GraphState) -> GraphState:
    """Rerank retrieved_chunks using bge-reranker-v2-m3.

    Attaches a "rerank_score" key to each top-K chunk dict.

    Args:
        state: GraphState with state["retrieved_chunks"] and state["question"].

    Returns:
        Updated GraphState with state["reranked_top_k"] — a list of up to
        RERANK_TOP_K chunk dicts, each extended with {"rerank_score": float}.
    """
    question = state["question"]
    chunks = state.get("retrieved_chunks", [])

    if not chunks:
        return {**state, "reranked_top_k": []}

    passages = [c.get("payload", {}).get("chunk_text", "") for c in chunks]
    ranked = rerank(question, passages, top_k=RERANK_TOP_K)

    reranked = []
    for idx, score in ranked:
        chunk = dict(chunks[idx])
        chunk["rerank_score"] = score
        reranked.append(chunk)

    return {**state, "reranked_top_k": reranked}
