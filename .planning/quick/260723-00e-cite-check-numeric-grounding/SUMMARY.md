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

## Follow-up required (NOT this task's scope)

EVAL-03 cannot pass until the chunking/page-anchoring/retrieval defect is fixed
(the deferred "Option 2" — fix `extract_sections_from_docling` section
segmentation + page anchoring, re-ingest Swiggy so cite-check windows are focused
and page-precise). This cite_check fix is a necessary prerequisite now in place.

Do NOT close EVAL-03 or mark Phase 3 gate-green until the live numeric gate
reaches ≥ 0.95 on real retrieval.
