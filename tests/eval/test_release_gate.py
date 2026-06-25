"""
Eval test — the numeric-faithfulness release gate LOGIC (D3-12), unit-tested
offline on a synthetic score: below NUMERIC_FAITHFULNESS_GATE (0.95) exits
non-zero AND writes a report; at/above passes. Enforcement over discipline — the
gate physically refuses deploy.

Requirement: EVAL-03. Plan 05 implements scripts/release_gate.py.
Function names are LOCKED. These tests are fully offline (no live Qdrant/Gemini):
enforce_gate takes the score directly, so no live computation is invoked.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.policies import NUMERIC_FAITHFULNESS_GATE  # noqa: E402
from scripts.release_gate import enforce_gate  # noqa: E402


def test_gate_exits_nonzero_below_threshold(tmp_path: Path) -> None:
    """A synthetic numeric_faithfulness of 0.94 makes the gate exit non-zero
    and writes a dated numeric-gate report (no live infra)."""
    with pytest.raises(SystemExit) as exc_info:
        enforce_gate(0.94, report_dir=tmp_path)

    # Non-zero exit code — the enforcement boundary (T-03-09).
    assert exc_info.value.code is not None
    assert exc_info.value.code != 0

    # The gate must WRITE a report when it refuses, not just exit.
    reports = list(tmp_path.glob("*-numeric-gate.md"))
    assert reports, "gate must write a *-numeric-gate.md report on refusal"
    body = reports[0].read_text(encoding="utf-8")
    assert "0.94" in body
    assert "FAIL" in body or "fail" in body.lower()


def test_gate_passes_at_or_above_threshold(tmp_path: Path) -> None:
    """0.96 and exactly 0.95 (>= threshold) pass without a non-zero exit."""
    # 0.96 — clearly above threshold.
    enforce_gate(0.96, report_dir=tmp_path)

    # 0.95 exactly — the gate is >= (boundary passes), not strictly greater.
    assert NUMERIC_FAITHFULNESS_GATE == 0.95
    enforce_gate(0.95, report_dir=tmp_path)
