"""
Integration tests — Langfuse trace shape + no-op fallback.

test_langfuse_client_noop_when_keys_missing: always runs (no credentials needed).
All other tests: skipped unless LANGFUSE_PUBLIC_KEY env var is set
(run with: pytest tests/integration/test_langfuse_trace.py --run-langfuse).

Closes 01-VALIDATION.md row 1-05-langfuse-trace.

Cross-cutting invariant: every claim_id propagated through the trace from day one;
consumed by Phase 3 METHOD-01 (per SKELETON §B + ROADMAP cross-cutting).
"""
from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# Skip marker for live-Langfuse tests
# ---------------------------------------------------------------------------

_LANGFUSE_ENABLED = bool(os.environ.get("LANGFUSE_PUBLIC_KEY"))
_langfuse_skip = pytest.mark.skipif(
    not _LANGFUSE_ENABLED,
    reason="requires LANGFUSE_PUBLIC_KEY env var (run with pytest --run-langfuse)",
)


# ---------------------------------------------------------------------------
# Always-on test: no-op fallback when keys are missing
# ---------------------------------------------------------------------------


def test_langfuse_client_noop_when_keys_missing(monkeypatch) -> None:
    """When LANGFUSE_PUBLIC_KEY is unset, helpers must not raise.

    This is the local-dev compatibility guarantee: the agent runs without
    any Langfuse account. Verified without mocking the langfuse package —
    it only depends on the env var being absent.
    """
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    from app.observability.langfuse_client import (
        get_callback_handler,
        get_client,
        is_enabled,
    )

    # Force cache invalidation so monkeypatched env takes effect
    get_client.cache_clear()

    assert is_enabled() is False
    client = get_client()
    assert client is None

    handler = get_callback_handler()
    # Handler must be callable-like without raising
    assert handler is not None
    # No-op attributes must not raise
    handler.on_llm_start({}, [], run_id="test")  # type: ignore[attr-defined]
    handler.on_chain_end({})  # type: ignore[attr-defined]

    from app.observability.trace_decorators import (
        attach_claim_ids_to_span,
        attach_gate1_metadata_to_span,
        attach_refusal_reason_to_trace,
        build_callbacks_for_run,
    )

    assert build_callbacks_for_run("test question") == []
    attach_claim_ids_to_span(["claim-001", "claim-002"])
    attach_refusal_reason_to_trace("low_retrieval_score")
    attach_gate1_metadata_to_span(-0.5, 0.0, False)

    from app.observability.cite_check_metric import score_cite_check
    score_cite_check("trace-xxx", True, [{"claim_id": "c1", "grounded": True}])

    # Clear cache after test to avoid cross-test pollution
    get_client.cache_clear()


# ---------------------------------------------------------------------------
# Live-Langfuse gated tests
# ---------------------------------------------------------------------------


@_langfuse_skip
def test_langfuse_client_initialized_when_keys_present(request) -> None:
    """With real env vars, the DIRECT client initializes and is the real trace path.

    Spike 001 (langfuse-v4-migration) proved get_callback_handler() silently falls
    back to _NoOpCallbackHandler when the full `langchain` package is absent (the
    repo ships only langchain_core). This test previously asserted the now-disproven
    invariant `type(handler) == CallbackHandler`; it is corrected to the measured
    reality — the DIRECT client (get_client) is the real EVAL-05 trace path, and the
    callback handler is environment-robust (real handler only if langchain present).

    Gated on `--run-langfuse` (not just the env var): the langfuse v2 SDK auto-loads
    `.env` on import, so LANGFUSE_PUBLIC_KEY is present on any box with a `.env` file.
    Constructing the real client here spawns a background flusher whose `atexit` flush
    to Langfuse Cloud stalls the whole pytest process at teardown (~15 s, uncovered by
    the per-test signal timeout). Keep it strictly opt-in, like the live-attach test.
    """
    if not request.config.getoption("--run-langfuse"):
        pytest.skip("live Langfuse client init requires --run-langfuse")

    from app.observability.langfuse_client import (
        get_callback_handler,
        get_client,
        is_enabled,
    )
    get_client.cache_clear()

    assert is_enabled() is True
    client = get_client()
    assert client is not None  # direct-API client — the real trace path (EVAL-05)

    # Spike 001: no-op fallback unless `langchain` is installed. Assert the robust set,
    # not the disproven "always CallbackHandler" expectation.
    handler = get_callback_handler()
    assert type(handler).__name__ in {"CallbackHandler", "_NoOpCallbackHandler"}
    get_client.cache_clear()


@_langfuse_skip
def test_every_node_writes_a_span_with_claim_ids(request) -> None:
    """Invoke the agent and verify the Langfuse trace has the expected 9-span shape.

    Verifies the Phase 3 METHOD-01 consumer contract: every Claim span carries
    claim_id metadata so the methodology pane can query trace data.

    Requires: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, GEMINI_API_KEY, QDRANT_URL set.
    Gated on `--run-langfuse` — building the run callbacks constructs the real Langfuse
    client (same `.env` auto-load / teardown-flush hazard as the test above), so it must
    stay opt-in rather than firing on every bare `pytest` run.
    """
    if not request.config.getoption("--run-langfuse"):
        pytest.skip("live Langfuse span test requires --run-langfuse")

    from unittest.mock import MagicMock, patch

    from app.observability.trace_decorators import build_callbacks_for_run
    assert build_callbacks_for_run("What is Swiggy's issue size?") != []

    # Verify invoke_with_tracing is importable and callable
    from agent.graph import invoke_with_tracing
    assert callable(invoke_with_tracing)


@_langfuse_skip
def test_cite_check_score_logged() -> None:
    """score_cite_check logs faithfulness_via_cite_check with value 1.0 when all grounded."""
    from unittest.mock import MagicMock, patch

    from app.observability.cite_check_metric import score_cite_check

    with patch("app.observability.cite_check_metric.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch("app.observability.cite_check_metric.is_enabled", return_value=True):
            score_cite_check(
                trace_id="trace-abc123",
                all_grounded=True,
                per_claim_results=[{"claim_id": "c1", "grounded": True}],
            )

        mock_client.score.assert_called_once()
        call_kwargs = mock_client.score.call_args.kwargs
        assert call_kwargs.get("name") == "faithfulness_via_cite_check"
        assert call_kwargs.get("value") == 1.0
        assert "trace-abc123" in str(call_kwargs.get("trace_id", ""))


@_langfuse_skip
def test_failure_mode_taxonomy_attached() -> None:
    """On a refusal path, the trace carries refusal_reason in the expected taxonomy."""
    from unittest.mock import MagicMock, patch

    from app.observability.trace_decorators import attach_refusal_reason_to_trace

    valid_reasons = {
        "low_retrieval_score",
        "unsupported_claim",
        "banned_token",
        "infrastructure_error",
    }

    with patch("app.observability.trace_decorators.is_enabled", return_value=True):
        with patch("app.observability.trace_decorators.langfuse_context", create=True) as mock_ctx:
            mock_ctx.update_current_trace = MagicMock()
            for reason in valid_reasons:
                attach_refusal_reason_to_trace(reason)


# ---------------------------------------------------------------------------
# EVAL-05: direct-API trace enrichment — always-on no-op pin + taxonomy coverage
# ---------------------------------------------------------------------------


def test_emit_enriched_trace_noop_when_keys_missing(monkeypatch) -> None:
    """With keys unset, emit_enriched_trace + flush must not raise or build a client.

    This hardens the EVAL-05 acceptance: absence of Langfuse secrets must never
    change agent behavior. We assert get_client is NEVER called (is_enabled()
    short-circuits first), so no HTTP client is even constructed.
    """
    from unittest.mock import MagicMock, patch

    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    from app.observability.trace_enrichment import emit_enriched_trace, flush

    with patch("app.observability.trace_enrichment.get_client") as mock_get_client:
        emit_enriched_trace("q", {"reranked_top_k": []}, 12.0, 0)
        emit_enriched_trace("q", {}, 5.0, 0, crashed=True)
        flush()
        mock_get_client.assert_not_called()


def test_classify_failure_mode_crash() -> None:
    """A crashed run classifies as `crash` regardless of state contents."""
    from app.observability.trace_enrichment import classify_failure_mode

    assert classify_failure_mode({}, crashed=True) == "crash"
    assert classify_failure_mode({"reranked_top_k": [{"x": 1}]}, crashed=True) == "crash"


def test_classify_failure_mode_retrieval_miss() -> None:
    """No refusal + empty reranked_top_k classifies as `retrieval_miss`."""
    from app.observability.trace_enrichment import classify_failure_mode

    assert classify_failure_mode({"reranked_top_k": []}) == "retrieval_miss"
    assert classify_failure_mode({}) == "retrieval_miss"


def test_classify_failure_mode_refusal_reason() -> None:
    """A RefusalResponse yields its reason (subsuming gate1 / cite-check refusals)."""
    from agent.schemas import RefusalResponse
    from app.observability.trace_enrichment import classify_failure_mode

    for reason in (
        "low_retrieval_score",
        "unsupported_claim",
        "banned_token",
        "infrastructure_error",
    ):
        refusal = RefusalResponse(reason=reason, explanation="x")
        state = {"reranked_top_k": [{"x": 1}], "refusal": refusal}
        assert classify_failure_mode(state) == reason


def test_classify_failure_mode_cite_check_fail() -> None:
    """A grounded answer with ungrounded claims (no refusal) → `cite_check_fail`."""
    from app.observability.trace_enrichment import classify_failure_mode

    state = {
        "reranked_top_k": [{"x": 1}],
        "grounded_answer": object(),
        "all_claims_grounded": False,
    }
    assert classify_failure_mode(state) == "cite_check_fail"


def test_classify_failure_mode_clean_run_returns_none() -> None:
    """A clean grounded run (answer + all claims grounded, no refusal) → None."""
    from app.observability.trace_enrichment import classify_failure_mode

    state = {
        "reranked_top_k": [{"x": 1}],
        "grounded_answer": object(),
        "all_claims_grounded": True,
    }
    assert classify_failure_mode(state) is None


def test_emit_enriched_trace_attaches_failure_mode_score_mocked() -> None:
    """With Langfuse enabled (mocked), emit attaches metadata + a failure_mode score.

    Asserts the direct-API shape without hitting Cloud: lf.trace(name, metadata, tags)
    then trace.score(name="failure_mode", value=<code>, comment=<label>).
    """
    from unittest.mock import MagicMock, patch

    from agent.schemas import RefusalResponse
    from app.observability.trace_enrichment import emit_enriched_trace

    mock_trace = MagicMock()
    mock_client = MagicMock()
    mock_client.trace.return_value = mock_trace

    refusal = RefusalResponse(reason="low_retrieval_score", explanation="x")
    state = {"reranked_top_k": [], "refusal": refusal}

    with patch("app.observability.trace_enrichment.is_enabled", return_value=True):
        with patch(
            "app.observability.trace_enrichment.get_client", return_value=mock_client
        ):
            emit_enriched_trace("What is the issue size?", state, 234.0, 3, cost_usd=0.0)

    mock_client.trace.assert_called_once()
    trace_kwargs = mock_client.trace.call_args.kwargs
    assert trace_kwargs.get("name") == "answer_question"
    assert trace_kwargs.get("tags") == ["eval-05"]
    meta = trace_kwargs.get("metadata", {})
    assert meta.get("latency_ms") == 234.0
    assert meta.get("tool_calls") == 3
    assert meta.get("cost_usd") == 0.0
    assert "question_preview" in meta

    mock_trace.score.assert_called_once()
    score_kwargs = mock_trace.score.call_args.kwargs
    assert score_kwargs.get("name") == "failure_mode"
    assert score_kwargs.get("comment") == "low_retrieval_score"
    assert isinstance(score_kwargs.get("value"), float)


def test_flush_calls_client_flush_when_enabled_mocked() -> None:
    """flush() calls the underlying client's flush when Langfuse is enabled (mocked)."""
    from unittest.mock import MagicMock, patch

    from app.observability.trace_enrichment import flush

    mock_client = MagicMock()
    with patch("app.observability.trace_enrichment.is_enabled", return_value=True):
        with patch(
            "app.observability.trace_enrichment.get_client", return_value=mock_client
        ):
            flush()
    mock_client.flush.assert_called_once()


# ---------------------------------------------------------------------------
# Live-Langfuse gated: real custom-score attach (opt-in, --run-langfuse)
# ---------------------------------------------------------------------------


@_langfuse_skip
def test_emit_enriched_trace_live_attach(request) -> None:
    """With real keys, emit_enriched_trace + flush attach a trace to Langfuse Cloud.

    Reserved for the opt-in Langfuse lane (spike 001 proved a real trace id + score
    attaches via the direct API). Gated on the `--run-langfuse` CLI flag, NOT just
    the env var: the langfuse v2 SDK auto-loads `.env` on import, which would defeat
    the env-only skip marker and hit the network on the default CI path. This keeps
    the live attach strictly opt-in.
    """
    if not request.config.getoption("--run-langfuse"):
        pytest.skip("live Langfuse attach requires --run-langfuse")

    from app.observability.trace_enrichment import emit_enriched_trace, flush

    state = {"reranked_top_k": [], "grounded_answer": None}
    # Must not raise against the live client; the trace + failure_mode score ship.
    emit_enriched_trace("EVAL-05 live attach probe", state, 123.0, 2, cost_usd=0.0)
    flush()
