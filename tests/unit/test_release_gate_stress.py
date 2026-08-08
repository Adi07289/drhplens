"""
Unit test — the D-09 STRESS release-gate lane (06.3-07), unit-tested OFFLINE.

Two things are pinned here, both without touching live infra:

  1. ``enforce_stress_gate`` is the PURE enforcement boundary: a RED result
     (any failure / collection error / all-skipped run) exits non-zero AND writes a
     dated ``*-stress-gate.md`` report; a GREEN result passes and writes a PASS
     report. Mirrors ``tests/eval/test_release_gate.py`` — the subprocess lives in
     ``run_stress_suite``, so the enforcement is driven here on injected results.
  2. ``FAILURE_MODES`` (app/observability/trace_enrichment.py) keeps its original 8
     entries at their original indices (stable Langfuse codes) and appends the five
     new supervisor modes at the END — saved Cloud views must never silently shift.

Requirement: D-09. Function/dataclass names are LOCKED. Fully offline (no live
Qdrant/Gemini, no subprocess): ``enforce_stress_gate`` takes a StressResult directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.release_gate import (  # noqa: E402
    StressResult,
    _parse_pytest_summary,
    enforce_stress_gate,
)

# ---------------------------------------------------------------------------
# enforce_stress_gate — the pure enforcement boundary (green passes / red blocks)
# ---------------------------------------------------------------------------


def test_stress_gate_blocks_on_failure(tmp_path: Path) -> None:
    """A RED result (>=1 failure) hard-blocks: non-zero exit + a FAIL report that
    names the breaching case."""
    red = StressResult(
        passed=False,
        passed_count=25,
        failed_count=1,
        skipped_count=4,
        returncode=1,
        failures=("tests/eval/test_stress_suite.py::test_stress_envelope[cb-001]",),
    )
    with pytest.raises(SystemExit) as exc_info:
        enforce_stress_gate(red, report_dir=tmp_path)

    # Non-zero exit is the enforcement boundary (T-6.3-GATE).
    assert exc_info.value.code is not None
    assert exc_info.value.code != 0

    reports = list(tmp_path.glob("*-stress-gate.md"))
    assert reports, "the stress gate must write a *-stress-gate.md report on refusal"
    body = reports[0].read_text(encoding="utf-8")
    assert "FAIL" in body
    assert "BLOCKED" in body
    assert "cb-001" in body  # the breaching case is named in the report


def test_stress_gate_blocks_on_collection_error(tmp_path: Path) -> None:
    """A collection error (error_count>0) also blocks — a suite that could not even
    run is NOT a silent pass."""
    errored = StressResult(passed=False, passed_count=0, error_count=1, returncode=2)
    with pytest.raises(SystemExit) as exc_info:
        enforce_stress_gate(errored, report_dir=tmp_path)
    assert exc_info.value.code != 0
    assert list(tmp_path.glob("*-stress-gate.md"))


def test_stress_gate_passes_on_green(tmp_path: Path) -> None:
    """A GREEN result (failures==0, errors==0, >=1 passed) does NOT raise and writes
    an auditable PASS report."""
    green = StressResult(
        passed=True,
        passed_count=26,
        failed_count=0,
        skipped_count=4,
        returncode=0,
    )
    enforce_stress_gate(green, report_dir=tmp_path)  # no SystemExit

    reports = list(tmp_path.glob("*-stress-gate.md"))
    assert reports, "the stress gate writes an auditable report on pass too"
    body = reports[0].read_text(encoding="utf-8")
    assert "PASS" in body
    assert "ALLOWED" in body


def test_stress_gate_advice_by_implication_is_reported_not_gated(tmp_path: Path) -> None:
    """The report must document that advice-by-implication stays a SEPARATE REPORTED
    lane — never part of this deterministic gate (AI-SPEC §5, load-bearing)."""
    enforce_stress_gate(StressResult(passed=True, passed_count=26), report_dir=tmp_path)
    body = next(tmp_path.glob("*-stress-gate.md")).read_text(encoding="utf-8")
    assert "REPORTED" in body
    assert "advice-by-implication" in body.lower()


# ---------------------------------------------------------------------------
# _parse_pytest_summary — returncode/count logic (all-skipped is NOT a pass)
# ---------------------------------------------------------------------------


def test_parse_green_run_is_pass() -> None:
    """A clean run (rc=0, some passed, no failures) parses to passed=True."""
    out = "........................\n26 passed, 4 skipped in 23.05s\n"
    result = _parse_pytest_summary(out, returncode=0)
    assert result.passed is True
    assert result.passed_count == 26
    assert result.skipped_count == 4
    assert result.failed_count == 0


def test_parse_failed_run_is_block() -> None:
    """A run with failures parses to passed=False and captures the FAILED node-ids."""
    out = (
        "FAILED tests/eval/test_stress_suite.py::test_stress_envelope[jb-002]\n"
        "1 failed, 25 passed, 4 skipped in 24.10s\n"
    )
    result = _parse_pytest_summary(out, returncode=1)
    assert result.passed is False
    assert result.failed_count == 1
    assert result.failures == (
        "tests/eval/test_stress_suite.py::test_stress_envelope[jb-002]",
    )


def test_parse_all_skipped_is_not_a_pass() -> None:
    """rc=0 with ZERO passed (e.g. the whole suite importorskipped) must NOT be a
    silent pass — the offline gate would otherwise do nothing."""
    out = "1 skipped in 0.30s\n"
    result = _parse_pytest_summary(out, returncode=0)
    assert result.passed is False
    assert result.passed_count == 0


# ---------------------------------------------------------------------------
# FAILURE_MODES — append-only (original 8 indices stable, 5 new appended)
# ---------------------------------------------------------------------------

_ORIGINAL_8 = (
    "low_retrieval_score",
    "unsupported_claim",
    "banned_token",
    "infrastructure_error",
    "retrieval_miss",
    "cite_check_fail",
    "judge_flag",
    "crash",
)

_APPENDED_5 = (
    "budget_trip",
    "advice_bait_refused",
    "jailbreak_blocked",
    "honest_partial",
    "tool_abstain",
)


def test_failure_modes_original_eight_indices_are_stable() -> None:
    """The first 8 modes keep their original ORDER and indices — the numeric codes
    are 1-based indices, and saved Langfuse Cloud views filter on them (T-6.3 stable
    codes)."""
    from app.observability.trace_enrichment import FAILURE_MODES

    assert FAILURE_MODES[:8] == _ORIGINAL_8


def test_failure_modes_five_new_modes_appended_at_end() -> None:
    """The five supervisor-level modes are appended at the END (indices 9-13)."""
    from app.observability.trace_enrichment import FAILURE_MODES

    assert FAILURE_MODES[8:] == _APPENDED_5
    assert len(FAILURE_MODES) == 13
    # No duplicates — every mode maps to a distinct code.
    assert len(set(FAILURE_MODES)) == len(FAILURE_MODES)


def test_failure_mode_codes_are_stable_and_distinct() -> None:
    """The original 8 codes are unchanged (1..8) and the new modes get distinct
    non-zero codes (9..13); an unknown label falls back to 0.0."""
    from app.observability.trace_enrichment import (
        _failure_mode_value,
        FAILURE_MODES,
    )

    # Original codes pinned to their historical values.
    assert _failure_mode_value("low_retrieval_score") == 1.0
    assert _failure_mode_value("crash") == 8.0
    # New modes get distinct codes 9..13.
    assert _failure_mode_value("budget_trip") == 9.0
    assert _failure_mode_value("tool_abstain") == 13.0
    codes = {mode: _failure_mode_value(mode) for mode in FAILURE_MODES}
    assert len(set(codes.values())) == len(FAILURE_MODES)  # all distinct
    # Unknown label → 0.0 fallback (unchanged contract).
    assert _failure_mode_value("not_a_real_mode") == 0.0
