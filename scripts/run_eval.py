"""
scripts/run_eval.py — Phase 1 eval suite.

Loads the gold set (tests/eval/gold_set.jsonl), invokes the agent against live
Qdrant + Gemini, computes citation accuracy + answer coverage + RAGAS faithfulness
+ recall@5, and emits a markdown report to eval/reports/<YYYY-MM-DD>-phase1-baseline.md.

Phase 1 MEASURES but does NOT release-gate:
  - Citation accuracy threshold for release gate: Phase 3 EVAL-03 (>=0.95)
  - RAGAS faithfulness threshold: Phase 6 EVAL-01 (>=0.95)
Phase 1 baseline captures the starting point; these values inform Phase 3 effort.

Usage:
    python scripts/run_eval.py
    python scripts/run_eval.py --gold-set tests/eval/gold_set.jsonl
    python scripts/run_eval.py --output-dir eval/reports
"""
from __future__ import annotations

import json
import os
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Ensure project root on path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _check_env() -> None:
    """Fail fast with a clear error if required env vars are missing."""
    missing = [v for v in ("GEMINI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY") if not os.environ.get(v)]
    if missing:
        print(f"ERROR: Missing env vars: {missing}")
        print("Copy .env.example to .env, fill in values, then run: python scripts/run_eval.py")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Answer normalization (same logic as cite_check.py Pattern 3)
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    import re
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _answer_coverage(expected_substrings: list[str], answer_prose: str) -> float:
    """Proportion of expected substrings present in normalized answer prose."""
    if not expected_substrings:
        return 1.0
    norm_prose = _normalize(answer_prose)
    hits = sum(1 for sub in expected_substrings if _normalize(sub) in norm_prose)
    return hits / len(expected_substrings)


def _citation_accuracy(expected_sources: list[dict], reranked_chunks: list[dict]) -> float:
    """Proportion of expected page ranges that overlap any returned chunk."""
    if not expected_sources:
        return 1.0
    hits = 0
    for exp_src in expected_sources:
        exp_start = exp_src.get("page_start", 0)
        exp_end = exp_src.get("page_end", 9999)
        for chunk in reranked_chunks:
            payload = chunk.get("payload", {})
            chunk_start = payload.get("page_start", 0)
            chunk_end = payload.get("page_end", 0)
            if chunk_start <= exp_end and chunk_end >= exp_start:
                hits += 1
                break
    return hits / len(expected_sources)


def _recall_at_k(expected_sources: list[dict], reranked_chunks: list[dict], k: int = 5) -> float:
    """Proportion of expected source page ranges appearing in top-k chunks."""
    if not expected_sources:
        return 1.0
    top_k = reranked_chunks[:k]
    hits = 0
    for exp_src in expected_sources:
        exp_start = exp_src.get("page_start", 0)
        exp_end = exp_src.get("page_end", 9999)
        for chunk in top_k:
            payload = chunk.get("payload", {})
            chunk_start = payload.get("page_start", 0)
            chunk_end = payload.get("page_end", 0)
            if chunk_start <= exp_end and chunk_end >= exp_start:
                hits += 1
                break
    return hits / len(expected_sources)


def _ragas_faithfulness(question: str, answer_prose: str, contexts: list[str]) -> float:
    """RAGAS faithfulness metric (LLM-as-judge). Returns 0.0 on error."""
    try:
        from ragas import evaluate  # type: ignore[import]
        from ragas.metrics import faithfulness  # type: ignore[import]
        from datasets import Dataset  # type: ignore[import]

        data = Dataset.from_dict({
            "question": [question],
            "answer": [answer_prose],
            "contexts": [contexts],
        })
        result = evaluate(data, metrics=[faithfulness])
        return float(result["faithfulness"])
    except Exception as exc:
        print(f"  RAGAS faithfulness skipped ({type(exc).__name__}: {exc})")
        return -1.0  # -1 signals "not measured" vs 0.0 which means "failed"


# ---------------------------------------------------------------------------
# Main eval loop
# ---------------------------------------------------------------------------


def run_eval(
    gold_set_path: str = "tests/eval/gold_set.jsonl",
    output_dir: str = "eval/reports",
) -> Path:
    """Run the eval suite and write the markdown report."""
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

    # Lazy import — only needed at runtime
    try:
        from agent.graph import invoke_with_tracing
        from agent.schemas import GroundedAnswer, RefusalResponse
    except ImportError as exc:
        print(f"ERROR: Cannot import agent: {exc}")
        sys.exit(1)

    results: list[dict[str, Any]] = []

    for entry in entries:
        qid = entry["qid"]
        question = entry["question"]
        category = entry["category"]
        is_refusal_expected = entry["is_refusal_expected"]
        expected_substrings = entry.get("expected_answer_contains", [])
        expected_sources = entry.get("expected_sources", [])

        print(f"\n[{qid}] {question[:60]}...")

        initial_state = {"question": question}
        try:
            final_state = invoke_with_tracing(initial_state, question)
        except Exception as exc:
            print(f"  CRASHED: {exc}")
            results.append({
                "qid": qid, "category": category, "status": "crashed",
                "error": str(exc)[:200],
            })
            continue

        refusal = final_state.get("refusal")
        grounded_answer = final_state.get("grounded_answer")
        reranked = final_state.get("reranked_top_k", [])

        if is_refusal_expected:
            refusal_fired = refusal is not None
            print(f"  refusal_expected=True, refusal_fired={refusal_fired}")
            results.append({
                "qid": qid,
                "category": category,
                "refusal_expected": True,
                "refusal_fired": refusal_fired,
                "refusal_correct": refusal_fired,
                "citation_accuracy": None,
                "answer_coverage": None,
                "ragas_faithfulness": None,
                "recall_at_5": None,
            })
        else:
            if grounded_answer is None:
                print(f"  UNEXPECTED REFUSAL (grounded expected)")
                results.append({
                    "qid": qid, "category": category,
                    "refusal_expected": False, "refusal_fired": True,
                    "refusal_correct": False,
                    "citation_accuracy": 0.0, "answer_coverage": 0.0,
                    "ragas_faithfulness": 0.0, "recall_at_5": 0.0,
                })
                continue

            prose = getattr(grounded_answer, "answer_prose", "") or ""
            cite_acc = _citation_accuracy(expected_sources, reranked)
            ans_cov = _answer_coverage(expected_substrings, prose)
            recall5 = _recall_at_k(expected_sources, reranked, k=5)
            contexts = [
                chunk.get("payload", {}).get("chunk_text", "")[:500]
                for chunk in reranked[:5]
            ]
            ragas_faith = _ragas_faithfulness(question, prose, contexts)

            print(f"  citation_acc={cite_acc:.2f} answer_cov={ans_cov:.2f} recall@5={recall5:.2f} ragas={ragas_faith:.2f}")
            results.append({
                "qid": qid,
                "category": category,
                "refusal_expected": False,
                "refusal_fired": False,
                "refusal_correct": True,
                "citation_accuracy": cite_acc,
                "answer_coverage": ans_cov,
                "ragas_faithfulness": ragas_faith,
                "recall_at_5": recall5,
            })

    # ---------------------------------------------------------------------------
    # Compute summary statistics
    # ---------------------------------------------------------------------------
    grounded_results = [r for r in results if not r["refusal_expected"] and "citation_accuracy" in r and r["citation_accuracy"] is not None]
    refusal_results = [r for r in results if r["refusal_expected"]]

    avg_cite = sum(r["citation_accuracy"] for r in grounded_results) / len(grounded_results) if grounded_results else 0.0
    avg_cov = sum(r["answer_coverage"] for r in grounded_results) / len(grounded_results) if grounded_results else 0.0
    ragas_vals = [r["ragas_faithfulness"] for r in grounded_results if r["ragas_faithfulness"] >= 0]
    avg_ragas = sum(ragas_vals) / len(ragas_vals) if ragas_vals else -1.0
    avg_recall = sum(r["recall_at_5"] for r in grounded_results) / len(grounded_results) if grounded_results else 0.0
    refusal_correct = sum(1 for r in refusal_results if r["refusal_correct"])

    # ---------------------------------------------------------------------------
    # Write markdown report
    # ---------------------------------------------------------------------------
    out_dir = PROJECT_ROOT / output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{date.today()}-phase1-baseline.md"

    lines = [
        f"# Phase 1 Eval Baseline — {date.today()}",
        "",
        "## Summary",
        "",
        f"| Metric | Value | Phase 1 threshold | Gate |",
        f"|---|---|---|---|",
        f"| Citation accuracy (grounded) | {avg_cite:.3f} | measure only | Phase 3 EVAL-03 ≥0.95 |",
        f"| Answer substring coverage | {avg_cov:.3f} | measure only | — |",
        f"| RAGAS faithfulness | {avg_ragas:.3f} | measure only | Phase 6 EVAL-01 ≥0.95 |",
        f"| Recall@5 | {avg_recall:.3f} | measure only | — |",
        f"| Refusal correctly fired | {refusal_correct}/{len(refusal_results)} | — | — |",
        f"| Total entries | {len(results)} | — | — |",
        "",
        "**Note:** Phase 1 measures but does not release-gate. Thresholds are set in Phase 3 (EVAL-03) and Phase 6 (EVAL-01).",
        "",
        "## Per-Entry Results",
        "",
        "| qid | category | cite_acc | ans_cov | ragas_faith | recall@5 | refusal_ok |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        cite = f"{r['citation_accuracy']:.2f}" if r["citation_accuracy"] is not None else "—"
        cov = f"{r['answer_coverage']:.2f}" if r["answer_coverage"] is not None else "—"
        rf = f"{r['ragas_faithfulness']:.2f}" if r.get("ragas_faithfulness") is not None and r.get("ragas_faithfulness", -1) >= 0 else "—"
        rec = f"{r['recall_at_5']:.2f}" if r.get("recall_at_5") is not None else "—"
        ref_ok = "yes" if r.get("refusal_correct") else "no"
        lines.append(f"| {r['qid']} | {r['category']} | {cite} | {cov} | {rf} | {rec} | {ref_ok} |")

    lines += [
        "",
        "## Gold Set Statistics",
        "",
        "| Category | Count | Avg citation_acc | Avg ragas_faith |",
        "|---|---|---|---|",
    ]
    for cat in ["factual", "numeric", "risk-factor", "refusal-eligible"]:
        cat_results = [r for r in grounded_results if r["category"] == cat]
        n = sum(1 for r in results if r["category"] == cat)
        avg_c = sum(r["citation_accuracy"] for r in cat_results) / len(cat_results) if cat_results else 0.0
        avg_rf_vals = [r["ragas_faithfulness"] for r in cat_results if r.get("ragas_faithfulness", -1) >= 0]
        avg_rf = sum(avg_rf_vals) / len(avg_rf_vals) if avg_rf_vals else None
        rf_str = f"{avg_rf:.2f}" if avg_rf is not None else "—"
        lines.append(f"| {cat} | {n} | {avg_c:.2f} | {rf_str} |")

    lines += [
        "",
        "## Notes",
        "",
        "- Gold set: 13 entries (5 factual + 3 numeric + 3 risk-factor + 2 refusal-eligible) against Swiggy DRHP 2024.",
        "- RAGAS faithfulness requires `ragas` package installed + GEMINI_API_KEY (LLM-as-judge); value of -1 means not measured.",
        "- This report is the Phase 3 EVAL-03 and Phase 6 EVAL-01 baseline.",
        f"- Generated: {date.today()} by scripts/run_eval.py",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to: {report_path}")
    return report_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DRHPLens Phase 1 eval suite")
    parser.add_argument("--gold-set", default="tests/eval/gold_set.jsonl")
    parser.add_argument("--output-dir", default="eval/reports")
    args = parser.parse_args()
    run_eval(gold_set_path=args.gold_set, output_dir=args.output_dir)
