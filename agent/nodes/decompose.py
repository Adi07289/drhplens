"""
agent/nodes/decompose.py — Multi-part question decomposer (D-06).

Uses Instructor + Gemini to split compound questions into atomic sub-questions.
Falls back to [original_question] if the LLM call fails.

T-1-01 mitigation: the raw user question is passed only as the user-role message.
It is never interpolated into the system-prompt scaffolding. Instructor's
SubQuestions schema bounds output to list[str] of length 1-4.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.policies import MAX_SUB_QUESTIONS
from agent.state import GraphState

# ---------------------------------------------------------------------------
# Pydantic schema for structured LLM output
# ---------------------------------------------------------------------------


class SubQuestions(BaseModel):
    """Structured output for the decompose node.

    questions: list of 1-MAX_SUB_QUESTIONS atomic sub-questions.
    original_is_single_clause: True if no split was needed.
    """

    questions: list[str] = Field(
        ...,
        min_length=1,
        max_length=MAX_SUB_QUESTIONS,
        description="Atomic sub-questions (1 to MAX_SUB_QUESTIONS)",
    )
    original_is_single_clause: bool = Field(
        ...,
        description="True iff the original question asks only one thing",
    )


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_system_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "decompose.md"
    return prompt_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# LLM client (lazy, so tests can mock without a real API key)
# ---------------------------------------------------------------------------


def _get_llm_client():
    """Return an Instructor-wrapped Gemini client.

    Requires GEMINI_API_KEY in environment at runtime.
    Tests mock this function via unittest.mock.patch.
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
            "Export it before running the agent."
        )

    genai_client = genai.Client(api_key=api_key)
    return instructor.from_genai(genai_client, mode=instructor.Mode.GENAI_JSON)


# ---------------------------------------------------------------------------
# Heuristic shortcut
# ---------------------------------------------------------------------------

_COMPOUND_MARKERS = ("and", "or", ";", "?")


def _is_likely_single_clause(question: str) -> bool:
    """Return True iff the question is short and contains no compound markers.

    This heuristic avoids a Gemini API call for the common case:
      - Length <= 60 characters
      - None of {"and", "or", ";"} present as word-boundary tokens or literals
    """
    if len(question) > 60:
        return False
    q_lower = question.lower()
    for marker in ("and", "or", ";"):
        # Word-boundary check for "and"/"or"; substring for ";"
        if marker == ";":
            if ";" in question:
                return False
        else:
            import re
            if re.search(rf"\b{marker}\b", q_lower):
                return False
    return True


# ---------------------------------------------------------------------------
# Main node function
# ---------------------------------------------------------------------------


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def _call_llm(question: str) -> SubQuestions:
    """Tenacity-retried LLM call. Separate function for testability."""
    client = _get_llm_client()
    system_prompt = _load_system_prompt()
    result = client.chat.completions.create(
        model="gemini-2.5-flash",
        response_model=SubQuestions,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    return result


def run(state: GraphState) -> GraphState:
    """Split compound questions into atomic sub-questions.

    If the question is short and has no compound markers, skip the LLM call
    and return the original question as a single-element list.

    On LLM failure after retries, falls back to [original_question].

    Args:
        state: GraphState with state["question"] populated.

    Returns:
        Updated GraphState with state["sub_questions"] as list[str].
    """
    question = state["question"]

    # Heuristic shortcut: skip LLM for obvious single-clause questions
    if _is_likely_single_clause(question):
        return {**state, "sub_questions": [question]}

    try:
        result = _call_llm(question)
        sub_questions = result.questions
    except Exception:
        # Fallback: treat as single question
        sub_questions = [question]

    return {**state, "sub_questions": sub_questions}
