# Red-Flag Extraction F1 — 2026-06-25

## Summary

| Metric | Value |
|---|---|
| Labeled cells (honest n) | 7 |
| Scored cells | 0 |
| Macro F1 (mean per-field score) | 0.000 |

**Interpretation (P10):** Macro F1 is the unweighted mean of the per-field scores below — numeric fields scored within their committed absolute tolerance, going-concern scored on exact equality, and the set fields scored by item-level rapidfuzz overlap. It says nothing about *which* fields fail: a high macro F1 can hide a single systematically-wrong field, so read the per-field table, not just this number. Refusals on not_disclosed cells count toward F1 and are NOT dropped (D3-03).

## Per-Field F1

| field_key | field_type | gold | prediction | score |
|---|---|---|---|---|
| ofs_vs_fresh | numeric | 59.0 | — | — |
| going_concern | boolean | False | — | — |
| auditor_history | set | ['S.R. Batliboi & Associates LLP'] | — | — |
| customer_concentration | set | not_disclosed | — | — |
| promoter_pledge_pct | numeric | not_disclosed | — | — |
| rpt_pct | numeric | not_disclosed | — | — |
| debt_trajectory | numeric | not_disclosed | — | — |

**Interpretation (P10):** A numeric field's score is binary (1.0 inside its `F1_NUMERIC_TOLERANCES` band, 0.0 outside) — it does not reward near-misses, so a field printing 'approximately' figures is scored generously by the ±tolerance, not the digits. A set field's score is the harmonic mean of item precision and recall, so a prediction that adds spurious customers is penalized as hard as one that omits real ones. A not_disclosed cell scores 1.0 ONLY when the extractor honestly refuses — a fabricated value on an absent field scores 0.0.

## Confidence-Bucket Reliability (D3-04)

| confidence_bucket | n | mean_score |
|---|---|---|

**Interpretation (P10):** This table is the confidence-reliability check — if the `high` bucket does not score meaningfully better than `low`, the confidence tier is decoration, not signal (evaluation theater). A well-calibrated extractor has monotonically decreasing mean_score from high -> low. The `not_disclosed` bucket carries fields the DRHP does not disclose; its mean_score measures honest-refusal accuracy, kept first-class and never folded into the graded buckets.

## Notes

- Gold set: `eval/gold/extraction_labels.jsonl` (swiggy-anchored; honest n per D3-05). Labeling protocol: `eval/gold/extraction_rubric.md`.
- Scorer is OFFLINE: predictions read from cached `data/redflag/<id>.json` via `load_redflag`; no live Qdrant/Gemini call.
- Per-field numeric tolerances from `agent.policies.F1_NUMERIC_TOLERANCES`; set overlap via rapidfuzz (no scikit-learn).
- Generated: 2026-06-25 by scripts/eval_extraction.py.