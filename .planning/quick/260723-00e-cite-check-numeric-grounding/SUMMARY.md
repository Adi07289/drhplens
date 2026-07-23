---
quick_id: 260723-00e
slug: cite-check-numeric-grounding
requirement: EVAL-03
status: incomplete
completed: 2026-07-23
gate_passing: false
---

# Summary: Decouple numeric grounding from the prose gate in cite_check

## What was done

Fixed the confirmed root cause of the numeric-faithfulness measurement bug in
`agent/nodes/cite_check.py::cite_check`. The prose fuzzy gate
(`token_set_ratio >= 52`) was checked **before** and gated the numeric
reconciliation; concise, honest numeric answers scored 16–49 against dense
financial windows, so `_scaled_numbers_grounded` never ran and genuinely-grounded
numbers were scored ungrounded. The two antibodies are now orthogonal:

```
source grounds a claim  ⇔  numbers_grounded AND (claim_has_numbers OR prose_grounded)
```

- numeric claim, numbers reconcile → grounded (numeric reconciliation is the proof)
- numeric claim, numbers don't reconcile → fails (P2 number-swap antibody intact)
- qualitative claim (no numbers) → still requires the prose gate (prose antibody intact)

`NUMERIC_FAITHFULNESS_GATE` left at 0.95 (untouched — the gate is not the bug).

**Test-first (TDD):** added 4 tests to `tests/unit/test_cite_check.py`
(low-prose numeric grounds; crore↔million under low prose; low-prose number-swap
still fails; low-prose qualitative still fails). The bug test failed first
(`token_set_ratio=16.67 < 52`), passes now. Full unit suite: **506 passed,
1 skipped, 0 regressions**.

## Verification result — gate is STILL RED (honest)

Live throttled numeric eval (all 50 Qs, rate-limit-safe): **numeric_faithfulness
= 0.10** (5 grounded / 43 ok / 7 refused / 0 crashed). Before: 0.08.

The fix works — **`prose-gate` failures dropped to 0**. But the score barely
moved because the binding constraint is now a **separate, larger defect**:
the cited windows frequently do not contain the claim's numbers (noise
fragments like `{91, 95907, 56603}`, or empty `set()`), caused by the broken
section/page anchoring (one 273,590-token "Preamble" section → wrong chunks,
span-offset slicing, flaky retrieval). Residual failure categories:
`numeric-mismatch` 38, `refused` 7.

## Follow-up (Part 2) — page-anchored re-parse + re-ingest (DONE, 2026-07-23)

The chunking/anchoring defect was fixed in the same session (user-approved):

- Root cause deeper than "bad chunker": the committed `*.docling.json` was a known
  Phase-1 **PyMuPDF-fallback placeholder** (per `data/swiggy_drhp/INGEST_LATER.md`)
  that flattened the whole prospectus into one 273,590-token section → every chunk
  inherited page span `(0,284)`.
- Docling can't re-parse here (needs torch≥2.4 + torchvision; conflicts with the
  pinned Phase-5 numpy/shap stack). Added a torch-free **page-anchored** parser
  `pipelines.ingest.parse_drhp_pages` (PyMuPDF text + pdfplumber table rows, one
  Section per page) + `test_parse_drhp_pages.py` pinning single-page anchoring.
- Re-ingested Swiggy: 541 pages → **1,885 single-page-anchored chunks**, ONNX-embedded,
  re-upserted to Qdrant `drhp_chunks` (old chunks deleted; collection = 1,885).
  Offline-validated: figures co-located (total+fresh+OFS in one chunk).
- **Result:** numeric grounding materially improved — on the questions that ran,
  num-001/003/004/006/008 now ground (all failed pre-re-ingest). num-001's
  multi-number issue-size claim grounds via co-location.

## Still open — EVAL-03 NOT yet green

- **Full gate re-measurement blocked by Gemini free-tier rate limits** (only ~12/50
  questions completed per run before quota exhaustion; not a fix problem).
- **Residual failures** are now (a) retrieval/citation precision (number is in the
  index but the LLM cited a chunk lacking it — num-002/num-005) and (b) derived-number
  gold questions (YoY %, ratios, "3 days") that can't ground by design — a numeric
  gold-set curation question.

Do NOT close EVAL-03 or mark the Phase-3 gate green until a full live run reaches
≥ 0.95. Next: rate-limit-safe batched gate run + retrieval-precision + gold-set review.
