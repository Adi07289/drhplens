"""
app/observability/trace_enrichment.py — Direct-API Langfuse trace enrichment (EVAL-05).

Spike 001 (langfuse-v4-migration) found the LangChain `CallbackHandler` path is
silently no-op: `get_callback_handler()` returns `_NoOpCallbackHandler` because the
full `langchain` package is absent (only `langchain_core` is installed), on both
langfuse v2 and v4. So "every agent run writes a trace" had NOT held in practice.

This module instruments via the **direct client API** instead (measured decision #5,
verified live in spike 001):

    lf = get_client()
    t = lf.trace(name="answer_question", metadata={...}, tags=["eval-05"])
    t.score(name="failure_mode", value=<code>, comment=<label>)
    lf.flush()

It attaches cost / latency / tool-call-count metadata plus a failure-mode custom
score drawn from the extended taxonomy (FAILURE_MODES).

Hard contracts (spike 001 / CONVENTIONS.md):
  - Do NOT import `langchain`; do NOT route through get_callback_handler.
  - Preserve the no-op fallback: with LANGFUSE_PUBLIC_KEY/SECRET_KEY unset the agent
    runs byte-for-byte unchanged (is_enabled() gate returns before any client call).
  - Every Langfuse call is try/except-swallowed so tracing NEVER crashes the agent
    response path (mirrors cite_check_metric.py).
  - flush() before short-lived process exit is mandatory (runner/CI) or scores
    silently never ship.
"""
from __future__ import annotations

from typing import Any

from app.observability.langfuse_client import get_client, is_enabled

# ---------------------------------------------------------------------------
# Failure-mode taxonomy (design doc §4.4 / SPEC requirement 4)
# ---------------------------------------------------------------------------
#
# The first four entries are the EXISTING RefusalResponse.reason values
# (agent/schemas.py :: RefusalReason) — the refusal-only taxonomy that
# trace_decorators.attach_refusal_reason_to_trace already emits. We EXTEND, not
# replace, that set with four run-level failure modes:
#   - retrieval_miss : the retrieval/rerank stage returned nothing usable
#   - cite_check_fail: a generated answer had dropped/ungrounded claims
#   - judge_flag     : an EVAL-TIME signal — the DeepEval judge (06.1-04 runner)
#                      flags the answer. It is NOT emittable at agent-runtime
#                      because the judge runs later in the eval runner, so
#                      classify_failure_mode() below never returns it. It lives
#                      in the taxonomy so the runner can attach it via the same
#                      emit path (see 06.1-04); the branch is intentionally
#                      unreachable from agent-runtime, documented here so it is
#                      not silently dead.
#   - crash          : GRAPH.invoke raised (wired in agent/graph.py).
FAILURE_MODES: tuple[str, ...] = (
    "low_retrieval_score",
    "unsupported_claim",
    "banned_token",
    "infrastructure_error",
    "retrieval_miss",
    "cite_check_fail",
    "judge_flag",
    "crash",
)


def _failure_mode_value(mode: str) -> float:
    """Map a failure-mode label to a stable numeric score code.

    Langfuse custom scores are numeric; the human-readable label rides in the
    `comment` field (mirrors cite_check_metric's comment usage). We use a 1-based
    index into FAILURE_MODES so each mode gets a distinct non-zero code that is
    filterable in Cloud saved views. Unknown labels fall back to 0.0.
    """
    try:
        return float(FAILURE_MODES.index(mode) + 1)
    except ValueError:
        return 0.0


def count_tool_calls(final_state: dict) -> int:
    """Count node/tool stages that produced output, derived deterministically from state.

    This is an HONEST count from observable state evidence — not a fabricated
    constant. Each stage is counted iff its state output is present:
      - retrieve : retrieved_chunks non-empty
      - rerank   : reranked_top_k non-empty
      - generate : grounded_answer is not None
      - cite_check: cite_check ran (all_claims_grounded key present in state)

    A refused / short-circuited run therefore reports fewer tool calls than a full
    happy-path run, which is the desired signal for the Langfuse tool-call view.
    """
    if not isinstance(final_state, dict):
        return 0
    count = 0
    if final_state.get("retrieved_chunks"):
        count += 1
    if final_state.get("reranked_top_k"):
        count += 1
    if final_state.get("grounded_answer") is not None:
        count += 1
    if "all_claims_grounded" in final_state:
        count += 1
    return count


def classify_failure_mode(final_state: dict, crashed: bool = False) -> str | None:
    """Map a completed agent run to a failure-mode label, or None for a clean run.

    Priority (matches 06.1-03-PLAN Task 1):
      1. crash        — GRAPH.invoke raised (caller passes crashed=True).
      2. refusal.reason — a RefusalResponse fired (one of the 4 refusal reasons).
                          This subsumes gate1 (low_retrieval_score) and
                          cite-check (unsupported_claim) refusals, since the graph
                          routes both through refuse_with_reformulation.
      3. retrieval_miss — no refusal, but reranked_top_k is empty (defensive:
                          a retrieval wipe-out that did not set a refusal).
      4. cite_check_fail — no refusal, but a grounded_answer exists with
                          all_claims_grounded is False (defensive: ungrounded
                          claims that did not route to a refusal).
      5. None         — clean grounded run.

    Modes 3 and 4 are defensive branches: under normal graph routing the refusal
    node sets low_retrieval_score / unsupported_claim first, so these fire only
    when state evidences the failure without a refusal object. The eval runner
    (06.1-04) may classify directly off state to distinguish them; `judge_flag`
    is attached only there (eval-time), never here.

    Args:
        final_state: Final GraphState dict (may be {} on a crash).
        crashed: True iff GRAPH.invoke raised.

    Returns:
        A FAILURE_MODES label, or None for a clean run.
    """
    if crashed:
        return "crash"
    if not isinstance(final_state, dict):
        return None

    refusal = final_state.get("refusal")
    if refusal is not None:
        reason = getattr(refusal, "reason", None)
        # Preserve dict-shaped refusals too (defensive; runtime uses RefusalResponse).
        if reason is None and isinstance(refusal, dict):
            reason = refusal.get("reason")
        return reason or "infrastructure_error"

    if not final_state.get("reranked_top_k"):
        return "retrieval_miss"

    if (
        final_state.get("grounded_answer") is not None
        and final_state.get("all_claims_grounded") is False
    ):
        return "cite_check_fail"

    return None


def emit_enriched_trace(
    question: str,
    final_state: dict,
    latency_ms: float,
    tool_calls: int,
    cost_usd: float = 0.0,
    crashed: bool = False,
) -> None:
    """Emit one enriched Langfuse trace via the DIRECT client API (EVAL-05).

    Attaches cost / latency / tool-call-count metadata and, when the run has a
    failure mode, a `failure_mode` custom score (numeric code + label comment).

    No-op contract: when Langfuse is disabled (keys unset) or the client is None,
    this returns immediately WITHOUT constructing a client or making any HTTP call —
    the local-dev / CI guarantee. Every Langfuse call is try/except-swallowed so a
    tracing failure NEVER breaks the agent response path (T-6.1-07 mitigation).

    Args:
        question: The user question (only an 80-char preview is sent — T-6.1-08).
        final_state: Final GraphState dict (use {} on a crash).
        latency_ms: Wall-clock latency of the run in milliseconds.
        tool_calls: Number of node/tool stages that produced output.
        cost_usd: Run cost in USD (free tier is $0; tracked per SPEC).
        crashed: True iff the run crashed (classified as `crash`).
    """
    # No-op fallback — the hard contract. Return before any client construction.
    if not is_enabled():
        return

    try:
        lf = get_client()
        if lf is None:
            return

        trace = lf.trace(
            name="answer_question",
            metadata={
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "tool_calls": tool_calls,
                "question_preview": question[:80],
            },
            tags=["eval-05"],
        )

        mode = classify_failure_mode(final_state, crashed=crashed)
        if mode is not None:
            trace.score(
                name="failure_mode",
                value=_failure_mode_value(mode),
                comment=mode,
            )
    except Exception:
        # Tracing must never crash the agent response path (mirror cite_check_metric).
        pass


def flush() -> None:
    """Flush buffered Langfuse events before a short-lived process exits.

    Mandatory in the runner / CI paths (spike 001 / CONVENTIONS.md): without it,
    scores are buffered and silently never ship. No-op when Langfuse is disabled,
    and try/except-guarded so it can never crash the caller.
    """
    if not is_enabled():
        return
    try:
        client = get_client()
        if client is not None:
            client.flush()
    except Exception:
        pass
