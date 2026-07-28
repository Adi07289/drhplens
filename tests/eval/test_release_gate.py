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

from agent.policies import (  # noqa: E402
    CITATION_ACCURACY_GATE,
    NUMERIC_FAITHFULNESS_GATE,
    RECALL_AT_10_GATE,
)
from eval.metrics import Aggregate, Corpus, EvalSummary  # noqa: E402
from scripts.release_gate import enforce_eval_gates, enforce_gate  # noqa: E402


def _summary(
    *,
    citation_accuracy: float = 1.0,
    recall_at_10: float = 1.0,
    faithfulness_deepeval: float = -1.0,
) -> EvalSummary:
    """Build an in-memory EvalSummary fixture (no live services).

    Only the three gate-relevant aggregate fields vary; the rest are valid
    defaults so the honesty invariants (named judge, n>0) hold.
    """
    return EvalSummary(
        generated="2026-07-28",
        judge_model="gemini-3.5-flash",
        corpus=Corpus(gold_set="tests/eval/gold_set.jsonl", ipo="Swiggy DRHP", n_questions=13),
        aggregate=Aggregate(
            faithfulness_deepeval=faithfulness_deepeval,
            citation_accuracy=citation_accuracy,
            recall_at_5=1.0,
            recall_at_10=recall_at_10,
            recall_at_30=1.0,
        ),
        report="eval/reports/2026-07-28-rag-eval.md",
    )


def test_eval_gate_blocks_on_citation_below_threshold(tmp_path: Path) -> None:
    """citation_accuracy=0.94 (< 0.95) hard-blocks: non-zero exit + FAIL report."""
    assert CITATION_ACCURACY_GATE == 0.95
    with pytest.raises(SystemExit) as exc_info:
        enforce_eval_gates(_summary(citation_accuracy=0.94), report_dir=tmp_path)

    assert exc_info.value.code is not None
    assert exc_info.value.code != 0

    reports = list(tmp_path.glob("*-eval-gate.md"))
    assert reports, "gate must write a *-eval-gate.md report on refusal"
    body = reports[0].read_text(encoding="utf-8")
    assert "0.940" in body
    assert "FAIL" in body


def test_eval_gate_blocks_on_recall_below_threshold(tmp_path: Path) -> None:
    """recall@10=0.80 (< 0.85) hard-blocks even when citation passes."""
    assert RECALL_AT_10_GATE == 0.85
    with pytest.raises(SystemExit) as exc_info:
        enforce_eval_gates(
            _summary(citation_accuracy=1.0, recall_at_10=0.80), report_dir=tmp_path
        )

    assert exc_info.value.code is not None
    assert exc_info.value.code != 0

    reports = list(tmp_path.glob("*-eval-gate.md"))
    assert reports, "gate must write a *-eval-gate.md report on refusal"
    body = reports[0].read_text(encoding="utf-8")
    assert "0.800" in body
    assert "FAIL" in body


def test_eval_gate_does_not_block_on_low_faithfulness(tmp_path: Path) -> None:
    """The KEY acceptance: passing deterministic metrics + a LOW faithfulness
    (0.10, well below the 0.95 target) must NOT raise — faithfulness is reported,
    never gated (T-6.1-16)."""
    enforce_eval_gates(
        _summary(citation_accuracy=0.96, recall_at_10=0.90, faithfulness_deepeval=0.10),
        report_dir=tmp_path,
    )  # no SystemExit

    reports = list(tmp_path.glob("*-eval-gate.md"))
    assert reports, "gate must write an auditable *-eval-gate.md report on pass too"
    body = reports[0].read_text(encoding="utf-8")
    assert "PASS" in body
    # faithfulness is present but flagged reported-not-gated.
    assert "REPORTED" in body
    assert "0.100" in body


def test_eval_gate_does_not_block_on_unmeasured_faithfulness(tmp_path: Path) -> None:
    """faithfulness=-1 (the 'not measured' sentinel) still does not block — a
    key-unset / rate-limited run must not flake the gate."""
    enforce_eval_gates(
        _summary(citation_accuracy=1.0, recall_at_10=1.0, faithfulness_deepeval=-1.0),
        report_dir=tmp_path,
    )  # no SystemExit

    reports = list(tmp_path.glob("*-eval-gate.md"))
    assert reports
    body = reports[0].read_text(encoding="utf-8")
    assert "PASS" in body
    assert "not measured" in body.lower()


def test_eval_gate_boundary_passes_at_thresholds(tmp_path: Path) -> None:
    """Exactly at the thresholds (>=) passes; the gate is not strictly-greater."""
    enforce_eval_gates(
        _summary(citation_accuracy=0.95, recall_at_10=0.85), report_dir=tmp_path
    )  # no SystemExit
    reports = list(tmp_path.glob("*-eval-gate.md"))
    assert reports
    assert "PASS" in reports[0].read_text(encoding="utf-8")


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
