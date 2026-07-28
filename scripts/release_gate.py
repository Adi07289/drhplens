"""
scripts/release_gate.py — the DRHPLens RELEASE GATE (EVAL-01 / EVAL-03 / D3-12).

Enforcement over discipline (RESEARCH Pitfall 4): a regression must physically
block deploy, not merely print a warning. `make release` invokes this script; it
runs TWO gates, both of which `sys.exit(1)` (and write a dated report) on breach:

  1. Deterministic eval gate (offline) — reads the committed
     `eval/reports/eval_summary.json` via the SHARED `eval.metrics.EvalSummary`
     schema and hard-gates `citation_accuracy >= CITATION_ACCURACY_GATE` (0.95)
     AND `recall@10 >= RECALL_AT_10_GATE` (0.85). `faithfulness_deepeval` is
     REPORTED, never gated (the LLM-judge is non-deterministic; hard-gating it is
     itself a flaky-gate failure mode) — a low value or the `-1` "not measured"
     sentinel never affects the exit code.
  2. Numeric-faithfulness gate (live) — enforces
     `agent.policies.NUMERIC_FAITHFULNESS_GATE` (0.95), UNCHANGED.

Two-layer design so each enforcement is unit-testable offline:
  - `enforce_gate(numeric_faithfulness, report_dir=...)` and
    `enforce_eval_gates(summary, report_dir=...)` are PURE: they take the parsed
    inputs directly, read thresholds from policy, write the report + exit non-zero
    on breach, and return None otherwise. NO live-infra import lives in either —
    `tests/eval/test_release_gate.py` drives both branches with no live call.
  - `main()` runs the offline eval gate against the committed artifact, then the
    LIVE numeric track (reusing run_eval + the importable
    compute_numeric_faithfulness). The only live-infra call lives there.

Usage:
    python scripts/release_gate.py          # runs both gates; exits non-zero on breach
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

from agent.policies import (  # noqa: E402
    CITATION_ACCURACY_GATE,
    NUMERIC_FAITHFULNESS_GATE,
    RECALL_AT_10_GATE,
)
from eval.metrics import EvalSummary  # noqa: E402

DEFAULT_REPORT_DIR = PROJECT_ROOT / "eval" / "reports"
DEFAULT_EVAL_SUMMARY = DEFAULT_REPORT_DIR / "eval_summary.json"


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


def _write_eval_gate_report(
    summary: EvalSummary,
    citation_passed: bool,
    recall_passed: bool,
    passed: bool,
    report_dir: Path,
) -> Path:
    """Write the dated deterministic eval-gate markdown report.

    Pure I/O — no live-infra import (mirrors ``_write_gate_report``). Called by
    ``enforce_eval_gates`` on BOTH branches so a pass leaves an auditable record
    too. Records the two GATED deterministic metrics (citation_accuracy,
    recall@10) with PASS/FAIL against their thresholds AND records
    ``faithfulness_deepeval`` with a ">= 0.95 target (REPORTED, not gated)" line
    — the faithfulness value is written for provenance but NEVER affects
    ``passed``.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{date.today()}-eval-gate.md"

    agg = summary.aggregate
    citation = agg.citation_accuracy
    recall = agg.recall_at_10
    faithfulness = agg.faithfulness_deepeval

    citation_status = "PASS" if citation_passed else "FAIL"
    recall_status = "PASS" if recall_passed else "FAIL"
    decision = (
        "Deploy ALLOWED — both deterministic gates meet their thresholds."
        if passed
        else "Deploy BLOCKED — a deterministic gate exits non-zero; the build halts here."
    )

    # faithfulness_deepeval: -1.0 is the documented "not measured" sentinel, never a real 0.0.
    if faithfulness < 0:
        faithfulness_cell = "-1.000 (not measured — sentinel)"
    else:
        faithfulness_cell = f"{faithfulness:.3f}"

    lines = [
        f"# Deterministic Eval Release Gate — {date.today()}",
        "",
        "## Decision",
        "",
        "| Metric | Value | Gate (>=) | Status |",
        "|---|---|---|---|",
        f"| citation_accuracy | {citation:.3f} | {CITATION_ACCURACY_GATE} | {citation_status} |",
        f"| recall@10 | {recall:.3f} | {RECALL_AT_10_GATE} | {recall_status} |",
        "",
        f"**{decision}**",
        "",
        "## Reported (NOT gated)",
        "",
        "| Metric | Value | Target (>=) | Status |",
        "|---|---|---|---|",
        f"| faithfulness_deepeval | {faithfulness_cell} | "
        f"{NUMERIC_FAITHFULNESS_GATE} target | REPORTED |",
        "",
        "**faithfulness_deepeval is REPORTED, not gated (T-6.1-16).** The DeepEval "
        "LLM-judge is non-deterministic run-to-run; hard-gating it is itself a "
        "critical failure mode (flaky gate). A low faithfulness — or the `-1` "
        "\"not measured\" sentinel (key unset / rate-limited) — NEVER exits "
        "non-zero. It renders a >= 0.95 target line for context only.",
        "",
        "## Interpretation (P10)",
        "",
        "- **citation_accuracy** (>= "
        f"{CITATION_ACCURACY_GATE}) is the project's custom deterministic "
        "attribution metric — \"did the cited page actually contain the claim\". "
        "A regression is a hard CI failure (CLAUDE.md project rule).",
        "- **recall@10** (>= "
        f"{RECALL_AT_10_GATE}) is a labelled REGRESSION FLOOR, not a headline "
        "quality metric (P10). It is saturated at 1.00 on the current gold set's "
        "coarse section-level page ranges (spike 003, mean 44.5-page spans); the "
        "0.85 floor is a regression tripwire set just below real performance, "
        "never advertised as a quality win.",
        "- Both thresholds are policy constants "
        "(`agent.policies.CITATION_ACCURACY_GATE` / `RECALL_AT_10_GATE`); they are "
        "enforced, not relaxed. Fix retrieval/attribution and re-run; do NOT lower "
        "the gate.",
        "",
        f"- Corpus: {summary.corpus.gold_set} — {summary.corpus.ipo} "
        f"({summary.corpus.n_questions} questions); judge: {summary.judge_model}.",
        f"- Generated: {date.today()} by scripts/release_gate.py.",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def enforce_eval_gates(
    summary: EvalSummary,
    report_dir: Path | None = None,
) -> None:
    """Refuse (sys.exit(1) + report) below the deterministic eval gates; pass otherwise.

    PURE enforcement logic — takes an already-parsed ``EvalSummary`` directly,
    reads the thresholds from ``agent.policies``, and contains NO live-infra call
    (no vector-DB / LLM-client / eval-runner import), so it is unit-tested offline
    on injected EvalSummary values. The gate reads the runner's committed metrics
    through the SHARED ``eval.metrics`` schema — no independent re-computation, so
    the report and the gate can never diverge (T-6.1-15).

    Gated (deterministic): ``citation_accuracy >= CITATION_ACCURACY_GATE`` AND
    ``recall_at_10 >= RECALL_AT_10_GATE``. Reported-only: ``faithfulness_deepeval``
    — a low value or the ``-1`` "not measured" sentinel NEVER affects the exit
    code (T-6.1-16).

    Args:
        summary: the parsed EvalSummary (from ``eval_summary.json``).
        report_dir: where to write the dated eval-gate report
            (defaults to eval/reports/). Tests pass a tmp dir.

    Returns:
        None when both deterministic gates pass (deploy allowed).

    Raises:
        SystemExit(1) when citation_accuracy < gate OR recall@10 < gate
        (deploy blocked) — a report is written first so the failure is auditable.
    """
    target_dir = report_dir if report_dir is not None else DEFAULT_REPORT_DIR

    agg = summary.aggregate
    citation_passed = agg.citation_accuracy >= CITATION_ACCURACY_GATE
    recall_passed = agg.recall_at_10 >= RECALL_AT_10_GATE
    passed = citation_passed and recall_passed

    report_path = _write_eval_gate_report(
        summary, citation_passed, recall_passed, passed, target_dir
    )

    if not passed:
        breaches = []
        if not citation_passed:
            breaches.append(
                f"citation_accuracy={agg.citation_accuracy:.3f} "
                f"< {CITATION_ACCURACY_GATE} (agent.policies.CITATION_ACCURACY_GATE)"
            )
        if not recall_passed:
            breaches.append(
                f"recall@10={agg.recall_at_10:.3f} "
                f"< {RECALL_AT_10_GATE} (agent.policies.RECALL_AT_10_GATE)"
            )
        print("RELEASE GATE FAILED: " + "; ".join(breaches) + ".")
        print(f"Report written to: {report_path}")
        print("Deploy is BLOCKED. Fix retrieval/attribution; do not lower the gate.")
        sys.exit(1)

    print(
        f"EVAL GATE OK: citation_accuracy={agg.citation_accuracy:.3f} "
        f">= {CITATION_ACCURACY_GATE}, recall@10={agg.recall_at_10:.3f} "
        f">= {RECALL_AT_10_GATE}. Report: {report_path}"
    )


def enforce_eval_gates_from_file(
    summary_path: Path | None = None,
    report_dir: Path | None = None,
) -> None:
    """Read the committed eval_summary.json via the shared schema, then enforce.

    Thin I/O wrapper: parses ``eval_summary.json`` through
    ``EvalSummary.model_validate_json`` (the SAME schema the runner writes) and
    delegates to the pure ``enforce_eval_gates``. Kept separate so the enforcement
    logic stays offline-testable on injected EvalSummary values.
    """
    path = summary_path if summary_path is not None else DEFAULT_EVAL_SUMMARY
    summary = EvalSummary.model_validate_json(path.read_text(encoding="utf-8"))
    enforce_eval_gates(summary, report_dir=report_dir)


def main() -> None:
    """Run BOTH release gates: the deterministic eval gate AND the live numeric gate.

    1. Deterministic eval gate (offline): read the committed
       ``eval/reports/eval_summary.json`` via the shared ``EvalSummary`` schema and
       hard-gate citation_accuracy + recall@10 (faithfulness reported-only).
    2. Live numeric gate: reuse run_eval._check_env fail-fast and the importable
       compute_numeric_faithfulness so the gate enforces the SAME number the
       numeric-track report shows. This is the only live-infra path in this module.

    Both gates fire; neither is removed. The deterministic gate runs first so an
    already-committed regression blocks deploy without touching live infra.
    """
    # 1) Deterministic eval gate — offline, reads the committed artifact.
    enforce_eval_gates_from_file()

    # 2) Live numeric-faithfulness gate — UNCHANGED.
    from scripts.run_eval import compute_numeric_faithfulness

    # The gate scores the DISCLOSED subset only — numeric_faithfulness is a GROUNDING
    # metric, valid only for numbers the DRHP actually states. Derived/computed answers
    # (margins, growth %, ratios, lakh restatements) cannot ground by construction and
    # are tracked as a separate reasoning eval. Rationale + full split (not score-gaming):
    # eval/gold/NUMERIC_EVAL_SPLIT.md.
    numeric_faithfulness = compute_numeric_faithfulness(
        numeric_set_path="eval/gold/numeric_eval_disclosed.jsonl",
        output_dir="eval/reports",
        write_report=True,
    )
    enforce_gate(numeric_faithfulness)


if __name__ == "__main__":
    main()
