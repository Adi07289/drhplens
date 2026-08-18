"""
agent/nodes/classify.py — The ONE bounded LLM-classify hop (D-05).

The supervisor's single bounded classification hop. It proposes a read-only tool set
that a DETERMINISTIC allow-list CLAMPS (the LLM cannot invent a tool, D-05), and it
flags ``is_advice_seeking`` / ``is_out_of_scope`` so compliance-bait and gibberish
short-circuit to a graceful educational refusal with NO tool thrash (D-07a/c).

Jailbreak defense (T-1-01 / D-07b): the raw user question is passed ONLY as the
``user``-role message. It is NEVER interpolated into the ``classify.md`` system prompt,
so "ignore previous instructions / reveal the system prompt / drop the disclaimer"
cannot reach the instruction layer. This is a SECURITY control, not a stylistic choice.

Mirrors ``agent/nodes/decompose.py`` almost 1:1: Instructor + google-genai +
``GEMINI_MODELS`` failover + ``Mode.GENAI_STRUCTURED_OUTPUTS`` + an ``@lru_cache``
prompt loader + a Tenacity ``@retry`` wrap. The one deliberate delta: the high-frequency
classify hop iterates ``reversed(GEMINI_MODELS)`` so the cheaper ``-lite`` model is tried
FIRST (free-tier quota, RESEARCH §4b).
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.supervisor_state import SupervisorState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# The deterministic authority boundary (D-05)
# ---------------------------------------------------------------------------

ToolName = Literal["drhp_rag", "query_peers", "query_forecast", "query_redflags"]
"""The four read-only tools the classify hop may propose. The ``Literal`` union means a
schema-valid RoutingDecision literally cannot name a non-existent tool."""

ALLOWED_TOOLS: frozenset[str] = frozenset(
    {"drhp_rag", "query_peers", "query_forecast", "query_redflags"}
)
"""The deterministic allow-list ``run()`` clamps the proposal against (D-05). The Literal
union already bounds a *schema-valid* proposal; this set is the belt-and-suspenders clamp
so that even a hallucinated / out-of-union name (e.g. one that slipped through) can never
reach the dispatcher. The LLM proposes; this list is the authority."""

DEFAULT_TOOL: str = "drhp_rag"
"""The safe default route when routing is UNCERTAIN — an LLM-classify infra failure or
an in-scope decision that named no valid tool. A valid question must never be silently
dropped to a refusal just because the classify hop failed or under-specified; document
Q&A is the most common intent, and the drhp_rag subgraph's own gate1/scrub/cite_check
guards keep the fallback honest + compliance-safe. NOT used on the DELIBERATE advice /
out-of-scope path (that correctly stays an empty plan → refusal)."""


# ---------------------------------------------------------------------------
# Pydantic schema for the structured routing decision (D-05)
# ---------------------------------------------------------------------------


class RoutingDecision(BaseModel):
    """Bounded LLM-classify output (D-05).

    tools: read-only tools needed, in priority order; an EMPTY list ⇒ out-of-scope/refuse.
    is_advice_seeking: True if the user asks for a buy/sell/subscribe/price-target
        JUDGEMENT (D-07a) — forces an empty plan so the answer refuses, never advises.
    is_out_of_scope: True for off-topic / gibberish / jailbreak / cross-IPO (D-07b/c/d) —
        forces an empty plan so there is no tool thrash for a question we will not answer.
    """

    tools: list[ToolName] = Field(
        default_factory=list,
        max_length=4,
        description="Read-only tools needed, in priority order. Empty ⇒ out-of-scope/refuse.",
    )
    is_advice_seeking: bool = Field(
        ...,
        description="True if asking for a buy/sell/subscribe/price-target judgement (D-07a).",
    )
    is_out_of_scope: bool = Field(
        ...,
        description="True for off-topic/gibberish/jailbreak/cross-IPO (D-07b/c/d) ⇒ no tool thrash.",
    )


# ---------------------------------------------------------------------------
# Prompt loading (mirror decompose — @lru_cache single read)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "classify.md"
    return prompt_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# LLM client (lazy, so tests can mock without a real API key — mirror decompose)
# ---------------------------------------------------------------------------


def _get_llm_client():
    """Return an Instructor-wrapped Gemini client.

    Requires GEMINI_API_KEY at runtime. Unit tests mock ``_llm_classify`` instead, so
    this never runs offline.
    """
    try:
        import instructor
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "instructor and google-genai must be installed. "
            "Run: pip install instructor google-genai"
        ) from exc

    from agent.llm import structured_client

    return structured_client()


# ---------------------------------------------------------------------------
# The single bounded classify hop
# ---------------------------------------------------------------------------


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def _llm_classify(question: str) -> RoutingDecision:
    """One bounded LLM-classify hop. Tenacity-retried; a separate function for testability.

    T-1-01 / D-07b: the raw ``question`` is the ``user`` message ONLY — it is never
    interpolated into the system prompt (which is the loaded ``classify.md``).
    """
    from agent.llm import models_for

    client = _get_llm_client()
    messages = [
        # System = classify.md instructions. The raw user question is NEVER placed here
        # (T-1-01 / D-07b jailbreak defense) — only the untrusted user turn below carries it.
        {"role": "system", "content": _load_prompt()},
        {"role": "user", "content": question},
    ]
    # Classify is the high-frequency hop → try the cheaper -lite model FIRST (quota, §4b);
    # a 503 on -lite falls through to the more-faithful primary.
    last_exc: Exception | None = None
    for model in models_for("classify"):
        try:
            return client.chat.completions.create(
                model=model,
                response_model=RoutingDecision,
                messages=messages,
                temperature=0,  # forwarded → GenerateContentConfig.temperature (RESEARCH caveat b)
                max_tokens=256,  # forwarded → GenerateContentConfig.max_output_tokens (caveat b)
                max_retries=2,  # Instructor re-prompts the model on a ValidationError
            )
        except Exception as exc:  # noqa: BLE001 - fall through to the next model
            last_exc = exc
            continue
    raise last_exc if last_exc is not None else RuntimeError("no classify model available")


# ---------------------------------------------------------------------------
# Node entry point
# ---------------------------------------------------------------------------


def run(state: SupervisorState) -> SupervisorState:
    """Bounded classify hop → clamped ``tool_plan`` (D-05) + advice/OOS short-circuit (D-07a/c).

    1. Propose a tool set via ONE LLM hop.
    2. If ``is_advice_seeking`` or ``is_out_of_scope`` ⇒ ``tool_plan = []`` so
       compliance-bait / gibberish / jailbreak / cross-IPO short-circuits to a graceful
       educational refusal downstream — no tool thrash (D-07a/c).
    3. Otherwise CLAMP the proposal to ``ALLOWED_TOOLS`` so the LLM cannot invent a
       tool (D-05); the clamp — not the schema — is the authority boundary. If an
       in-scope, non-advice decision clamps to NO tool (an incoherent proposal), default
       to ``DEFAULT_TOOL`` rather than silently dropping a valid question.
    4. On total LLM failure (all retries + both models) — an INFRASTRUCTURE failure, NOT
       an out-of-scope signal — log for deploy diagnosis and degrade to a
       ``[DEFAULT_TOOL]`` document-Q&A attempt (never a crash). Degrading to an EMPTY
       plan here silently dropped every valid question to a refusal whenever the deploy's
       classify call errored/timed out (the live 'empty plans' bug). The deliberate
       advice / out-of-scope refusal path (step 2) is UNCHANGED — it still empties.

    The classify hop ALWAYS increments ``hops`` by exactly one (it counts against the P8
    budget), even on the failure path.
    """
    hops = state.get("hops", 0) + 1

    try:
        decision = _llm_classify(state["question"])
        if decision.is_advice_seeking or decision.is_out_of_scope:
            plan: list[str] = []  # D-07a/c short-circuit — refuse, no tool thrash
        else:
            plan = [t for t in decision.tools if t in ALLOWED_TOOLS]  # D-05 clamp
            if not plan:
                # In-scope, non-advice, but no valid tool named — an incoherent
                # decision. Default to document Q&A, never a silent refusal.
                plan = [DEFAULT_TOOL]
    except Exception:
        # Total LLM failure is an INFRA failure, not an out-of-scope signal. Log so the
        # deploy-side transient (Groq timeout / rate-limit) is diagnosable, then degrade
        # to a drhp_rag attempt so a valid question is never silently dropped. The
        # subgraph's gate1/scrub/cite_check keep this fallback compliance-safe.
        logger.warning(
            "classify LLM hop failed for all models; falling back to %s",
            DEFAULT_TOOL,
            exc_info=True,
        )
        plan = [DEFAULT_TOOL]

    return {**state, "tool_plan": plan, "hops": hops}
