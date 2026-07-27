# Phase 6a — Eval Harness + Inline Metrics + Langfuse Ops (Design)

**Date:** 2026-07-28
**Status:** Approved (brainstorm). Next: `/gsd-spec-phase 6a` → `/gsd-ai-integration-phase`.
**Requirements:** EVAL-01, EVAL-02, EVAL-05.

---

## 1. Scope

Phase 6a is the first of three 6-slices. It builds **only** the eval centerpiece:

| In scope (6a) | Requirement |
|---|---|
| First-class committed RAG eval suite: faithfulness + recall@k + citation-accuracy | EVAL-01 |
| Honest inline eval numbers on IPO pages + methodology table | EVAL-02 |
| Langfuse trace enrichment + failure-mode custom scores + ops views | EVAL-05 |

**Explicitly out of scope** (deferred, do not build here):

- EVAL-04 "Show your work" pane — **already delivered** by METHOD-01 (Phase 3).
- OPS-03 committed HTML eval dashboards — **6b**.
- LAND-01 recruiter methodology landing page — **6b** (6a only fills the existing eval-table placeholders on `/methodology`).
- FAILGAL-01 failure gallery — **6b** (6a commits the Langfuse screenshots it will consume).
- Multi-tool agent orchestration + SEBI legal-review gate + public launch — **6c**.
- Authoring per-IPO gold sets for non-Swiggy IPOs — future work (not blocking 6a).

## 2. What already exists (do not rebuild)

- `scripts/run_eval.py` — already implements deterministic `_citation_accuracy`, `_recall_at_k`, optional `_ragas_faithfulness`, `_answer_coverage`; and a **release-gated** `compute_numeric_faithfulness` that `scripts/release_gate.py` imports. Currently framed as "Phase 1 baseline, measure-only," single 13-entry Swiggy gold set.
- **Langfuse plumbing** in `app/observability/`: `langfuse_client.py` (no-op fallback when keys unset), `trace_decorators.py` (`build_callbacks_for_run` + a refusal-only failure-mode taxonomy: `low_retrieval_score / unsupported_claim / banned_token / infrastructure_error`), `cite_check_metric.py`. `agent/graph.py:invoke_with_tracing` attaches callbacks. **The plumbing exists; the ops dashboard/scores do not.**
- `pages/01_methodology.py` — eval-metrics table with **placeholder rows** (e.g. `"Context recall@k · RAGAS · k=5/10/30 · reported · Phase 6"`) and already reads `model_card/card_data.json` at render.
- **DeepEval is not present** in the repo. RAGAS is referenced but not a hard dependency.

## 3. Key decisions (from brainstorm)

1. **Metric engine:** DeepEval for the faithfulness **LLM-judge** (CI-native `assert_test`, satisfies the roadmap's "DeepEval CI integration" spike flag, portfolio keyword). Recall@k and citation-accuracy **stay deterministic span-overlap** (more honest + reproducible for span-level DRHP eval than an LLM-judged `context_recall`). RAGAS kept as an **optional offline cross-check** only.
2. **Inline surface:** an **honest system-level figure** on every IPO page ("Measured across our N-question eval set…"), plus a per-IPO line **only** where a real gold set exists. Never a fabricated per-IPO number.
3. **Provenance:** eval numbers are a **committed JSON artifact** read at render (the `card_data.json` pattern) — **no live LLM-judge calls at page load** (P19 demo-safety, zero per-view cost/latency).
4. **Langfuse dashboard:** **Langfuse Cloud hosted** (traces are "reviewable by the developer"). 6a enriches traces + adds custom scores + saved views + committed screenshots. No bespoke in-app dashboard.
5. **Gate posture:** **deterministic metrics hard-gate; LLM-judge is reported-with-target.** Citation-accuracy and recall@10 block deploy; DeepEval faithfulness is surfaced with a ≥0.95 target but does not block CI (LLM-judges flake run-to-run). The existing `numeric_faithfulness ≥ 0.95` hard gate is unchanged.

## 4. Components

### 4.1 Eval suite (EVAL-01)

Extract the metrics into an importable module so **the report and the gate call one implementation** (mirrors `compute_numeric_faithfulness`):

```
eval/metrics/
  recall.py               # deterministic span-overlap recall@k; report k = 5 / 10 / 30
  citation.py             # deterministic span-overlap citation-accuracy
  faithfulness_deepeval.py# DeepEval FaithfulnessMetric (LLM-judge via Gemini); reported, not gated
  ragas_crosscheck.py     # optional, flag-gated, offline only — not in CI
```

The runner (evolved `run_eval.py`, no longer "Phase 1 baseline") emits **two artifacts per release**:

- `eval/reports/<date>-rag-eval.md` — human-readable report.
- `eval/reports/eval_summary.json` — **machine artifact the UI reads.** Stable schema (see §4.3). This is the `card_data.json` analog for RAG eval.

DeepEval CI lane: `tests/eval/test_faithfulness_deepeval.py` using `assert_test`. Opt-in (needs `GEMINI_API_KEY`), **non-blocking** — measures + records, does not fail the deterministic gate.

### 4.2 Release gate (gate posture)

`scripts/release_gate.py` gains deterministic checks importing the §4.1 module:

- **HARD GATE (block deploy):** `citation_accuracy ≥ 0.95`, `recall@10 ≥ 0.85`, `numeric_faithfulness ≥ 0.95` (existing).
- **REPORTED (no block):** DeepEval faithfulness, with a ≥0.95 target line in the report.

`recall@10 ≥ 0.85` is a **stated default ratified against the spike's measured baseline** — set just below real performance with a safety margin, never above (would self-block) nor trivially low (meaningless). The spike (§6) fixes the final number.

### 4.3 Inline surface (EVAL-02)

A small render component (Streamlit, Deep-Slate design system) reads `eval/reports/eval_summary.json` and renders on **every IPO page**:

> Measured across our 13-question eval set (Swiggy DRHP, 2026-07-28, judge=gemini-…):
> faithfulness 0.xx · recall@10 0.xx · citation 0.xx — [view report]

- IPOs **with** their own gold set additionally show a per-IPO line.
- IPOs **without** one show **no per-page number** — honesty invariant.
- Also fills the existing `pages/01_methodology.py` placeholder rows with these live numbers.

**`eval_summary.json` schema (UI contract, pinned by a test):**

```json
{
  "generated": "2026-07-28",
  "judge_model": "gemini-...",
  "corpus": { "gold_set": "tests/eval/gold_set.jsonl", "ipo": "Swiggy DRHP", "n_questions": 13 },
  "aggregate": {
    "faithfulness_deepeval": 0.00,        // reported (not gated)
    "citation_accuracy": 0.00,            // gated >= 0.95
    "recall_at_5": 0.00,
    "recall_at_10": 0.00,                 // gated >= 0.85
    "recall_at_30": 0.00
  },
  "per_ipo": { "<ipo_id>": { "n": 13, "faithfulness_deepeval": 0.00, "...": 0.00 } },
  "report": "eval/reports/2026-07-28-rag-eval.md"
}
```

**Honesty invariants on this surface (from the design system):** plain IBM-Plex-Mono figures; **no red/green, no badges, no severity icons, no verdict UX**; every figure carries provenance (n, IPO, date, judge model) + a link to the committed report; LLM-judge faithfulness always labelled as judge-based.

### 4.4 Langfuse ops (EVAL-05)

Build on the existing `app/observability/` plumbing — **no in-app dashboard**:

- Attach **cost / latency / tool-call counts** to each trace (trace-level metadata/observations).
- Promote the **failure-mode taxonomy to Langfuse custom scores** (the spike-flagged "custom-score callbacks"), extended beyond the 4 refusal reasons to also cover: `retrieval_miss / cite_check_fail / judge_flag / crash`.
- Define **saved Langfuse Cloud views** for cost/latency/tool-calls/failure-mode.
- Commit a few **screenshots** for the README + failure gallery (6b consumes them).
- Preserve the **no-op fallback**: everything must still run with Langfuse keys unset.

## 5. Testing

- **Unit (TDD):** deterministic `recall_at_k` and `citation_accuracy` as pure functions with gold-set fixtures — write tests first.
- **Schema test:** pin `eval_summary.json` shape so the §4.3 UI contract can't silently break.
- **Integration (opt-in, needs key):** DeepEval faithfulness against a small fixed context; assert the value lands in the report/JSON.
- **Langfuse:** extend `tests/integration/test_langfuse_trace.py` to assert custom-score attach + the no-op fallback path.
- **Gate:** a test that a below-threshold deterministic metric makes `release_gate.py` exit non-zero.

## 6. Spike first (~1–2 days, per roadmap research flag)

Before planning the full build, a spike validates:

1. DeepEval `assert_test` CI shape against Gemini (cost, latency, determinism spread).
2. Langfuse custom-score callback wiring on the existing callback handler.
3. **Measures the recall@10 baseline** that ratifies the §4.2 gate threshold.

## 7. Downstream hand-off

Per the Phase-6 execution plan, after this spec:

`/gsd-spec-phase 6a` → `/gsd-ai-integration-phase` (AI-SPEC: eval strategy / guardrails / Langfuse monitoring) + `/gsd-ui-phase` (inline-surface UI-SPEC) → `/gsd-spike` → `/gsd-plan-phase` → `/gsd-execute-phase` (TDD the metric code) → gates: **`/gsd-eval-review`** (the critical one — no evaluation theater, P10) + `/gsd-ui-review` + `/gsd-code-review` + `/gsd-secure-phase` + `verify` → `/gsd-ship`. Hold public launch behind 6c's SEBI gate.
