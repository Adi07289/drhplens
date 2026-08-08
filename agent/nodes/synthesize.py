"""
agent/nodes/synthesize.py — the terminal synthesis node (D-03/D-08).

This is the bounded supervisor's LAST node: whatever the router forwarded (a
DRHP-grounded answer, a set of read-only tool results, a budget-trip, or an empty
out-of-scope plan), synthesize composes ONE honestly-labelled, scrubber-clean,
disclaimered answer object for the renderer.

Scope of THIS plan (06.3-05, the DRHP-only vertical slice):
    * DRHP-only path — the embedded ``drhp_rag`` sub-agent produced a
      ``grounded_answer``: RE-APPLY ``compliance.scrubber.scrub`` to the grounded
      prose (belt-and-suspenders block, mirroring ``agent/nodes/scrub.py``), rely on
      the subgraph's EXISTING deterministic cite-check result
      (``all_claims_grounded``) for ``Claim`` grounding — the cite-check is NOT
      forked (D-03) — inject the disclaimer, and set ``is_partial``. ZERO live LLM
      on this path: it composes existing state, no new model call.
    * Honest-partial path — the run reached synthesize with an UNFINISHED
      ``tool_plan`` (the P8 counter halted early, D-06) or a tool ABSTAINED (P14):
      return whatever grounded content exists, explicitly labelled incomplete
      (``is_partial=True``, ``unaddressed[...]``) — NEVER fabricating the missing
      part (D-08). Deterministic, no live LLM.
    * Refusal path — nothing is grounded and no tool ran (classify emptied the
      plan for advice-bait / gibberish / jailbreak / cross-IPO, D-07): surface the
      existing educational refusal — never fabricate an answer.

Deferred to 06.3-06 (Wave 4, the fusion plan): the LIVE multi-tool FUSION hop
(``_llm_fuse`` — the Instructor+Gemini call that weaves DRHP text + tool numbers
into one FusedAnswer) and the EXTENDED provenance cite-check (ToolClaim → source
record, D-03). ``_llm_fuse`` is defined here as a documented placeholder so the
offline stress suite can STUB it (``patch("agent.nodes.synthesize._llm_fuse")``);
the call-site + the deterministic post-processing envelope (re-scrub + disclaimer
+ ``is_partial``) are wired now, so a stubbed fusion answer flows end-to-end.

Compliance boundary (mirrors ``agent/nodes/scrub.py`` / ``emit.py``): the scrubber
and the disclaimer are re-applied AFTER generation, so no prompt can strip them
(D-07b). The node returns via the ``{**state, ...}`` overwrite convention every
existing node uses — the renderer owns the final output shape (emit.run posture).
"""
from __future__ import annotations

from compliance.disclaimer_text import ANCHOR_COPY, PER_ANSWER_FOOTER
from compliance.scrubber import scrub

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

    Synthesis is a post-hoc belt-and-suspenders re-scrub (the DRHP subgraph already
    scrubbed + block-and-regenerated internally, D-09). There is NO live LLM here to
    regenerate, so a banned token that still survives to synthesize BLOCKS to a
    refusal rather than fabricating a clean rewrite (honesty invariant)."""
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
        explanation=ui_copy.REFUSAL_BANNED_TOKEN_COPY,
        reformulation_suggestions=[],
    )


# ---------------------------------------------------------------------------
# Multi-tool FUSION hop — the live LLM call lands in 06.3-06 (Wave 4).
# ---------------------------------------------------------------------------


def _llm_fuse(state: SupervisorState) -> FusedAnswer:
    """Fuse ``tool_results`` (+ any ``grounded_answer``) into ONE cited FusedAnswer.

    DEFERRED to 06.3-06: the real Instructor+Gemini fusion hop (mirroring
    ``agent/nodes/decompose.py`` / ``classify.py``, temperature=0, system/user
    separation for the D-07b jailbreak defense) plus the extended provenance
    cite-check (ToolClaim → committed source record, D-03). This DRHP-only slice
    wires the CALL-SITE and the deterministic post-processing envelope (re-scrub +
    disclaimer + ``is_partial``) so a stubbed fusion answer flows end-to-end; the
    OFFLINE D-09 stress suite patches this symbol per fixture
    (``patch("agent.nodes.synthesize._llm_fuse", ...)``).

    Raising (rather than returning a fabricated answer) is the honest placeholder:
    no live multi-tool caller exists in this slice, so this body is never reached
    live — only via the stress-suite stub or the 06.3-06 implementation.
    """
    raise NotImplementedError(
        "Live multi-tool fusion LLM hop lands in 06.3-06 (Wave 4); the offline D-09 "
        "stress suite stubs this symbol. The DRHP-only slice (06.3-05) does not "
        "invoke a live fusion call."
    )


# ---------------------------------------------------------------------------
# Node entry point
# ---------------------------------------------------------------------------


def run(state: SupervisorState) -> SupervisorState:
    """Compose ONE scrubbed, cited, disclaimered, honest-partial-aware answer.

    Branch order (first match wins):

    1. ``tool_results`` present → the multi-tool FUSION path: call ``_llm_fuse``
       (real impl in 06.3-06; stubbed offline), re-scrub the fused prose, inject the
       disclaimer, and set ``is_partial`` (True on a fused-flagged partial, an
       UNFINISHED plan/budget-trip, or a tool ABSTAIN — D-08). A banned token
       surviving the fuse BLOCKS to a refusal (never a fabricated rewrite).
    2. ``grounded_answer`` present (DRHP-only) → re-scrub the grounded prose, rely on
       the subgraph's ``all_claims_grounded`` cite-check result (NOT forked, D-03),
       inject the disclaimer, set ``is_partial`` from the plan state. ZERO live LLM.
    3. UNFINISHED ``tool_plan`` with nothing grounded → an honest labelled partial
       (``is_partial=True``), deterministic + no fabrication (D-06/D-08 budget-trip).
    4. Otherwise (empty plan, nothing grounded, no tools) → the educational refusal.

    Returns the ``{**state, ...}`` overwrite: sets ``disclaimer`` (the post-generation
    surface), ``is_partial``, and one of ``fused_answer`` / ``grounded_answer`` /
    ``refusal`` — the renderer owns the final shape (emit.run posture).
    """
    tool_results = state.get("tool_results", []) or []
    grounded = state.get("grounded_answer")
    unfinished_plan = bool(state.get("tool_plan"))
    any_abstain = any(bool(r.get("abstain")) for r in tool_results)
    disclaimer = _disclaimer()

    # -- Branch 1: multi-tool fusion (real impl in 06.3-06; stubbed offline) --------
    if tool_results:
        fused = _llm_fuse(state)
        is_partial = bool(fused.is_partial) or unfinished_plan or any_abstain
        if not _rescrub_passed(fused.answer_prose):
            return {
                **state,
                "fused_answer": None,
                "grounded_answer": None,
                "refusal": _banned_token_refusal(),
                "is_partial": is_partial,
                "disclaimer": disclaimer,
            }
        fused = fused.model_copy(update={"is_partial": is_partial})
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
