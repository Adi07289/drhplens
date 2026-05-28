"""
agent/nodes/scrub.py — Banned-token scrubber node (D-09 hard-block-and-regenerate).

Calls the pure-function scrubber from compliance/scrubber.py on the LLM's answer_prose.
Implements the retry-budget logic: first failure increments regenerate_attempts to 1
(graph routes back to generate); second failure increments to 2 (graph routes to refuse).

This node MUST NOT call the LLM. It operates entirely on state["grounded_answer"].
"""
from __future__ import annotations

from compliance.scrubber import scrub
from agent.policies import MAX_REGENERATE_ATTEMPTS
from agent.schemas import RefusalResponse
from agent.state import GraphState


def run(state: GraphState) -> GraphState:
    """Apply the deterministic banned-token scrubber to the LLM's answer prose.

    D-09 semantics:
    - First banned-token hit: increment regenerate_attempts to 1 → graph retries generate.
    - Second hit (regenerate_attempts becomes 2, exceeds MAX_REGENERATE_ATTEMPTS=1):
      additionally set state["refusal"] so the graph routes to refuse_with_reformulation.

    Args:
        state: GraphState with state["grounded_answer"].answer_prose populated.

    Returns:
        Updated GraphState with scrub_passed, scrub_failure_match, regenerate_attempts,
        and optionally refusal set.
    """
    grounded_answer = state.get("grounded_answer")
    if grounded_answer is None:
        # No answer to scrub (infrastructure_error path already set refusal)
        return {**state, "scrub_passed": True}

    result = scrub(grounded_answer.answer_prose)

    if result.passed:
        return {
            **state,
            "scrub_passed": True,
            "scrub_failure_match": None,
        }

    # Scrub failed — increment counter
    new_attempts = state.get("regenerate_attempts", 0) + 1

    updated: dict = {
        **state,
        "scrub_passed": False,
        "scrub_failure_match": result.matched_token,
        "regenerate_attempts": new_attempts,
    }

    # If attempts exceed the budget, stage a refusal (D-09 exhausted)
    if new_attempts > MAX_REGENERATE_ATTEMPTS:
        from ui import copy as ui_copy
        updated["refusal"] = RefusalResponse(
            reason="banned_token",
            explanation=ui_copy.REFUSAL_BANNED_TOKEN_COPY,
            reformulation_suggestions=[],
        )

    return updated
