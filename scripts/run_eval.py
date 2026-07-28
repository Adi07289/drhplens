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

# ---------------------------------------------------------------------------
# The ONE metric implementation (06.1-01/02) — imported here, never re-implemented,
# so the committed eval_summary.json and scripts/release_gate.py can never diverge
# (mirrors how release_gate imports compute_numeric_faithfulness below). These live
# AFTER the sys.path insert above so `python scripts/run_eval.py` (sys.path[0]=scripts/)
# still resolves the project packages.
# ---------------------------------------------------------------------------
from agent.policies import DRHP_ID_DEFAULT  # noqa: E402
from app.observability.langfuse_client import get_client, is_enabled  # noqa: E402
from app.observability.trace_enrichment import FAILURE_MODES, flush  # noqa: E402
from eval.metrics import (  # noqa: E402
    Aggregate,
    Corpus,
    EvalSummary,
    citation_accuracy,
    faithfulness_deepeval,
    recall_at_k,
)
from eval.metrics.faithfulness_deepeval import NOT_MEASURED  # noqa: E402


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
            # ONE shared impl (eval.metrics) — the private copies were deleted (06.1-04).
            cite_acc = citation_accuracy(expected_sources, reranked)
            ans_cov = _answer_coverage(expected_substrings, prose)
            recall5 = recall_at_k(expected_sources, reranked, 5)
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


# ===========================================================================
# RAG eval runner (06.1-04, EVAL-01) — the first-class committed runner.
#
# One pass over the gold set emits BOTH the pinned machine artifact
# eval/reports/eval_summary.json (read by the inline UI surface + release gate)
# and the human eval/reports/<date>-rag-eval.md (judge reasons + P10 interpretation).
# It imports the ONE eval/metrics implementation, so the report and the gate can
# never diverge (mirrors compute_numeric_faithfulness below).
#
# Two paths, one final_state shape:
#   - default (with_faithfulness=False): recall + citation via retrieve+rerank only
#     (NO Gemini generate — spike 003); faithfulness serialized as the -1 "not
#     measured" sentinel. $0, never touches the free-tier daily quota. P10 honesty:
#     a real judge number is withheld until the >=0.7 human calibration passes.
#   - --with-faithfulness: invokes the full agent (invoke_with_tracing) and scores the
#     DeepEval Gemini judge SERIALLY (5-RPM safe) over the top-5 reranked context (P18).
# ===========================================================================


def _retrieval_state(question: str, drhp_id: str) -> dict:
    """Run retrieve + rerank ONLY (no Gemini generate) -> a final_state-shaped dict.

    The deterministic metrics need only the retrieval candidates (recall over the 50
    retrieved_chunks) and the reranked window (citation) — the generate node (Gemini)
    is not required, so this pass costs $0 and never consumes the free-tier daily quota
    (spike 003 validated this exact path). Returns {retrieved_chunks, reranked_top_k, ...}.
    """
    from agent.nodes import rerank, retrieve

    state: dict = {"question": question, "drhp_id": drhp_id}
    state = retrieve.run(state)
    state = rerank.run(state)
    return state


def _retrieval_only_invoke(initial_state: dict, question: str) -> dict:
    """Deterministic invoke_fn matching the invoke_with_tracing(initial_state, question)
    signature, so run_rag_eval treats the retrieval-only and full-agent paths uniformly."""
    return _retrieval_state(
        initial_state.get("question", question),
        initial_state.get("drhp_id", DRHP_ID_DEFAULT),
    )


def _attach_judge_flag(question: str, faithfulness: float, threshold: float = 0.95) -> None:
    """Attach the eval-time `judge_flag` failure mode to Langfuse when a MEASURED
    faithfulness falls below threshold (Wave 2 taxonomy — app/observability).

    judge_flag is the one FAILURE_MODES entry only emittable at EVAL time: the judge runs
    here in the runner, not in the agent, so trace_enrichment.classify_failure_mode never
    returns it. It is wired here via the same direct-client score path. Inert on the default
    run — faithfulness is the -1 "not measured" sentinel, so the < threshold branch fires
    only under --with-faithfulness with a real judge score. No-op when Langfuse keys are
    unset (is_enabled gate); every call is swallowed so tracing can never break the runner.
    """
    if faithfulness < 0 or faithfulness >= threshold:
        return  # not measured, or at/above the target line — nothing to flag
    if not is_enabled():
        return
    try:
        lf = get_client()
        if lf is None:
            return
        trace = lf.trace(
            name="answer_question",
            metadata={"question_preview": question[:80], "faithfulness": faithfulness},
            tags=["eval-05", "eval-judge"],
        )
        trace.score(
            name="failure_mode",
            value=float(FAILURE_MODES.index("judge_flag") + 1),
            comment="judge_flag",
        )
    except Exception:
        # Tracing must never crash the runner (mirror emit_enriched_trace).
        pass


def run_rag_eval(
    gold_set_path: str = "tests/eval/gold_set.jsonl",
    output_dir: str = "eval/reports",
    with_faithfulness: bool = False,
    invoke_fn=None,
    drhp_id: str = DRHP_ID_DEFAULT,
) -> Path:
    """First-class RAG eval runner: emit eval_summary.json + <date>-rag-eval.md in one pass.

    Args:
        gold_set_path: JSONL gold set (default the 13-Q Swiggy set).
        output_dir: where both artifacts are written.
        with_faithfulness: opt-in DeepEval judge pass (default OFF). When OFF the committed
            faithfulness is the -1 "not measured" sentinel (P10 honesty guard + free-tier
            daily-quota reality); the deterministic recall/citation are always REAL.
        invoke_fn: dependency-injection hook for offline tests. Signature
            ``invoke_fn(initial_state, question) -> final_state``. When None the live path is
            built and _check_env fail-fast runs; when provided, no live services are touched.
        drhp_id: the IPO whose gold set this is (Swiggy) — the sole per_ipo key.

    Returns:
        Path to the written eval_summary.json.
    """
    live = invoke_fn is None
    if live:
        _check_env()
        if with_faithfulness:
            from agent.graph import invoke_with_tracing

            invoke_fn = invoke_with_tracing
        else:
            invoke_fn = _retrieval_only_invoke

    gold_path = PROJECT_ROOT / gold_set_path
    if not gold_path.exists():
        print(f"ERROR: gold set not found at {gold_path}")
        sys.exit(1)

    entries = [
        json.loads(line)
        for line in gold_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    grounded = [e for e in entries if not e.get("is_refusal_expected", False)]
    print(
        f"Loaded {len(entries)} gold entries ({len(grounded)} grounded) from {gold_path}"
    )

    per_q: list[dict[str, Any]] = []
    for entry in grounded:
        qid = entry["qid"]
        question = entry["question"]
        category = entry.get("category", "")
        expected_sources = entry.get("expected_sources", [])

        print(f"\n[{qid}] {question[:60]}...")
        final_state = invoke_fn({"question": question, "drhp_id": drhp_id}, question)

        retrieved = final_state.get("retrieved_chunks", []) or []
        reranked = final_state.get("reranked_top_k", []) or []

        # recall over the 50 retrieved candidates (NOT reranked — RERANK_TOP_K=5 makes
        # k=10/30 undefined on the reranked list, measured decision #2 / spike 003);
        # citation over the reranked window the agent actually consumed.
        r5 = recall_at_k(expected_sources, retrieved, 5)
        r10 = recall_at_k(expected_sources, retrieved, 10)
        r30 = recall_at_k(expected_sources, retrieved, 30)
        cite = citation_accuracy(expected_sources, reranked)

        faith: float = NOT_MEASURED
        reason = (
            "<reason: not measured — deterministic-only run; enable the judge with "
            "--with-faithfulness (needs GEMINI_API_KEY + free-tier daily quota)>"
        )
        if with_faithfulness:
            grounded_answer = final_state.get("grounded_answer")
            prose = (getattr(grounded_answer, "answer_prose", "") or "") if grounded_answer else ""
            # P18: judge only the top-5 reranked chunk text the generate node consumed,
            # byte-identical (truncated to ~500 chars as in the legacy track). Serial call.
            contexts = [
                c.get("payload", {}).get("chunk_text", "")[:500] for c in reranked[:5]
            ]
            faith, reason = faithfulness_deepeval(question, prose, contexts)
            _attach_judge_flag(question, faith)

        faith_str = "—" if faith < 0 else f"{faith:.2f}"
        print(
            f"  recall@5/10/30={r5:.2f}/{r10:.2f}/{r30:.2f} "
            f"citation={cite:.2f} faithfulness={faith_str}"
        )
        per_q.append({
            "qid": qid,
            "category": category,
            "recall_at_5": r5,
            "recall_at_10": r10,
            "recall_at_30": r30,
            "citation_accuracy": cite,
            "faithfulness": faith,
            "reason": reason,
            "n_retrieved": len(retrieved),
            "n_reranked": len(reranked),
        })

    if not per_q:
        # A deterministic metric could not be computed (no grounded questions) — fail.
        print("ERROR: no grounded gold entries to score")
        sys.exit(1)

    def _mean(key: str) -> float:
        return sum(r[key] for r in per_q) / len(per_q)

    # faithfulness aggregate: mean of the MEASURED (>= 0) values only; -1 if none measured.
    faith_measured = [r["faithfulness"] for r in per_q if r["faithfulness"] >= 0]
    agg_faith = (
        sum(faith_measured) / len(faith_measured) if faith_measured else NOT_MEASURED
    )

    aggregate = Aggregate(
        faithfulness_deepeval=agg_faith,
        citation_accuracy=_mean("citation_accuracy"),
        recall_at_5=_mean("recall_at_5"),
        recall_at_10=_mean("recall_at_10"),
        recall_at_30=_mean("recall_at_30"),
    )
    corpus = Corpus(gold_set=gold_set_path, ipo="Swiggy DRHP", n_questions=len(entries))
    report_rel = f"eval/reports/{date.today()}-rag-eval.md"
    summary = EvalSummary(
        generated=date.today().isoformat(),
        judge_model="gemini-3.5-flash",  # spike 002: 2.5-flash 404s; 3.5-flash is the codebase judge
        corpus=corpus,
        aggregate=aggregate,
        # per_ipo carries ONLY Swiggy — the one IPO with a real gold set (honesty invariant;
        # never fabricate a per-IPO figure for an IPO without one).
        per_ipo={drhp_id: aggregate},
        report=report_rel,
    )

    out_dir = PROJECT_ROOT / output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # model_dump_json validates against the pinned EvalSummary schema at write time —
    # a schema violation raises here and fails the runner, which is correct.
    json_path = out_dir / "eval_summary.json"
    json_path.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"\neval_summary.json written to: {json_path}")

    report_path = _write_rag_eval_report(
        per_q, summary, len(entries), len(grounded), out_dir
    )
    print(f"rag-eval report written to: {report_path}")

    # ship the enriched Langfuse traces (06.1-03) before this short-lived process exits.
    flush()

    return json_path


def _write_rag_eval_report(
    per_q: list[dict[str, Any]],
    summary: EvalSummary,
    n_total: int,
    n_grounded: int,
    out_dir: Path,
) -> Path:
    """Write the dated <date>-rag-eval.md: provenance header, summary table, a per-question
    table carrying the judge `reason` strings, and the mandatory per-metric Interpretation
    (P10) section — including the recall-saturation floor caveat + the gold-set follow-up."""
    agg = summary.aggregate
    report_path = out_dir / f"{date.today()}-rag-eval.md"

    faith_val = (
        "not measured (-1)"
        if agg.faithfulness_deepeval < 0
        else f"{agg.faithfulness_deepeval:.3f}"
    )

    lines = [
        f"# RAG Eval — {date.today()}",
        "",
        f"> Measured over the {summary.corpus.n_questions}-question gold set "
        f"({summary.corpus.ipo}; {n_grounded} grounded questions scored, "
        f"{n_total - n_grounded} refusal-eligible excluded), generated "
        f"{summary.generated}, judge = `{summary.judge_model}`. "
        f"Machine artifact: `eval/reports/eval_summary.json`.",
        "",
        "## Summary",
        "",
        "| Metric | Value | Gate posture |",
        "|---|---|---|",
        f"| faithfulness_deepeval | {faith_val} | REPORTED (target >= 0.95, never gated) |",
        f"| citation_accuracy | {agg.citation_accuracy:.3f} | HARD GATE >= 0.95 |",
        f"| recall@5 | {agg.recall_at_5:.3f} | reported |",
        f"| recall@10 | {agg.recall_at_10:.3f} | HARD GATE >= 0.85 (regression floor) |",
        f"| recall@30 | {agg.recall_at_30:.3f} | reported |",
        "",
        "## Per-Question Results",
        "",
        "| qid | category | recall@5 | recall@10 | recall@30 | citation | faithfulness | judge reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in per_q:
        f_str = "—" if r["faithfulness"] < 0 else f"{r['faithfulness']:.2f}"
        reason = (r.get("reason") or "").replace("|", "\\|").replace("\n", " ")
        if len(reason) > 200:
            reason = reason[:197] + "..."
        lines.append(
            f"| {r['qid']} | {r['category']} | {r['recall_at_5']:.2f} | "
            f"{r['recall_at_10']:.2f} | {r['recall_at_30']:.2f} | "
            f"{r['citation_accuracy']:.2f} | {f_str} | {reason} |"
        )

    lines += [
        "",
        "## Interpretation (P10)",
        "",
        "Every headline figure below carries an honest interpretation — no metric is "
        "surfaced as a verdict, and a low score renders identically to a high one.",
        "",
        f"**Faithfulness (DeepEval LLM-judge, `{summary.judge_model}`) — REPORTED, not gated.** "
        "This is an LLM-as-judge score: the fraction of the answer's claims the judge finds "
        "supported by the top-5 reranked DRHP chunks the agent actually retrieved (P18). It is "
        "non-deterministic (it drifts run-to-run even at temperature 0), so it is REPORTED "
        "against a 0.95 target line and NEVER hard-gates a release — hard-gating a run-to-run "
        "variable judge is itself a critical failure mode. A value of -1 means NOT MEASURED "
        "(free-tier Gemini daily quota exhausted / key unset), never a real 0.0. The judge "
        "figure must NOT be trusted or surfaced as a headline until a >= 50-example human "
        "spot-check reaches >= 0.7 judge-vs-human correlation (AI-SPEC §5); this run withholds "
        "it (-1) pending that calibration.",
        "",
        "**Citation accuracy — deterministic, HARD-GATED >= 0.95.** Pure page-range span "
        "overlap: did the cited page actually contain the claim (CLAUDE.md's custom metric). It "
        "is model-free and reproducible, computed over the reranked chunks the agent consumed. "
        "This is the finer-grained REAL retrieval-quality signal (spike 003) and — with "
        "numeric_faithfulness — carries the release gate: a citation-accuracy regression is a "
        "hard CI failure.",
        "",
        "**Recall@k — deterministic; a LABELLED REGRESSION FLOOR, NOT a headline quality "
        "metric (P10).** recall@10 is gated at >= 0.85 ONLY as a conservative regression floor. "
        "Recall reads high (1.00 at every k on the current gold set) because the gold "
        "`expected_sources` are coarse 10-101-page section ranges (mean 44.5 pages — spike "
        "003), which span-overlap satisfies trivially; a \"recall@10 = 1.00\" headline would be "
        "evaluation theater. Recall is computed over the 50 `retrieved_chunks` (the Qdrant "
        "candidates), NOT the 5 reranked chunks, because RERANK_TOP_K=5 makes k=10/30 undefined "
        "on the reranked list. The real retrieval-quality signal lives in citation-accuracy + "
        "faithfulness, not here.",
        "",
        "**Gold-set follow-up (flagged, NOT executed in 6.1 — measured decision #7).** To make "
        "recall discriminating, tighten the gold `expected_sources` to <= 2-3-page answer spans "
        "and add labelled RPT-attribution + numeric unit/period coverage, then re-measure and "
        "re-ratify the recall@10 threshold (AI-SPEC §5). Until then recall stays a coarse floor "
        "and per-IPO figures are suppressed wherever a real gold set is absent.",
        "",
        "## Notes",
        "",
        f"- Gold set: `{summary.corpus.gold_set}` ({summary.corpus.ipo}); "
        f"{n_grounded}/{n_total} grounded questions scored for the deterministic metrics.",
        "- One metric implementation: the runner imports `recall_at_k` / `citation_accuracy` / "
        "`faithfulness_deepeval` from `eval.metrics` — the same functions `scripts/release_gate.py` "
        "imports, so the report and the gate can never diverge.",
        f"- Machine artifact (UI + gate contract): `eval/reports/eval_summary.json` "
        f"(schema-validated `EvalSummary`, judge = `{summary.judge_model}`).",
        f"- Generated: {date.today()} by scripts/run_eval.py (run_rag_eval).",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ===========================================================================
# Numeric-faithfulness track (D3-11 / D3-13) — ADDITIVE; the Phase 1 track above
# is unchanged. numeric_faithfulness = fraction of eval Qs whose EVERY emitted
# number grounds to a cited DRHP span via the Plan 02 extended cite_check
# per-number grounding. release_gate.py imports compute_numeric_faithfulness so
# the gate runs the SAME computation — no duplication.
# ===========================================================================


def _question_numbers_grounded(grounded_answer: Any, reranked: list[dict]) -> bool:
    """True iff every number the agent emitted grounds via cite_check (D3-10/D3-13).

    Reuses the Plan 02 extended per-number grounding in agent.nodes.cite_check
    (lakh/crore/million reconciliation + relative tolerance) rather than
    re-implementing a numeric subset check here — one normalization path across
    cite-check + eval (RESEARCH §Don't Hand-Roll). A grounded_answer whose every
    claim is grounded by the cite_check node has every emitted number grounded;
    we re-run cite_check against the reranked window so the eval is independent of
    runtime state and exercises the SAME deterministic antibody the gate enforces.
    """
    from agent.nodes.cite_check import cite_check

    if grounded_answer is None:
        return False

    retrieved_chunks: dict[str, str] = {}
    for chunk in reranked:
        payload = chunk.get("payload", {})
        chunk_id = payload.get("chunk_id", chunk.get("id", ""))
        chunk_text = payload.get("chunk_text", "")
        if chunk_id:
            retrieved_chunks[chunk_id] = chunk_text

    all_grounded, _failures = cite_check(grounded_answer, retrieved_chunks)
    return all_grounded


def compute_numeric_faithfulness(
    numeric_set_path: str = "eval/gold/numeric_eval.jsonl",
    output_dir: str = "eval/reports",
    write_report: bool = True,
) -> float:
    """Run the numeric-only eval set against live services and return the score.

    numeric_faithfulness = (# eval Qs whose every emitted number grounds) /
    (# eval Qs). Writes a dated markdown numeric-track section to output_dir when
    write_report=True. This is the importable computation release_gate.py calls
    (D3-12) so the gate enforces the SAME number the report shows.

    Returns the aggregate numeric_faithfulness in [0.0, 1.0]; raises SystemExit
    (via _check_env / missing file) if the live environment is not ready.
    """
    _check_env()

    numeric_path = PROJECT_ROOT / numeric_set_path
    if not numeric_path.exists():
        print(f"ERROR: numeric eval set not found at {numeric_path}")
        sys.exit(1)

    entries = [
        json.loads(line)
        for line in numeric_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    print(f"Loaded {len(entries)} numeric eval entries from {numeric_path}")

    try:
        from agent.graph import invoke_with_tracing
    except ImportError as exc:
        print(f"ERROR: Cannot import agent: {exc}")
        sys.exit(1)

    per_q: list[dict[str, Any]] = []
    for entry in entries:
        qid = entry["qid"]
        question = entry["question"]
        print(f"\n[{qid}] {question[:60]}...")

        try:
            final_state = invoke_with_tracing({"question": question}, question)
        except Exception as exc:
            print(f"  CRASHED: {exc}")
            # A crash means no grounded numbers were emitted faithfully → fail.
            per_q.append({"qid": qid, "grounded": False, "status": "crashed"})
            continue

        grounded_answer = final_state.get("grounded_answer")
        reranked = final_state.get("reranked_top_k", [])
        grounded = _question_numbers_grounded(grounded_answer, reranked)
        print(f"  numbers_grounded={grounded}")
        per_q.append({"qid": qid, "grounded": grounded, "status": "ok"})

    n = len(per_q)
    n_grounded = sum(1 for r in per_q if r["grounded"])
    numeric_faithfulness = (n_grounded / n) if n else 0.0
    print(
        f"\nnumeric_faithfulness = {n_grounded}/{n} = {numeric_faithfulness:.3f}"
    )

    if write_report:
        _write_numeric_report(per_q, numeric_faithfulness, output_dir)

    return numeric_faithfulness


def _write_numeric_report(
    per_q: list[dict[str, Any]],
    numeric_faithfulness: float,
    output_dir: str,
) -> Path:
    """Write the dated numeric-track markdown section (mirrors the Phase 1 writer)."""
    from agent.policies import NUMERIC_FAITHFULNESS_GATE

    out_dir = PROJECT_ROOT / output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{date.today()}-numeric-faithfulness.md"

    n = len(per_q)
    n_grounded = sum(1 for r in per_q if r["grounded"])
    passes = numeric_faithfulness >= NUMERIC_FAITHFULNESS_GATE

    lines = [
        f"# Numeric-Faithfulness Track — {date.today()}",
        "",
        "## Summary",
        "",
        "| Metric | Value | Gate | Status |",
        "|---|---|---|---|",
        f"| numeric_faithfulness | {numeric_faithfulness:.3f} | "
        f">= {NUMERIC_FAITHFULNESS_GATE} (EVAL-03 / D3-12) | "
        f"{'PASS' if passes else 'FAIL'} |",
        f"| Questions grounded | {n_grounded}/{n} | — | — |",
        "",
        "**Interpretation (P10):** numeric_faithfulness is the fraction of "
        "numeric-only eval questions whose *every* emitted number grounds to a "
        "cited DRHP span via the deterministic, non-LLM cite_check per-number "
        "antibody (lakh/crore/million reconciliation + relative tolerance, D3-10). "
        "A single hallucinated or mis-reconciled number fails that question. The "
        f">= {NUMERIC_FAITHFULNESS_GATE} release gate (scripts/release_gate.py) "
        "physically refuses deploy below this threshold — enforcement, not a "
        "printed warning.",
        "",
        "## Per-Question Results",
        "",
        "| qid | numbers_grounded | status |",
        "|---|---|---|",
    ]
    for r in per_q:
        lines.append(
            f"| {r['qid']} | {'yes' if r['grounded'] else 'no'} | {r['status']} |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- Numeric eval set: `eval/gold/numeric_eval.jsonl` (Swiggy-anchored; "
        "right-sized to the ingested DRHP set per D3-05).",
        "- Grounding reuses `agent.nodes.cite_check.cite_check` — the same "
        "deterministic antibody the agent uses at emit time (no LLM judge).",
        f"- Generated: {date.today()} by scripts/run_eval.py "
        "(compute_numeric_faithfulness).",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Numeric-track report written to: {report_path}")
    return report_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DRHPLens RAG eval suite")
    parser.add_argument("--gold-set", default="tests/eval/gold_set.jsonl")
    parser.add_argument("--output-dir", default="eval/reports")
    parser.add_argument(
        "--with-faithfulness",
        action="store_true",
        help="Opt-in: run the DeepEval Gemini judge (serial, 5-RPM safe) over the full "
        "agent. Default OFF -> faithfulness is serialized as the -1 'not measured' "
        "sentinel (P10 honesty guard + free-tier daily-quota reality), and the "
        "deterministic recall/citation are computed via retrieve+rerank only (no Gemini).",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Run the legacy Phase 1 baseline (run_eval) instead of the RAG eval runner.",
    )
    parser.add_argument(
        "--numeric",
        action="store_true",
        help="Run the numeric-faithfulness track (D3-11/D3-13) instead of the RAG eval runner.",
    )
    parser.add_argument(
        "--numeric-set", default="eval/gold/numeric_eval.jsonl"
    )
    args = parser.parse_args()
    if args.numeric:
        compute_numeric_faithfulness(
            numeric_set_path=args.numeric_set, output_dir=args.output_dir
        )
    elif args.legacy:
        run_eval(gold_set_path=args.gold_set, output_dir=args.output_dir)
    else:
        run_rag_eval(
            gold_set_path=args.gold_set,
            output_dir=args.output_dir,
            with_faithfulness=args.with_faithfulness,
        )
