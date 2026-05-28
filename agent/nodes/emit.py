"""
agent/nodes/emit.py — Terminal node for both happy-path and refusal-path.

Pure passthrough: does not transform answer_prose or refusal messages.
The {{claim_id}} placeholders in answer_prose are preserved for the Wave 4
renderer (ui/citation_chip.py) to resolve into numbered superscript chips.

This node is the graph's END marker for all paths.
"""
from __future__ import annotations

from agent.state import GraphState


def run(state: GraphState) -> GraphState:
    """Pass state through to the graph END.

    If state["refusal"] is set, the refusal is the emit payload.
    If state["grounded_answer"] is set and all_claims_grounded is True,
    the grounded answer is the emit payload.

    In both cases, no transformation is applied here. The Wave 4 Streamlit
    renderer reads the output state and renders appropriately.

    Args:
        state: Final GraphState after all gates.

    Returns:
        State unchanged (emit is a passthrough terminal node).
    """
    # No transformation — Wave 4 renderer owns the output shape
    return state
