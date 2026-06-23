"""
agent/nodes/refuse_with_reformulation.py — Shared terminal refusal node.

All three refusal paths (Gate 1 low_retrieval_score, Gate 2 unsupported_claim,
scrub-exhausted banned_token) converge here for consistent UX.

Per RESEARCH Open Question 5: NO LLM call. Pure deterministic:
1. Embed the question.
2. search_relaxed() with no score threshold, limit=RELAXED_SEARCH_LIMIT.
3. Take top-2 unique section names as reformulation chips.
4. Build the RefusalResponse message from ui.copy templates.

T-1-01 mitigation: the user's question is embedded and used only as a Qdrant
query vector — never interpolated into a system prompt.
T-1-14 mitigation: chip values are DRHP section names (public data from the
filed prospectus) — no PII or secret leakage surface.

DO NOT add any import for openai, genai, instructor, or groq to this file.
This node is LLM-free by design (Open Question 5 decision).
"""
from __future__ import annotations

from agent.policies import (
    DRHP_ID_DEFAULT,
    RELAXED_SEARCH_LIMIT,
    RELAXED_SEARCH_TOP_SECTIONS,
)
from app.observability.trace_decorators import attach_refusal_reason_to_trace
from agent.schemas import RefusalResponse
from agent.state import GraphState
from storage.vector import search_relaxed
from tools.embedder import embed_query
from ui.copy import REFUSAL_BANNED_TOKEN_COPY, REFUSAL_NO_GROUNDING_TEMPLATE


def _top_unique_sections(hits: list[dict], k: int = RELAXED_SEARCH_TOP_SECTIONS) -> list[str]:
    """Return the top-k unique section names from the search hits in order.

    Iterates hits (assumed already sorted by relevance score descending from
    search_relaxed) and collects unique section values until we have k of them.

    Args:
        hits: List of Qdrant hit dicts with payload containing "section".
        k: Maximum number of unique sections to return.

    Returns:
        List of unique section name strings (length 0..k).
    """
    seen: set[str] = set()
    result: list[str] = []
    for hit in hits:
        section = hit.get("payload", {}).get("section", "")
        if section and section not in seen:
            seen.add(section)
            result.append(section)
            if len(result) >= k:
                break
    return result


def run(state: GraphState) -> GraphState:
    """Enrich the refusal response with reformulation suggestions.

    Idempotent: if refusal already has suggestions + message, return unchanged.

    Steps:
    1. Idempotency guard.
    2. Embed the original question.
    3. search_relaxed() — no score threshold per Open Question 5.
    4. Compute top unique section suggestions.
    5. Determine reason (preserve upstream reason if already set).
    6. Build message from ui.copy templates.
    7. Set state["refusal"].

    Args:
        state: GraphState with optional pre-populated state["refusal"].

    Returns:
        Updated GraphState with state["refusal"] fully populated.
    """
    existing_refusal = state.get("refusal")

    # Idempotency guard: if already fully populated, skip
    if (
        existing_refusal is not None
        and existing_refusal.reformulation_suggestions
        and existing_refusal.explanation
    ):
        return state

    # Step 1: Determine reason (preserve upstream or default to low_retrieval_score)
    if existing_refusal is not None:
        reason = existing_refusal.reason
    else:
        reason = "low_retrieval_score"

    # Step 2 & 3: Embed + relaxed search (skip for banned_token — user question was fine)
    suggestions: list[str] = []
    if reason != "banned_token":
        try:
            qv = embed_query(state["question"])
            hits = search_relaxed(
                query_vector=qv,
                drhp_id=state.get("drhp_id") or DRHP_ID_DEFAULT,
                limit=RELAXED_SEARCH_LIMIT,
            )
            suggestions = _top_unique_sections(hits, RELAXED_SEARCH_TOP_SECTIONS)
        except Exception:
            # If embedding/search fails, proceed with empty suggestions
            suggestions = []

    # Step 4: Build message
    if reason == "banned_token":
        message = REFUSAL_BANNED_TOKEN_COPY
        suggestions = []  # No reformulation chips for banned-token refusals
    else:
        s1 = suggestions[0] if len(suggestions) >= 1 else ""
        s2 = suggestions[1] if len(suggestions) >= 2 else s1
        if s1:
            message = REFUSAL_NO_GROUNDING_TEMPLATE.format(
                topic=state["question"],
                suggestion1=s1,
                suggestion2=s2 if s2 else s1,
            )
        else:
            message = (
                f"This DRHP does not contain sufficient information to answer "
                f"your question about '{state['question']}'."
            )

    # Step 5: Set refusal
    refusal = RefusalResponse(
        reason=reason,
        explanation=message,
        reformulation_suggestions=suggestions,
    )

    # Attach failure-mode taxonomy to Langfuse trace (no-op when disabled).
    attach_refusal_reason_to_trace(reason)

    return {**state, "refusal": refusal}
