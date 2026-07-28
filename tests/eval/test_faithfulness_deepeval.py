"""Tests for the DeepEval faithfulness metric — the REPORTED (never-gated) dimension.

Two lanes, mirroring the harness's two-lane split (AI-SPEC §5):

  (a) ALWAYS-ON sentinel unit test — runs in default ``pytest`` with NO ``GEMINI_API_KEY``.
      Pins the report-not-crash guarantee: with the key unset, ``faithfulness_deepeval`` returns
      the ``-1.0`` "not measured" sentinel and does NOT raise (threat T-6.1-05: never conflate
      "not measured" with a real 0.0). This lane makes no live judge call.

  (b) OPT-IN ``assert_test`` lane — SKIPPED unless ``GEMINI_API_KEY`` is set (mirrors the
      ``LANGFUSE_PUBLIC_KEY`` skip in ``tests/integration/test_langfuse_trace.py``). Invoke it
      with the DeepEval runner, NOT plain pytest:

          deepeval test run tests/eval/test_faithfulness_deepeval.py -c -i -n 1

      (-c cache: skip the judge when only deterministic code changed; -i ignore malformed judge
      JSON so a flaky verdict never fails the build; -n 1 serial for the 5-RPM free-tier ceiling —
      spike 002.) ``assert_test`` RAISES below threshold, so it is reserved for THIS opt-in lane
      only. It is NON-BLOCKING: it never participates in ``scripts/release_gate.py``'s deterministic
      exit code — the deterministic ``recall@k`` / ``citation_accuracy`` carry the release gate,
      because hard-gating a run-to-run-variable LLM judge is itself a critical failure mode.
"""
from __future__ import annotations

import os

import pytest

from eval.metrics.faithfulness_deepeval import NOT_MEASURED, faithfulness_deepeval

# ---------------------------------------------------------------------------
# Skip marker for the opt-in, key-gated assert_test lane
# ---------------------------------------------------------------------------

# Gate on an EXPLICIT opt-in flag, not mere GEMINI_API_KEY presence: DeepEval's pytest
# plugin auto-loads the repo .env, so a key-only skip never actually skips locally and the
# lane would red the default suite on free-tier quota. Every other live test in this repo
# uses an explicit flag (--run-eval, --run-langfuse, NSE_LIVE_SMOKE, RUN_SLOW_EMBED); match
# that. Run this lane with: RUN_FAITHFULNESS_JUDGE=1 pytest ..., or `deepeval test run ... -c -i -n 1`.
_requires_gemini = pytest.mark.skipif(
    not os.environ.get("RUN_FAITHFULNESS_JUDGE"),
    reason=(
        "opt-in faithfulness judge lane — set RUN_FAITHFULNESS_JUDGE=1 (and GEMINI_API_KEY) to run, "
        "or use `deepeval test run tests/eval/test_faithfulness_deepeval.py -c -i -n 1`. "
        "Non-blocking; skipped by default so .env auto-load / free-tier quota never reds the suite."
    ),
)


# ---------------------------------------------------------------------------
# (a) ALWAYS-ON: the -1 "not measured" sentinel (default CI, no key, no judge call)
# ---------------------------------------------------------------------------


def test_not_measured_sentinel_without_key(monkeypatch) -> None:
    """With GEMINI_API_KEY unset, faithfulness_deepeval reports -1.0 and does NOT raise.

    This is the report-not-crash guarantee: an unset key (default CI) yields the documented
    "not measured" sentinel, never a misleading 0.0 and never an exception. No live judge call.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    score, reason = faithfulness_deepeval(
        question="What was net loss in FY2024?",
        answer="Net loss was Rs 2,350 crore.",
        contexts=["FY2024 net loss Rs 2,350 crore."],
    )

    assert score == NOT_MEASURED == -1.0
    assert "not measured" in reason.lower()


# ---------------------------------------------------------------------------
# (b) OPT-IN: assert_test faithfulness lane (needs GEMINI_API_KEY; skipped otherwise)
# ---------------------------------------------------------------------------


@_requires_gemini
def test_faithful_fixture_assert_test_optin() -> None:
    """Opt-in gated lane: a faithful answer clears the 0.95 target on the gemini-3.5-flash judge.

    Fixture is spike 002's faithful case (measured ~1.00). ``assert_test`` RAISES below threshold,
    so this runs ONLY with a key present and ONLY via `deepeval test run ... -c -i -n 1`. It is
    non-blocking — it never gates ``scripts/release_gate.py``.
    """
    from deepeval import assert_test
    from deepeval.metrics import FaithfulnessMetric
    from deepeval.models import GeminiModel
    from deepeval.test_case import LLMTestCase

    context = [
        "FY2024 revenue Rs 11,000 crore (FY2023 Rs 8,265 crore); net loss Rs 2,350 crore.",
    ]
    test_case = LLMTestCase(
        input="What were FY2024 revenue and net loss?",
        actual_output="Revenue Rs 11,000 cr; net loss Rs 2,350 cr.",
        retrieval_context=context,
    )

    judge = GeminiModel(
        model="gemini-3.5-flash",
        api_key=os.environ["GEMINI_API_KEY"],
        temperature=0.0,
    )
    metric = FaithfulnessMetric(
        threshold=0.95,
        model=judge,
        include_reason=True,
        async_mode=False,  # serial: 5-RPM free-tier ceiling
    )

    # Free-tier gemini-3.5-flash is capped at 5 RPM AND 20 requests/day (spike 002).
    # A quota exhaustion is NOT a faithfulness verdict — skip rather than fail so the
    # non-blocking opt-in lane never reports a red on a rate limit. run_async=False keeps
    # the judge serial (matching the `-n 1` intent) instead of bursting concurrent claims.
    try:
        assert_test(test_case, [metric], run_async=False)
    except Exception as exc:  # noqa: BLE001 — narrow via message; avoids a google.genai import
        msg = str(exc)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg or "quota" in msg.lower():
            pytest.skip(f"gemini free-tier quota exhausted (5 RPM / 20 per day) — not a faithfulness failure: {msg[:120]}")
        raise
