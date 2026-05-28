"""
agent/nodes/retrieve.py — Dense ANN retrieval from Qdrant filtered by drhp_id.

Storage-bus invariant: this node calls storage.vector.search() (READ only).
It never calls upsert_chunks (that's the pipeline's job).
"""
from __future__ import annotations

from agent.policies import DRHP_ID_DEFAULT, RETRIEVE_LIMIT
from agent.state import GraphState
from storage.vector import search
from tools.embedder import embed_query


def run(state: GraphState) -> GraphState:
    """Embed the question and retrieve top-RETRIEVE_LIMIT chunks from Qdrant.

    Uses DRHP_ID_DEFAULT for Phase 1 single-IPO scope. Phase 2 will introduce
    dynamic drhp_id selection based on the user's chosen IPO.

    Args:
        state: GraphState with at least state["question"] populated (by intake).

    Returns:
        Updated GraphState with state["retrieved_chunks"] populated as a list
        of dicts: [{chunk_id, score, payload}].
    """
    question = state["question"]
    query_vector = embed_query(question)
    hits = search(
        query_vector=query_vector,
        drhp_id=DRHP_ID_DEFAULT,
        limit=RETRIEVE_LIMIT,
    )
    return {**state, "retrieved_chunks": hits}
