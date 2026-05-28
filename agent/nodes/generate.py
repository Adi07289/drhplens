"""
agent/nodes/generate.py — Instructor-validated Gemini LLM call returning GroundedAnswer.

REQUIRES GEMINI_API_KEY in environment at runtime. Import is clean without the key;
instantiation of get_llm_client() raises RuntimeError if the key is absent.

T-1-02 mitigation: system prompt (agent/prompts/generate.md) explicitly instructs
the LLM to describe advisory language neutrally. Defense in depth: scrubber (Task 3)
and cite-check (Task 3) provide additional post-output gates.

T-1-08 mitigation: _load_system_prompt() asserts the prompt itself passes the
compliance scrubber at import time — prevents a copy edit from accidentally
embedding a banned token in our own system prompt.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_exponential

from agent.schemas import GroundedAnswer, RefusalResponse
from agent.state import GraphState
from app.observability.trace_decorators import attach_claim_ids_to_span


# ---------------------------------------------------------------------------
# Prompt loading + import-time self-scrub (T-1-08 mitigation)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_system_prompt() -> str:
    """Load generate.md once and assert it passes the compliance scrubber.

    T-1-08: if a future prompt edit introduces a banned token, this import-time
    assertion will fail before any HTTP request is served.

    Returns:
        The system prompt text.

    Raises:
        AssertionError: if the prompt contains a banned token.
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "generate.md"
    text = prompt_path.read_text(encoding="utf-8")

    from compliance.scrubber import scrub
    result = scrub(text)
    assert result.passed, (
        f"agent/prompts/generate.md contains a banned token: {result.match!r}. "
        f"Fix the prompt before deploying (T-1-08 mitigation)."
    )
    return text


# ---------------------------------------------------------------------------
# LLM client singleton
# ---------------------------------------------------------------------------


def get_llm_client():
    """Return an Instructor-wrapped Gemini client (lru_cache singleton).

    Requires GEMINI_API_KEY in environment at runtime.
    Tests mock this function via unittest.mock.patch("agent.nodes.generate.get_llm_client").

    Returns:
        Instructor-wrapped google.genai client configured for structured output.

    Raises:
        RuntimeError: if GEMINI_API_KEY is not set or instructor/google-genai is missing.
    """
    try:
        import instructor
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "instructor and google-genai must be installed. "
            "Run: pip install instructor google-genai"
        ) from exc

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set in environment. "
            "Export it before running the agent: export GEMINI_API_KEY=<your-key>"
        )

    genai_client = genai.Client(api_key=api_key)
    return instructor.from_genai(genai_client, mode=instructor.Mode.GENAI_JSON)


# ---------------------------------------------------------------------------
# User message assembly
# ---------------------------------------------------------------------------


def _build_user_message(state: GraphState) -> str:
    """Assemble the user-role message sent to the LLM.

    Includes:
    1. The question or sub-questions (multi-part D-06 support).
    2. Reranked top-K chunks formatted with metadata for grounding.
    3. If this is a regeneration attempt with a scrub failure, a hard instruction
       to avoid the matched banned token.

    Args:
        state: Current GraphState.

    Returns:
        Formatted user message string.
    """
    sub_questions = state.get("sub_questions") or [state["question"]]

    if len(sub_questions) == 1:
        question_block = f"Question: {sub_questions[0]}"
    else:
        question_lines = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(sub_questions))
        question_block = f"Questions (multi-part — address each one):\n{question_lines}"

    chunks = state.get("reranked_top_k", [])
    chunk_lines = []
    for c in chunks:
        payload = c.get("payload", {})
        chunk_id = payload.get("chunk_id", c.get("id", "unknown"))
        section = payload.get("section", "Unknown Section")
        page = payload.get("printed_page_label", str(payload.get("page_start", "?")))
        text = payload.get("chunk_text", "")
        chunk_lines.append(
            f"[chunk_id={chunk_id}, section={section}, printed_page={page}]\n{text}"
        )

    context_block = "Retrieved DRHP Context:\n\n" + "\n\n---\n\n".join(chunk_lines)

    # D-09 regeneration addendum: if this is a retry due to a scrub failure
    regen_addendum = ""
    regenerate_attempts = state.get("regenerate_attempts", 0)
    scrub_failure_match = state.get("scrub_failure_match")
    if regenerate_attempts > 0 and scrub_failure_match:
        regen_addendum = (
            f"\n\nPREVIOUS ATTEMPT REJECTED: Your previous answer contained advisory language "
            f"(matched token: '{scrub_failure_match}'). "
            f"Rewrite the answer to describe what the DRHP says neutrally; "
            f"do not use any form of '{scrub_failure_match}' or similar prescriptive language. "
            f"Only describe; never advise any action."
        )

    return f"{question_block}\n\n{context_block}{regen_addendum}"


# ---------------------------------------------------------------------------
# LLM call with retry
# ---------------------------------------------------------------------------


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def _call_llm_with_retry(state: GraphState) -> GroundedAnswer:
    """Instructor-validated Gemini call with tenacity retry on transient errors.

    Instructor's own max_retries=3 handles JSON validation drift.
    Tenacity wraps the entire call for transient HTTP/quota errors.
    """
    client = get_llm_client()
    system_prompt = _load_system_prompt()
    user_message = _build_user_message(state)

    try:
        import instructor
        result = client.chat.completions.create(
            model="gemini-2.5-flash",
            response_model=GroundedAnswer,
            max_retries=3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return result
    except instructor.exceptions.InstructorRetryException:
        raise  # Let tenacity handle it, or bubble to run() for graceful refusal


# ---------------------------------------------------------------------------
# Node entry point
# ---------------------------------------------------------------------------


def run(state: GraphState) -> GraphState:
    """Invoke the LLM to generate a GroundedAnswer from the reranked context.

    On success: populates state["grounded_answer"].
    On Instructor validation failure after all retries: sets state["refusal"]
    with reason="infrastructure_error" — the graph routes to emit gracefully.
    The node MUST NOT crash the graph on LLM failure.

    Args:
        state: GraphState with reranked_top_k, sub_questions, and regenerate_attempts.

    Returns:
        Updated GraphState with either grounded_answer set (success) or
        refusal set (infrastructure error path).
    """
    try:
        grounded_answer = _call_llm_with_retry(state)
        attach_claim_ids_to_span([c.claim_id for c in grounded_answer.claims])
        return {**state, "grounded_answer": grounded_answer}
    except Exception:
        # Graceful failure: infrastructure error → refusal path (no crash)
        from ui import copy as ui_copy
        refusal = RefusalResponse(
            reason="infrastructure_error",
            explanation=ui_copy.ERROR_LLM_TIMEOUT,
            reformulation_suggestions=[],
        )
        return {**state, "refusal": refusal}
