"""
agent/nodes/retrieve.py — Dense ANN retrieval from Qdrant filtered by drhp_id.

Storage-bus invariant: this node calls storage.vector.search() (READ only).
It never calls upsert_chunks (that's the pipeline's job).
"""
from __future__ import annotations

from agent.policies import DRHP_ID_DEFAULT, RETRIEVE_LIMIT
from agent.schemas import RefusalResponse
from agent.state import GraphState
from data.catalogue_loader import is_known_drhp_id
from storage.vector import search
from tools.embedder import embed_query


def run(state: GraphState) -> GraphState:
    """Embed the question and retrieve top-RETRIEVE_LIMIT chunks from Qdrant.

    Reads drhp_id from state (Phase 2 dynamic IPO selection). intake.run
    guarantees the key is present, defaulting to DRHP_ID_DEFAULT when the
    caller omits it — this falls back to DRHP_ID_DEFAULT defensively for any
    caller that bypasses intake (e.g. tests invoking retrieve.run directly).

    T-02-V5 mitigation: drhp_id is validated against the catalogue allow-list
    (data.catalogue_loader.is_known_drhp_id) BEFORE it can reach
    storage.vector.search()'s Qdrant filter. An unknown drhp_id never touches
    Qdrant — it short-circuits to a refusal with empty retrieved_chunks so the
    graph routes straight to emit.

    Args:
        state: GraphState with at least state["question"] populated (by intake).

    Returns:
        Updated GraphState with state["retrieved_chunks"] populated as a list
        of dicts: [{chunk_id, score, payload}], or a refusal if drhp_id is
        not in the catalogue allow-list.
    """
    drhp_id = state.get("drhp_id") or DRHP_ID_DEFAULT

    if not is_known_drhp_id(drhp_id):
        refusal = RefusalResponse(
            reason="infrastructure_error",
            explanation=(
                "This IPO is not in our covered catalogue. Please choose an "
                "IPO from the catalogue list."
            ),
            reformulation_suggestions=[],
        )
        return {**state, "retrieved_chunks": [], "refusal": refusal}

    question = state["question"]
    query_vector = embed_query(question)
    hits = search(
        query_vector=query_vector,
        drhp_id=drhp_id,
        limit=RETRIEVE_LIMIT,
    )
    return {**state, "retrieved_chunks": hits}
