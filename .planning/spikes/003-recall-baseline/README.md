---
spike: 003
name: recall-baseline
type: standard
validates: "Given the 13-Q Swiggy gold set, when recall_at_k runs over live agent+Qdrant, then real recall@5/10/30 ratifies the recall@10 >= 0.85 hard-gate"
verdict: PARTIAL
related: [001, 002]
tags: [recall, retrieval, gate-threshold, P10]
---

# Spike 003: Recall Baseline (ratify the recall@10 gate)

## What This Validates

Run the deterministic `recall_at_k` over the Swiggy gold set against live Qdrant to get the real recall@5/10/30 — and ratify (or correct) the SPEC's `recall@10 ≥ 0.85` hard-gate threshold.

## How to Run

```bash
set -a && . ./.env && set +a
PYTHONPATH=. .venv/bin/python  # retrieve.run({"question": q}) -> retrieved_chunks (50); span-overlap recall@k
```

## Results (measured live, n=11 grounded gold Qs)

| Metric | Value | Notes |
|--------|-------|-------|
| retrieval recall@5 | **1.000** | over the 50 Qdrant candidates |
| retrieval recall@10 | **1.000** | " |
| retrieval recall@30 | **1.000** | " |
| **reranked**-recall@5 | **1.000** | over the top-5 the model actually consumes |
| candidates/question | 50 (all) | `RETRIEVE_LIMIT=50` |
| expected-span width | **10–101 pages, mean 44.5** | the smoking gun |

## Investigation Trail

1. Found `RERANK_TOP_K = 5` — the rerank node caps output at 5 chunks. **recall@10 and recall@30 are undefined on the reranked output**; they must be computed over `retrieved_chunks` (the 50 Qdrant candidates). Structural decision for `eval/metrics/recall.py`.
2. Ran retrieval-only (no `generate` node → no Gemini, no 5-RPM limit) over the 11 grounded questions: **recall@5/10/30 = 1.000** across the board, in ~5s.
3. Perfect recall is suspicious (P10). Ran the harder **reranked-recall@5** (loaded bge-reranker) → also **1.000**.
4. Measured the `expected_sources` span widths: **10 to 101 pages, mean 44.5**. The gold set's "expected source" is a whole DRHP *section* (page range), not the specific answer page. Span-overlap against a 44-page range is trivially satisfied by almost any retrieved chunk.

## Verdict: PARTIAL ⚠ — baseline measured, but the metric is saturated / low-signal

- **Measured baseline: recall@k = 1.000 at every k.** So `recall@10 ≥ 0.85` is trivially passed today.
- **⚠ The recall metric does not discriminate retrieval quality** — it is saturated at 1.0 because the gold-set `expected_sources` are coarse section-level page ranges (mean 44.5 pages, up to 101). A "recall@10 = 1.00 ✓" headline would be **evaluation theater** (P10). The `/gsd-eval-review` gate must reject presenting it as a quality win without this caveat.
- **Decisions / recommendations for the plan:**
  1. **Compute recall@10/@30 over `retrieved_chunks` (50), not `reranked_top_k` (5)** — the rerank cap makes k>5 undefined otherwise.
  2. **Keep `recall@10 ≥ 0.85` only as a conservative regression FLOOR**, explicitly labelled as such (not a quality signal), with an interpretation paragraph noting the span coarseness. Do not advertise the 1.0.
  3. **Make recall meaningful = a gold-set task:** tighten `expected_sources` to the specific answer page(s) (or a ≤2–3 page span), then re-measure and re-ratify the threshold. This is where the real recall signal comes from.
  4. **Lean on citation-accuracy + faithfulness for real retrieval-quality signal** — citation-accuracy ("the *cited* page actually contains the claim") is finer-grained than section-range recall and is the metric that should carry weight; recall stays a coarse floor.
- Ties to the Section-1b/AI-SPEC gold-set coverage-gap flag: the gold set needs finer span labels (and RPT/numeric coverage) to make the eval discriminating.
