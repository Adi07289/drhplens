"""
scripts/calibrate_gate1.py — Gate 1 threshold calibration (RESEARCH Open Question 1).

Sweeps GATE1_THRESHOLD from -2.0 to +2.0 in 0.5 steps against tests/eval/gold_set.jsonl.
Runs the graph once per gold entry (gathering gate1_max_score), then sweeps analytically.
Emits recommended threshold that maximizes (correct_grounded + correct_refusals).

Per RESEARCH Open Question 1: "Sweep ±2.0 in 0.5 steps. Pick the threshold that
maximizes (correct_grounded + correct_refusals) on the gold set. Document the chosen
value in agent/policies.py as a named constant."

Usage:
    python scripts/calibrate_gate1.py
    python scripts/calibrate_gate1.py --gold-set tests/eval/gold_set.jsonl
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CANDIDATE_THRESHOLDS = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]


def _check_env() -> None:
    import os
    missing = [v for v in ("GEMINI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY") if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing env vars: {missing}")
        print("Fill in your .env and run: python scripts/calibrate_gate1.py")
        sys.exit(1)


def run_calibration(
    gold_set_path: str = "tests/eval/gold_set.jsonl",
    output_dir: str = "eval/reports",
) -> None:
    """Run the Gate 1 calibration sweep and print/save results."""
    _check_env()

    gold_path = PROJECT_ROOT / gold_set_path
    if not gold_path.exists():
        print(f"ERROR: gold set not found at {gold_path}")
        sys.exit(1)

    entries = [
        json.loads(line)
        for line in gold_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    print(f"Loaded {len(entries)} gold set entries from {gold_path}")

    try:
        from agent.graph import GRAPH
    except ImportError as exc:
        print(f"ERROR: Cannot import agent: {exc}")
        sys.exit(1)

    # ---------------------------------------------------------------------------
    # Step 1: Run graph once per entry, collect gate1_max_score
    # ---------------------------------------------------------------------------
    print("\nCollecting gate1_max_score for each gold entry...")
    scores: list[tuple[float, bool]] = []  # (gate1_max_score, is_refusal_expected)

    for entry in entries:
        qid = entry["qid"]
        question = entry["question"]
        is_refusal_expected = entry["is_refusal_expected"]
        print(f"  [{qid}] {question[:55]}...", end=" ", flush=True)

        try:
            # We only need gate1_max_score — the graph short-circuits at gate1_check
            # for refusals, and computes it for grounded entries before calling LLM.
            final_state = GRAPH.invoke({"question": question})
            max_score = final_state.get("gate1_max_score", -1.0)
            scores.append((max_score, is_refusal_expected))
            print(f"score={max_score:.4f}")
        except Exception as exc:
            print(f"FAILED ({exc})")
            scores.append((-1.0, is_refusal_expected))

    # ---------------------------------------------------------------------------
    # Step 2: Sweep thresholds analytically
    # ---------------------------------------------------------------------------
    print(f"\nSwept thresholds: {CANDIDATE_THRESHOLDS}")
    print(f"\n{'Threshold':>12} {'TP':>5} {'TN':>5} {'FP':>5} {'FN':>5} {'Precision':>10} {'Recall':>8} {'Objective':>10}")
    print("-" * 75)

    best_objective = -1
    best_threshold = 0.0
    sweep_results = []

    for tau in CANDIDATE_THRESHOLDS:
        tp = tn = fp = fn = 0
        for (score, is_refusal_expected) in scores:
            would_refuse = score < tau
            if is_refusal_expected and would_refuse:
                tp += 1
            elif not is_refusal_expected and not would_refuse:
                tn += 1
            elif not is_refusal_expected and would_refuse:
                fp += 1
            elif is_refusal_expected and not would_refuse:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        objective = tp + tn

        print(f"{tau:>12.1f} {tp:>5} {tn:>5} {fp:>5} {fn:>5} {precision:>10.3f} {recall:>8.3f} {objective:>10}")
        sweep_results.append({
            "threshold": tau, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "objective": objective,
        })

        if objective > best_objective or (objective == best_objective and tau < best_threshold):
            best_objective = objective
            best_threshold = tau

    # ---------------------------------------------------------------------------
    # Step 3: Recommendation
    # ---------------------------------------------------------------------------
    n = len(entries)
    print(f"\nRecommended GATE1_THRESHOLD: {best_threshold}")
    print(f"  Objective (correct_grounded + correct_refusals): {best_objective}/{n}")
    print()
    print("Paste into agent/policies.py:")
    calibration_comment = (
        f"# Calibrated {date.today()} against tests/eval/gold_set.jsonl "
        f"(n={n}), recommended value from scripts/calibrate_gate1.py "
        f"(correct_grounded+correct_refusals={best_objective}/{n})"
    )
    print(f"GATE1_THRESHOLD: float = {best_threshold}  {calibration_comment}")

    # ---------------------------------------------------------------------------
    # Step 4: Save snapshot report
    # ---------------------------------------------------------------------------
    out_dir = PROJECT_ROOT / output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{date.today()}-gate1-calibration.md"

    lines = [
        f"# Gate 1 Calibration — {date.today()}",
        "",
        f"Gold set: `{gold_set_path}` (n={n})",
        "",
        "## Sweep Results",
        "",
        "| Threshold | TP | TN | FP | FN | Precision | Recall | Objective |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sweep_results:
        marker = " **<-- recommended**" if r["threshold"] == best_threshold else ""
        lines.append(
            f"| {r['threshold']:.1f} | {r['tp']} | {r['tn']} | {r['fp']} | {r['fn']} "
            f"| {r['precision']:.3f} | {r['recall']:.3f} | {r['objective']}{marker} |"
        )
    lines += [
        "",
        f"## Recommendation",
        "",
        f"**GATE1_THRESHOLD = {best_threshold}**",
        f"Objective (correct_grounded + correct_refusals) = {best_objective}/{n}",
        "",
        "Paste into `agent/policies.py`:",
        "```python",
        f"GATE1_THRESHOLD: float = {best_threshold}  {calibration_comment}",
        "```",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nCalibration report saved to: {report_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gate 1 threshold calibration sweep")
    parser.add_argument("--gold-set", default="tests/eval/gold_set.jsonl")
    parser.add_argument("--output-dir", default="eval/reports")
    args = parser.parse_args()
    run_calibration(gold_set_path=args.gold_set, output_dir=args.output_dir)
