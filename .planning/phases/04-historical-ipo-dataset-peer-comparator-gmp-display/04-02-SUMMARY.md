---
phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
plan: 02
subsystem: ui
tags: [streamlit, formatting, inr, indian-grouping, lakh-crore]

requires:
  - phase: 02-multi-ipo-catalogue-drhp-snapshot-surface
    provides: the ad-hoc ₹ render sites (_format_issue_size, _format_fin_value) this consolidates
provides:
  - ui/format_inr.py — the ONE shared Indian rupee formatter (Indian grouping + auto lakh↔crore + None→"—" + parenthesised negatives)
  - app-wide adoption of format_inr at every ₹ render site
  - AST-based adoption gate preventing the Western-grouping bug from reappearing
affects: [04-05 peer table, 04-06 GMP block, any future ₹ render]

tech-stack:
  added: []
  patterns: [single-source formatting utility, AST-based adoption gate]

key-files:
  created: [ui/format_inr.py, tests/unit/test_format_inr.py, tests/unit/test_format_inr_adoption.py]
  modified: [ui/catalogue.py, ui/snapshot_blocks.py]

key-decisions:
  - "format_inr takes RUPEES; crore-unit callers convert (* 1e7) before calling — no double-scaling"
  - "Adoption gate is AST-based (JoinedStr + format_spec) so docstrings documenting the old bug don't self-invalidate it"

patterns-established:
  - "ONE shared format_inr utility (D4-07): grouping is re-implemented nowhere; every ₹ site delegates"
  - "AST adoption gate: fail on any ui/*.py f-string rendering ₹ with a ',' group-spec"

requirements-completed: [UI-04]

duration: 20min
completed: 2026-07-06
---

# Phase 4 · Plan 02: Shared Indian rupee formatter Summary

**Every ₹ amount in the app now renders through one `format_inr` utility with correct Indian digit grouping (12,34,567) and auto-scaled lakh↔crore — closing the latent FLAG-FORMAT Western-grouping bug at its two live sites and pinning it shut with an AST adoption gate.**

## What shipped

- **`ui/format_inr.py`** — `format_inr(amount) -> str`: Indian grouping (last 3 digits, then groups of 2), auto lakh (≥₹1,00,000) / crore (≥₹1,00,00,000) scaling, `None → "—"`, negatives in parentheses (inherited no-red convention). Returns a string only; `tabular-nums` stays a CSS concern.
- **Adoption refactor** — `ui/catalogue.py::_format_issue_size` and `ui/snapshot_blocks.py::_format_fin_value` now delegate to `format_inr` (crore inputs converted `* 1e7`), replacing the two bare Western `f"₹{n:,}"` renders. The catalogue None-copy ("Issue size not disclosed") and the financials `—` + aria-label / no-red-negative behaviour are preserved.
- **Tests** — `test_format_inr.py` (grouping + lakh/crore + negatives + None); `test_format_inr_adoption.py` (AST gate: no ui/*.py f-string renders ₹ with a `,` group-spec, and both call sites reference `format_inr`).

## Verification

- Plan verify (`test_format_inr.py` + `test_format_inr_adoption.py` + `test_catalogue.py`): **27 passed**.
- Whole suite: **328 passed, 7 skipped, 7 xfailed** (the pre-existing bge-m3 live-model embedder test deselected as agreed). No regressions.
- FLAG-FORMAT confirmed fixed: a ₹11,327 cr issue renders `₹11,327 crore`, never `₹1.13 lakh crore` (no double-scaling) and never Western `₹11,327 cr`.

## Notes

- Commits: `3c796ad` (RED tests), `aed6661` (utility), `8a4c648` (adoption + gate).
- Recovery: the executing subagent hit the session limit after committing Task 1 and the two refactors (uncommitted); Task 2's adoption test + closeout were completed inline on `main`.

## Self-Check

- [x] `ui/format_inr.py` exists with `def format_inr`.
- [x] Both `_format_issue_size` and `_format_fin_value` reference `format_inr`.
- [x] Adoption gate green; whole suite green (minus the ignored embedder test).
- [x] UI-04 (formatting portion) delivered; no red/green introduced.
