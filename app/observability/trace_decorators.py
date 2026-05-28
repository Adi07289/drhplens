"""
app/observability/trace_decorators.py — LangGraph callback helpers for Langfuse tracing.

Provides four helpers that nodes call to attach metadata to the active Langfuse span/trace.
All four no-op gracefully when Langfuse is not enabled (is_enabled() is False).

Per SKELETON cross-cutting invariant: claim_id references are materialized on the
generate and cite_check node spans so Phase 3 METHOD-01 can query trace data.

Failure-mode taxonomy (attach_refusal_reason_to_trace):
  refusal_reason ∈ {low_retrieval_score, unsupported_claim, banned_token, infrastructure_error}
  Matches the RefusalResponse.reason enum (agent/schemas.py).
"""
from __future__ import annotations

from typing import Any

from app.observability.langfuse_client import get_callback_handler, is_enabled


def build_callbacks_for_run(
    question: str,
    trace_metadata: dict[str, Any] | None = None,
) -> list:
    """Return the LangGraph callbacks list for a single agent run.

    When is_enabled() is False, returns [] — LangGraph accepts an empty list and
    the agent runs without any tracing overhead.

    Args:
        question: The user question (first 80 chars recorded in trace metadata).
        trace_metadata: Extra metadata dict merged into the trace (e.g. session_id).

    Returns:
        List with one CallbackHandler configured for this run, or [].
    """
    if not is_enabled():
        return []

    handler = get_callback_handler()
    # Attempt to set run-level metadata if the handler supports it
    try:
        from langfuse.callback import CallbackHandler  # type: ignore[import]
        if isinstance(handler, CallbackHandler):
            extra = {
                "phase": "1",
                "question_preview": question[:80],
                **(trace_metadata or {}),
            }
            handler.trace_name = "answer_question"
            # metadata propagated through LangChain callbacks metadata kwarg at invoke time
            handler.metadata = extra
    except (ImportError, AttributeError):
        pass

    return [handler]


def attach_claim_ids_to_span(claim_ids: list[str]) -> None:
    """Attach claim_id list to the current active Langfuse observation.

    Called from generate.py and cite_check.py nodes after GroundedAnswer is available.
    The Phase 3 METHOD-01 consumer queries these claim_ids to build the methodology pane.

    No-op when Langfuse is not enabled.

    Args:
        claim_ids: List of claim_id strings from GroundedAnswer.claims.
    """
    if not is_enabled():
        return
    try:
        from langfuse.decorators import langfuse_context  # type: ignore[import]
        langfuse_context.update_current_observation(metadata={"claim_ids": claim_ids})
    except (ImportError, Exception):
        pass


def attach_refusal_reason_to_trace(reason: str) -> None:
    """Attach refusal_reason to the current Langfuse trace root.

    Called from refuse_with_reformulation.py before returning state.
    The failure-mode taxonomy (low_retrieval_score | unsupported_claim |
    banned_token | infrastructure_error) matches the RefusalResponse.reason enum.

    No-op when Langfuse is not enabled.

    Args:
        reason: RefusalResponse.reason string value.
    """
    if not is_enabled():
        return
    try:
        from langfuse.decorators import langfuse_context  # type: ignore[import]
        langfuse_context.update_current_trace(metadata={"refusal_reason": reason})
    except (ImportError, Exception):
        pass


def attach_gate1_metadata_to_span(
    max_score: float,
    threshold: float,
    passed: bool,
) -> None:
    """Attach Gate 1 scoring metadata to the current active Langfuse observation.

    Called from gate1_check.py after computing the gate result.
    The Wave 5 calibration script (scripts/calibrate_gate1.py) uses these values
    when sweeping GATE1_THRESHOLD against the gold set.

    No-op when Langfuse is not enabled.

    Args:
        max_score: The maximum reranker score from reranked_top_k.
        threshold: The GATE1_THRESHOLD value used for this run.
        passed: Whether gate1_passed was True.
    """
    if not is_enabled():
        return
    try:
        from langfuse.decorators import langfuse_context  # type: ignore[import]
        langfuse_context.update_current_observation(
            metadata={
                "gate1_max_score": max_score,
                "gate1_threshold": threshold,
                "gate1_passed": passed,
            }
        )
    except (ImportError, Exception):
        pass
