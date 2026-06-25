"""
scripts/release_gate.py — the numeric-faithfulness RELEASE GATE (EVAL-03 / D3-12).

Enforcement over discipline (RESEARCH Pitfall 4): a hallucinated number must
physically block deploy, not merely print a warning. `make release` invokes this
script; when the measured numeric_faithfulness is below
`agent.policies.NUMERIC_FAITHFULNESS_GATE`, the gate writes a dated report AND
calls `sys.exit(1)`, so Make halts the build.

Two-layer design so the enforcement logic is unit-testable offline:
  - `enforce_gate(numeric_faithfulness, report_dir=...)` is PURE: it takes the
    score directly, reads the threshold from policy, writes the report + exits
    non-zero below it, and returns None at/above it. NO live-infra import lives
    in this function — `tests/eval/test_release_gate.py` drives both branches
    (a below-threshold score and at/above-threshold scores) with no live call.
  - `main()` runs the LIVE numeric track (reusing run_eval._check_env fail-fast +
    the importable compute_numeric_faithfulness) and feeds the score to
    enforce_gate. The only live-infra call lives here.

Usage:
    python scripts/release_gate.py          # live run; exits non-zero if < gate
    make release                            # same, via the Makefile target
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root on path (mirrors run_eval.py / calibrate_gate1.py posture)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.policies import NUMERIC_FAITHFULNESS_GATE  # noqa: E402

DEFAULT_REPORT_DIR = PROJECT_ROOT / "eval" / "reports"


def _write_gate_report(
    numeric_faithfulness: float,
    passed: bool,
    report_dir: Path,
) -> Path:
    """Write the dated numeric-gate markdown report (mirrors run_eval's writer).

    Pure I/O — no live-infra import. Called by enforce_gate on BOTH branches so a
    pass leaves an auditable record too, but the gate's *enforcement* (sys.exit)
    is what blocks deploy.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{date.today()}-numeric-gate.md"

    status = "PASS" if passed else "FAIL"
    decision = (
        "Deploy ALLOWED — numeric_faithfulness meets the gate."
        if passed
        else "Deploy BLOCKED — gate exits non-zero; the build halts here."
    )

    lines = [
        f"# Numeric-Faithfulness Release Gate — {date.today()}",
        "",
        "## Decision",
        "",
        "| Metric | Value | Gate (>=) | Status |",
        "|---|---|---|---|",
        f"| numeric_faithfulness | {numeric_faithfulness:.3f} | "
        f"{NUMERIC_FAITHFULNESS_GATE} | {status} |",
        "",
        f"**{decision}**",
        "",
        "**Interpretation (P10):** numeric_faithfulness is the fraction of "
        "numeric-only eval questions (`eval/gold/numeric_eval.jsonl`) whose "
        "*every* emitted number grounds to a cited DRHP span via the "
        "deterministic, non-LLM cite_check antibody (D3-10). The "
        f">= {NUMERIC_FAITHFULNESS_GATE} threshold is the ROADMAP cross-phase "
        "invariant; it is enforced, not relaxed. A FAIL means at least one "
        "emitted number could not be grounded — fix the extractor / tune "
        "tolerances per the rubric and re-run; do NOT lower the gate.",
        "",
        f"- Threshold source: `agent.policies.NUMERIC_FAITHFULNESS_GATE`.",
        f"- Generated: {date.today()} by scripts/release_gate.py.",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def enforce_gate(
    numeric_faithfulness: float,
    report_dir: Path | None = None,
) -> None:
    """Refuse (sys.exit(1) + report) below the policy gate; pass at/above it.

    PURE enforcement logic — takes the score directly, reads the threshold from
    `agent.policies.NUMERIC_FAITHFULNESS_GATE`, and contains NO live-infra call
    (no vector-DB or LLM-client import), so it is unit-tested offline on
    injected scores below and at/above the threshold.

    Args:
        numeric_faithfulness: the measured score in [0.0, 1.0].
        report_dir: where to write the dated numeric-gate report
            (defaults to eval/reports/). Tests pass a tmp dir.

    Returns:
        None when numeric_faithfulness >= threshold (deploy allowed).

    Raises:
        SystemExit(1) when numeric_faithfulness < threshold (deploy blocked) —
        a report is written first so the failure is auditable.
    """
    target_dir = report_dir if report_dir is not None else DEFAULT_REPORT_DIR
    passed = numeric_faithfulness >= NUMERIC_FAITHFULNESS_GATE
    report_path = _write_gate_report(numeric_faithfulness, passed, target_dir)

    if not passed:
        print(
            f"RELEASE GATE FAILED: numeric_faithfulness="
            f"{numeric_faithfulness:.3f} < {NUMERIC_FAITHFULNESS_GATE} "
            f"(agent.policies.NUMERIC_FAITHFULNESS_GATE)."
        )
        print(f"Report written to: {report_path}")
        print("Deploy is BLOCKED. Fix the numbers; do not lower the gate.")
        sys.exit(1)

    print(
        f"RELEASE GATE OK: numeric_faithfulness={numeric_faithfulness:.3f} "
        f">= {NUMERIC_FAITHFULNESS_GATE}. Report: {report_path}"
    )


def main() -> None:
    """Run the LIVE numeric track and enforce the gate.

    The only live-infra path in this module: reuses run_eval._check_env fail-fast
    and the importable compute_numeric_faithfulness so the gate enforces the SAME
    number the numeric-track report shows.
    """
    from scripts.run_eval import compute_numeric_faithfulness

    numeric_faithfulness = compute_numeric_faithfulness(
        numeric_set_path="eval/gold/numeric_eval.jsonl",
        output_dir="eval/reports",
        write_report=True,
    )
    enforce_gate(numeric_faithfulness)


if __name__ == "__main__":
    main()
