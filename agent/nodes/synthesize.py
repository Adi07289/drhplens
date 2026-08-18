"""
agent/nodes/synthesize.py — the terminal synthesis node (D-03/D-04/D-08).

This is the bounded supervisor's LAST node: whatever the router forwarded (a
DRHP-grounded answer, a set of read-only tool results, a budget-trip, or an empty
out-of-scope plan), synthesize composes ONE honestly-labelled, scrubber-clean,
disclaimered answer object for the renderer.

Two paths compose an answer:

    * Multi-tool FUSION path (this plan, 06.3-06) — ``tool_results`` carry structured
      records: run ONE fusion LLM hop (``_llm_fuse`` → Instructor + Gemini → a
      ``FusedAnswer``) that weaves the DRHP ``grounded_answer`` + the peer / forecast
      band / GMP-vs-model gap / red-flag records into ONE cited paragraph where every
      number carries a ``Claim`` (DRHP span) or a ``ToolClaim`` (source_tool /
      source_record_id). Then RE-SCRUB (block, never a fabricated rewrite), run the
      EXTENDED cite-check (``cite_check.partition_fused_claims`` — Claim → DRHP span
      unchanged; ToolClaim → reconcile the number against its committed source record)
      and DROP any unresolved number (FM-3), inject the disclaimer, and set
      ``is_partial`` on any tool abstain/error or budget-trip (D-08).

    * DRHP-only path (06.3-05) — the embedded ``drhp_rag`` sub-agent produced a
      ``grounded_answer`` and NO tool records: RE-APPLY ``compliance.scrubber.scrub``,
      rely on the subgraph's EXISTING deterministic cite-check result
      (``all_claims_grounded``) for ``Claim`` grounding (the cite-check is NOT forked,
      D-03), inject the disclaimer, set ``is_partial``. ZERO live LLM on this path.

Honest-partial + refusal paths are unchanged from 06.3-05: an UNFINISHED plan with
nothing grounded returns a labelled partial (D-06/D-08); an empty plan with nothing
grounded surfaces the educational refusal — never fabricating an answer.

Jailbreak defense (T-1-01 / D-07b): the raw user question is passed to the fusion hop
ONLY as the ``user``-role message; the trusted tool CONTEXT rides the system message,
never the user question into the instruction layer. Compliance boundary (mirrors
``scrub.py`` / ``emit.py``): the scrubber and the disclaimer are re-applied AFTER
generation, so no prompt can strip them (D-07b).
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_exponential

from compliance.disclaimer_text import ANCHOR_COPY, PER_ANSWER_FOOTER
from compliance.scrubber import scrub

from agent.cache.semantic_cache import cached_answer
from agent.nodes.cite_check import partition_fused_claims
from agent.schemas import FusedAnswer, RefusalResponse
from agent.supervisor_state import SupervisorState

# ---------------------------------------------------------------------------
# Deterministic honest-partial copy (D-08) — no fabrication, no banned token.
# scrubber-clean by construction; pp-002 in the D-09 stress suite re-scrubs this.
# ---------------------------------------------------------------------------

HONEST_PARTIAL_PROSE: str = (
    "This answer is incomplete: the run reached its step budget before every part "
    "of your question could be gathered. Nothing here is filled in with a guess — "
    "the parts left uncovered are listed so the gap is explicit."
)

_UNADDRESSED_BUDGET: str = "ran out of steps before finishing"

# The fusion hop's explicit output-token budget — never unbounded (a free-tier quota
# AND latency risk, AI-SPEC §4b). Bounded to a fused-answer length.
_FUSION_MAX_TOKENS: int = 2048


# ---------------------------------------------------------------------------
# Disclaimer injection (D-07/D-08) — the post-generation compliance surface.
# ---------------------------------------------------------------------------


def _disclaimer() -> str:
    """The per-answer disclaimer string injected AFTER generation (cannot be
    prompt-stripped, D-07b). Carries the D-07 anchor copy + the per-answer footer
    substring the renderer + the D-09 stress suite assert is present."""
    return f"{ANCHOR_COPY} {PER_ANSWER_FOOTER}"


# ---------------------------------------------------------------------------
# Re-scrub (D-09 posture re-applied) + refusal shells.
# ---------------------------------------------------------------------------


def _rescrub_passed(prose: str) -> bool:
    """Re-apply the SAME deterministic banned-token scrubber to the answer prose.

    Synthesis is a post-hoc belt-and-suspenders re-scrub. There is NO regen-in-place
    here, so a banned token that still survives to synthesize BLOCKS to a refusal
    rather than fabricating a clean rewrite (honesty invariant)."""
    return scrub(prose).passed


def _banned_token_refusal() -> RefusalResponse:
    """The refusal shown when a banned token survives to synthesis (D-09 exhausted)."""
    from ui import copy as ui_copy  # lazy (mirror scrub.py) — avoids import cycles

    return RefusalResponse(
        reason="banned_token",
        explanation=ui_copy.REFUSAL_BANNED_TOKEN_COPY,
        reformulation_suggestions=[],
    )


def _educational_refusal() -> RefusalResponse:
    """The graceful educational refusal for an empty (out-of-scope / advice-bait /
    jailbreak / cross-IPO) plan (D-07a/b/c/d). Reuses the single scrubber-clean
    ``REFUSAL_BANNED_TOKEN_COPY`` (PATTERNS: do NOT add a new advice-adjacent
    string) — "DRHPLens describes; it doesn't advise"."""
    from ui import copy as ui_copy  # lazy (mirror scrub.py)

    return RefusalResponse(
        reason="unsupported_claim",
        explanation=ui_copy.REFUSAL_NO_ANSWER_COPY,
        reformulation_suggestions=[],
    )


# ---------------------------------------------------------------------------
# Multi-tool FUSION hop (06.3-06) — Instructor + Gemini → FusedAnswer.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_prompt() -> str:
    """Load the fusion system prompt (describe-never-conclude, per-number provenance,
    D-04 GMP caveat). Read once, mirroring ``decompose`` / ``classify``."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "synthesize.md"
    return prompt_path.read_text(encoding="utf-8")


def _get_fusion_client():
    """Return an Instructor-wrapped Gemini client (lazy; tests mock ``_llm_fuse`` /
    ``_get_fusion_client`` so this never runs offline). Requires GEMINI_API_KEY."""
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


def _build_fusion_context(state: SupervisorState) -> str:
    """Serialize the TRUSTED fusion input — the DRHP grounded answer + the committed
    tool records — into the system-message context block (never the user turn).

    Every number the model may write must trace back to one of these records; the
    prompt instructs it to attach ``source_record_id`` accordingly (D-03).
    """
    parts: list[str] = []
    grounded = state.get("grounded_answer")
    if grounded is not None:
        try:
            parts.append(
                "DRHP-GROUNDED ANSWER (already cite-checked; keep its {{claim_id}} "
                "markers + spans verbatim):\n" + grounded.model_dump_json()
            )
        except Exception:  # noqa: BLE001 - defensive; context is best-effort text
            parts.append("DRHP-GROUNDED ANSWER:\n" + str(grounded))
    tool_results = state.get("tool_results", []) or []
    if tool_results:
        parts.append(
            "TOOL RECORDS (committed artifacts; every tool-derived number MUST trace "
            "to one of these via source_tool + source_record_id):\n"
            + json.dumps(tool_results, ensure_ascii=False, default=str)
        )
    return "\n\n".join(parts)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def _call_fusion_llm(question: str, context: str) -> FusedAnswer:
    """The single faithfulness-critical fusion hop (Instructor + Gemini).

    Reserves the primary ``gemini-3.5-flash`` FIRST (it grounds numbers more
    faithfully), falling through ``GEMINI_MODELS`` on a 503. T-1-01/D-07b: the raw user
    question is the ``user`` message ONLY — never interpolated into the instruction /
    context layer; the trusted tool context rides the ``system`` message.
    ``temperature=0`` keeps numbers from paraphrase-drifting off their source records
    (D-03); ``max_tokens`` is always explicit (never unbounded — §4b).
    """
    client = _get_fusion_client()
    system = _load_prompt()
    if context:
        system = f"{system}\n\n---\nFUSION CONTEXT (trusted; NOT user input):\n{context}"
    messages = [
        # The raw user question is ONLY the user turn (T-1-01) — never the system layer.
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    from agent.llm import models_for

    last_exc: Exception | None = None
    for model in models_for("synthesize"):  # main tier: 70B first, 8B fallback
        try:
            return client.chat.completions.create(
                model=model,
                response_model=FusedAnswer,
                messages=messages,
                temperature=0,  # → GenerateContentConfig.temperature (RESEARCH caveat b)
                max_tokens=_FUSION_MAX_TOKENS,  # → max_output_tokens (caveat b)
                max_retries=2,  # Instructor re-prompts the model on a ValidationError
            )
        except Exception as exc:  # noqa: BLE001 - fall through to the next model
            last_exc = exc
            continue
    raise last_exc if last_exc is not None else RuntimeError("no fusion model available")


def _llm_fuse(state: SupervisorState) -> FusedAnswer:
    """Fuse ``tool_results`` (+ any ``grounded_answer``) into ONE cited FusedAnswer.

    Runs the faithfulness-critical fusion hop (``_call_fusion_llm``) through the D-06
    semantic cache keyed by ``(drhp_id, question)`` — two near-identical questions
    should not each burn a Gemini call against the tight free-tier RPD. The cache is a
    best-effort quota optimizer: if the embedder is unavailable it computes directly.

    The offline D-09 stress suite + the fusion unit tests patch this symbol
    (``patch("agent.nodes.synthesize._llm_fuse", ...)``) with a deterministic
    ``FusedAnswer`` so the post-processing envelope (re-scrub + extended cite-check +
    disclaimer + ``is_partial``) is exercised without a live LLM.
    """
    question = state.get("question", "")
    drhp_id = state.get("drhp_id", "") or ""
    context = _build_fusion_context(state)

    def _compute() -> FusedAnswer:
        return _call_fusion_llm(question, context)

    try:
        from tools.embedder import embed_query  # reuse the already-loaded bge-m3

        return cached_answer(drhp_id, question, embed_query, _compute)
    except Exception:  # noqa: BLE001 - the cache is a quota optimizer, never a hard dep
        return _compute()


# ---------------------------------------------------------------------------
# Extended cite-check plumbing for the fused answer (D-03, FM-3).
# ---------------------------------------------------------------------------


def _retrieved_chunks(state: SupervisorState) -> dict[str, str]:
    """Build the ``chunk_id → chunk_text`` map the DRHP ``Claim`` cite-check needs.

    Mirrors ``cite_check.run``'s reranked→dict step so a fused DRHP ``Claim`` grounds
    against the same reranked top-k the subgraph produced (the ``ToolClaim`` branch
    ignores this and reconciles against ``tool_results`` instead)."""
    chunks: dict[str, str] = {}
    for chunk in state.get("reranked_top_k", []) or []:
        if not isinstance(chunk, dict):
            continue
        payload = chunk.get("payload", {}) or {}
        cid = payload.get("chunk_id", chunk.get("id", ""))
        if cid:
            chunks[cid] = payload.get("chunk_text", "")
    return chunks


def _strip_markers(prose: str, dropped_ids: list[str]) -> str:
    """Remove the orphaned ``{{claim_id}}`` markers of DROPPED claims from the prose so
    a number the cite-check could not trace is never rendered as a broken citation
    (FM-3). Collapses the whitespace the removal leaves behind."""
    for cid in dropped_ids:
        prose = prose.replace(f"{{{{{cid}}}}}", "")
    prose = re.sub(r"[ \t]{2,}", " ", prose)
    prose = re.sub(r"\s+([.,;:])", r"\1", prose)
    return prose.strip()


# ---------------------------------------------------------------------------
# Node entry point
# ---------------------------------------------------------------------------


def run(state: SupervisorState) -> SupervisorState:
    """Compose ONE scrubbed, cited, disclaimered, honest-partial-aware answer.

    Branch order (first match wins):

    1. ``tool_results`` present → the multi-tool FUSION path (06.3-06): call
       ``_llm_fuse``, re-scrub the fused prose (banned token → BLOCK to a refusal, never
       a fabricated rewrite), run the EXTENDED cite-check and DROP every unresolved
       ``ToolClaim`` / ungrounded ``Claim`` (FM-3), inject the disclaimer, and set
       ``is_partial`` (True on a fused-flagged partial, an UNFINISHED plan/budget-trip,
       or a tool ABSTAIN — D-08).
    2. ``grounded_answer`` present (DRHP-only, 06.3-05) → re-scrub, rely on the
       subgraph's ``all_claims_grounded`` (NOT forked, D-03), inject the disclaimer, set
       ``is_partial`` from the plan state. ZERO live LLM.
    3. UNFINISHED ``tool_plan`` with nothing grounded → an honest labelled partial.
    4. Otherwise (empty plan, nothing grounded, no tools) → the educational refusal.
    """
    tool_results = state.get("tool_results", []) or []
    grounded = state.get("grounded_answer")
    unfinished_plan = bool(state.get("tool_plan"))
    any_abstain = any(bool(r.get("abstain")) for r in tool_results)
    disclaimer = _disclaimer()

    # -- Branch 1: multi-tool fusion (06.3-06) --------------------------------------
    if tool_results:
        fused = _llm_fuse(state)
        is_partial = bool(fused.is_partial) or unfinished_plan or any_abstain

        # Re-scrub the fused prose. No live regen here → a surviving banned token BLOCKS
        # to the refusal (never a fabricated clean rewrite, honesty invariant).
        if not _rescrub_passed(fused.answer_prose):
            return {
                **state,
                "fused_answer": None,
                "grounded_answer": None,
                "refusal": _banned_token_refusal(),
                "is_partial": is_partial,
                "disclaimer": disclaimer,
            }

        # Extended cite-check (D-03): keep grounded claims, DROP any number that cannot
        # be traced to a committed source record (ToolClaim) or DRHP span (Claim) — FM-3.
        kept, dropped = partition_fused_claims(
            list(fused.claims), _retrieved_chunks(state), tool_results
        )
        prose = _strip_markers(fused.answer_prose, dropped)
        fused = fused.model_copy(
            update={"answer_prose": prose, "claims": kept, "is_partial": is_partial}
        )
        return {
            **state,
            "fused_answer": fused,
            "refusal": None,
            "is_partial": is_partial,
            "disclaimer": disclaimer,
        }

    # -- Branch 2: DRHP-only path (re-scrub + cite-check passthrough, NO live LLM) ---
    if grounded is not None:
        if not _rescrub_passed(grounded.answer_prose):
            return {
                **state,
                "grounded_answer": None,
                "refusal": _banned_token_refusal(),
                "is_partial": unfinished_plan,
                "disclaimer": disclaimer,
            }
        if not state.get("all_claims_grounded", False):
            # The subgraph could not ground every claim → surface its refusal
            # (never fabricate). Fall back to the educational refusal if unset.
            return {
                **state,
                "refusal": state.get("refusal") or _educational_refusal(),
                "is_partial": unfinished_plan,
                "disclaimer": disclaimer,
            }
        return {
            **state,
            "refusal": None,
            "is_partial": unfinished_plan,
            "disclaimer": disclaimer,
        }

    # -- Branch 3: budget-trip / unfinished plan, nothing grounded → honest partial -
    if unfinished_plan:
        partial = FusedAnswer(
            answer_prose=HONEST_PARTIAL_PROSE,
            claims=[],
            is_partial=True,
            unaddressed=[_UNADDRESSED_BUDGET],
        )
        return {
            **state,
            "fused_answer": partial,
            "refusal": None,
            "is_partial": True,
            "disclaimer": disclaimer,
        }

    # -- Branch 4: empty plan, nothing grounded → educational / out-of-scope refusal -
    return {
        **state,
        "refusal": state.get("refusal") or _educational_refusal(),
        "is_partial": False,
        "disclaimer": disclaimer,
    }
