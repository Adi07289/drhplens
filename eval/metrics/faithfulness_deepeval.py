"""eval.metrics.faithfulness_deepeval — the DeepEval LLM-judge faithfulness metric (REPORTED).

Faithfulness is the one non-deterministic dimension in the harness: an LLM judge scores the
fraction of an answer's claims that are supported by the reranked DRHP chunks the agent
*actually retrieved*. It is REPORTED, never gated — the deterministic ``recall_at_k`` /
``citation_accuracy`` carry the release gate (AI-SPEC §5; hard-gating a run-to-run-variable
judge is itself a critical failure mode). So this wrapper *measures* (records score + reason)
and NEVER raises on a low score; the opt-in ``assert_test`` lane
(``tests/eval/test_faithfulness_deepeval.py``) is the only place a below-threshold score raises.

Landmines baked in from spike 002 (`.planning/spikes/002-deepeval-gemini-judge/`):
  - Judge model = ``gemini-3.5-flash`` — the id the codebase already runs on. The AI-SPEC §4
    sketch used a now-stale ``gemini-2.x`` flash id that returns 404 "no longer available to new
    users"; do NOT reintroduce it. The judge is Gemini-only (native ``deepeval.models.GeminiModel``
    on ``GEMINI_API_KEY``) — no third-party judge backend / proprietary-vendor key is acquired.
  - Free-tier Gemini is 5 RPM and faithfulness fans out (truths-extraction + per-claim verdicts),
    so ``async_mode=False`` (serial) + a tenacity 429/5xx backoff (~30-65s window) keep it cheap.
  - Infra failure (``GEMINI_API_KEY`` unset OR rate-limit exhaustion after backoff) returns the
    ``-1.0`` "not measured" sentinel — NEVER a misleading ``0.0`` (0.0 means a real measured zero).
    Mirrors the ``scripts/run_eval._ragas_faithfulness`` sentinel and ``eval.metrics.schema``'s
    ``faithfulness_deepeval`` field bound (``ge=-1.0`` where -1.0 is the sole sub-zero value).
"""
from __future__ import annotations

import os
from functools import lru_cache

from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_random,
)

# The "-1 = not measured" sentinel — distinct from a real measured 0.0 (threat T-6.1-05:
# never conflate "failed / not measured" with a genuine zero-faithfulness score).
NOT_MEASURED: float = -1.0

# Retryable transient conditions on the free tier. Spike 002 measured
# `429 RESOURCE_EXHAUSTED — 5 requests/min` for gemini-3.5-flash; 5xx is treated as transient too.
_TRANSIENT_TEXT = (
    "429",
    "resource_exhausted",
    "rate limit",
    "quota exceeded",
    "unavailable",
    "503",
)


# Single source of truth for the judge model id (spike 002 / AI-SPEC §8 item 1: the stale
# gemini-2.x flash literal in the §4 sketch 404s). The runner reads THIS for eval_summary.json's
# judge_model provenance — never a decoupled literal — so a model bump can't make the committed
# provenance (and the schema's honesty guard) silently lie (WR-04).
JUDGE_MODEL = "gemini-3.5-flash"


@lru_cache(maxsize=1)
def _judge():
    """Module-cached native Gemini judge — built once per process (5-RPM free tier is precious).

    Model id is ``JUDGE_MODEL`` (``gemini-3.5-flash``) — the id the codebase runs on. Reads
    ``GEMINI_API_KEY`` only; callers must guard the missing-key case *before* calling this
    (``faithfulness_deepeval`` does), so this never ``KeyError``s on the reported path.
    """
    from deepeval.models import GeminiModel

    return GeminiModel(
        model=JUDGE_MODEL,
        api_key=os.environ["GEMINI_API_KEY"],
        temperature=0.0,
    )


def _is_transient(exc: BaseException) -> bool:
    """True if ``exc`` looks like a transient 429/5xx worth a backoff retry."""
    code = getattr(exc, "code", None)
    if code is None:
        code = getattr(exc, "status_code", None)
    if isinstance(code, int) and code in (429, 500, 502, 503, 504):
        return True
    text = str(exc).lower()
    return any(token in text for token in _TRANSIENT_TEXT)


def faithfulness_deepeval(
    question: str, answer: str, contexts: list[str]
) -> tuple[float, str]:
    """Return ``(score, reason)`` for the answer's faithfulness to the retrieved contexts.

    REPORTED, never gated: this measures (records score + reason) and never raises on a low
    score. On infra failure (``GEMINI_API_KEY`` unset, or 429/5xx exhaustion after backoff) it
    returns the ``(-1.0, "<reason: not measured — ...>")`` sentinel rather than a misleading 0.0.

    Args:
        question: the gold-set question (``LLMTestCase.input``).
        answer: the agent's prose answer (``LLMTestCase.actual_output``).
        contexts: the top-k reranked DRHP chunks the agent ACTUALLY saw
            (``LLMTestCase.retrieval_context``). Passed through byte-identical — do NOT
            expand or summarize; feeding the judge more than the agent retrieved would
            inflate the score dishonestly and defeat the P18 answer-without-retrieving guard.

    Returns:
        ``(score, reason)`` where ``score`` is a float in ``[0.0, 1.0]`` on success, or
        ``NOT_MEASURED`` (``-1.0``) with a human-readable cause on infra failure.
    """
    # Report, don't crash: an unset key is "not measured", never a fabricated 0.0.
    if not os.environ.get("GEMINI_API_KEY"):
        return NOT_MEASURED, "<reason: not measured — GEMINI_API_KEY unset>"

    try:
        from deepeval.metrics import FaithfulnessMetric
        from deepeval.test_case import LLMTestCase

        tc = LLMTestCase(
            input=question,
            actual_output=answer,
            retrieval_context=contexts,
        )
        # threshold=0.95 is a REPORTED target line only — measure() never asserts it.
        metric = FaithfulnessMetric(
            threshold=0.95,
            model=_judge(),
            include_reason=True,
            async_mode=False,  # serial: free-tier is 5 RPM, async bursts 429
        )

        # tenacity 429/5xx backoff around the (fanning-out) judge call. ~30-65s per spike 002's
        # 5-RPM window; a few attempts then give up and fall through to the -1 sentinel.
        for attempt in Retrying(
            retry=retry_if_exception(_is_transient),
            wait=wait_random(min=30, max=65),
            stop=stop_after_attempt(3),
            reraise=True,
        ):
            with attempt:
                metric.measure(tc)  # measure() != assert_test(): records, does not raise on low score

        return float(metric.score), (metric.reason or "")
    except Exception as exc:  # noqa: BLE001 — REPORTED path: any infra failure -> -1 sentinel, never raise
        return NOT_MEASURED, f"<reason: not measured — {type(exc).__name__}: {exc}>"
