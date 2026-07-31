---
quick_id: 260723-00e
slug: cite-check-numeric-grounding
created: 2026-07-23
requirement: EVAL-03
status: in-progress
---

# Quick Task: Decouple numeric grounding from the prose gate in cite_check

## Problem (Job 2 — numeric-faithfulness gate failing)

The EVAL-03 release gate (`scripts/release_gate.py`) measured
`numeric_faithfulness ≈ 0.08` vs the `0.95` gate — deploy BLOCKED. Confirmed by
live end-to-end reproduction of the numeric eval set:

- The agent answers **honestly**. The DRHP states figures in **millions**, so it
  emits e.g. `₹112,473.90 million` (= 11,247.39 crore) — correct, and
  reconcilable to the gold via the existing million/crore unit logic.
- **The measurement is broken.** `agent/nodes/cite_check.cite_check()` checks the
  prose fuzzy gate `token_set_ratio >= CITE_CHECK_TOKEN_RATIO (52)` **before** the
  numeric reconciliation and `continue`s past the source when it fails. A concise
  numeric sentence vs a dense ~431-token financial window scores only **31–49**,
  so `_scaled_numbers_grounded` never runs and genuinely-grounded numbers are
  scored ungrounded.

Root cause: two orthogonal antibodies (numeric reconciliation vs prose overlap)
were wired as a hard AND, with prose gating numeric. Concise numeric answers
can't clear the prose gate against large windows.

Out of scope (separate follow-up): the broken section/page anchoring that
produces giant `(0,284)`-style chunks. Not touched here.

## Fix (targeted, test-first)

In `cite_check()`, evaluate both antibodies independently and ground a source when:

```
numbers_grounded AND (claim_has_numbers OR prose_grounded)
```

where `numbers_grounded = _numbers_subset OR _scaled_numbers_grounded` (trivially
True when the claim carries no numbers). This means:

- Numeric claim, numbers reconcile → grounded (numeric reconciliation IS the proof;
  the prose gate no longer false-rejects it). **← the fix**
- Numeric claim, numbers do NOT reconcile → fails (P2 number-swap antibody intact).
- Qualitative claim (no numbers) → still requires the prose gate (prose antibody intact).

`NUMERIC_FAITHFULNESS_GATE` stays `0.95` — untouched.

## Tasks

1. **[test]** Add failing tests to `tests/unit/test_cite_check.py`:
   pin (a) a numeric claim with low prose overlap + reconciling number now grounds,
   (b) low-prose number-swap still fails, (c) low-prose qualitative claim still fails.
2. **[fix]** Decouple the two antibodies in `agent/nodes/cite_check.py::cite_check`.
3. **[verify]** `pytest tests/unit/test_cite_check.py tests/unit/test_numeric_grounding.py`
   green; full unit suite no-regression; then re-run the live numeric gate and record
   the new score.

## Verification

- Unit: new tests green, existing cite-check + numeric-grounding tests green, no suite regression.
- Live: `.venv/bin/python scripts/run_eval.py --numeric` numeric_faithfulness materially up from 0.08 (iterate on residual per-question misses).
