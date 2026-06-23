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

    Reads drhp_id from state (Phase 2 dynamic IPO selection). intake.run
    guarantees the key is present, defaulting to DRHP_ID_DEFAULT when the
    caller omits it — this falls back to DRHP_ID_DEFAULT defensively for any
    caller that bypasses intake (e.g. tests invoking retrieve.run directly).

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
        drhp_id=state.get("drhp_id") or DRHP_ID_DEFAULT,
        limit=RETRIEVE_LIMIT,
    )
    return {**state, "retrieved_chunks": hits}
