---
phase: 03-structured-signal-extraction-red-flag-table
plan: 02
subsystem: agent + pipelines
tags: [cite-check, numeric-grounding, unit-reconciliation, confidence-rubric, deterministic, llm-free, tdd]

# Dependency graph
requires:
  - phase: 03-structured-signal-extraction-red-flag-table
    plan: 01
    provides: NUMERIC_GROUNDING_REL_TOLERANCE policy constant, Wave 0 test stubs (test_numeric_grounding, test_confidence_rubric)
  - phase: 01-foundation-mvp-a-cited-q-a-on-one-ipo
    provides: cite_check _normalize/_extract_numbers/_numbers_subset, GroundedAnswer/Claim/RefusalResponse/RetrievedChunkRef schemas
provides:
  - "agent/nodes/cite_check.py — per-number unit-aware (lakh/crore/million/billion, ₹/%) + tolerance grounding via _extract_scaled_numbers + _scaled_numbers_grounded; exact-string subset kept as fast short-circuit"
  - "pipelines/confidence.py — deterministic classify_confidence(ga) -> (tier, score) + confidence_for_field(field) -> (None, None) for RefusalResponse"
affects: [03-03 precompute (calls confidence_for_field per field), 03-04 extraction-f1, 03-05 release-gate (numeric track uses extended grounding)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unit-aware magnitude canonicalization: number + adjacent lakh/crore/million/billion token -> single float magnitude, compared within a relative policy tolerance"
    - "Fast-path-then-reconcile: exact-string numeric subset short-circuits to grounded; unit-reconciliation only runs on the false-fail residue (zero regression to existing cite-check)"
    - "Confidence as composition of cite_check primitives (one normalization path), not a new algorithm or an LLM self-report"

key-files:
  created:
    - pipelines/confidence.py
  modified:
    - agent/nodes/cite_check.py
    - tests/unit/test_numeric_grounding.py
    - tests/unit/test_confidence_rubric.py

key-decisions:
  - "Unit reconciliation + tolerance live in a new _scaled_numbers_grounded helper called AFTER the exact-string _numbers_subset short-circuit, so existing green cite-check tests do not regress and _numbers_subset keeps its backward-compatible signature"
  - "Confidence 'verbatim' is defined on the emitted VALUE (numeric tokens must be a verbatim subset of the cited span), not the whole claim sentence — a numeric red-flag value is rarely phrased identically to the DRHP prose"
  - "tier->score is a fixed policy-anchored lookup (high=0.90/medium=0.70/low=0.50), pane-only (D3-02); chosen over a derived token_set_ratio so the same tier always reports the same defensible score"
  - "Default tier is medium (grounded upstream but neither verbatim nor cross-section), never low — low is reserved for the explicit >=2-distinct-section cross-section inference"

requirements-completed: [EVAL-03, EXTRACT-02]

# Metrics
duration: ~20min
completed: 2026-06-25
---

# Phase 3 Plan 02: Deterministic Truth-Grounding Core Summary

**Per-number unit-aware (lakh/crore/million/billion, ₹/%) + relative-tolerance grounding extending the non-LLM `cite_check` antibody (D3-10), plus a deterministic source-grounding confidence rubric (`classify_confidence`, D3-01) — both LLM-free, both sharing one normalization path, both flipping their Wave-0 stubs from skip to green.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 (both `tdd="true"`, full RED -> GREEN per task)
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- **Task 1 (D3-10):** Extended `agent/nodes/cite_check.py` with `_extract_scaled_numbers` (maps a number + adjacent unit word/symbol to a canonical float magnitude) and `_scaled_numbers_grounded` (reconciles every claim magnitude against some window magnitude within `NUMERIC_GROUNDING_REL_TOLERANCE`). The cite_check loop now grounds a numeric claim when the exact-string subset OR the unit-reconcilable tolerance match passes — so "₹11,247 crore" grounds against "11,24,700 lakh" instead of false-failing the 0.95 gate, while a genuinely-different magnitude (9,500 crore vs 4,499 crore) and an ungrounded number stay blockable.
- **Task 2 (D3-01):** Created `pipelines/confidence.py` with `classify_confidence(ga) -> (tier, score)` (verbatim value -> high; numeric reconciliation/transformation -> medium; cross-section -> low; grounded-but-otherwise -> medium default) and `confidence_for_field(field)` which returns `(None, None)` for a `RefusalResponse` (D3-03 — absence carries no tier). Reuses cite_check `_normalize`/`_extract_numbers`/`_extract_scaled_numbers` (single normalization path); no LLM and no Qdrant import.
- Both modules stay LLM-free (grep gate returns 0); both reuse the shared cite_check normalization path (`key_links` contract honored).

## Task Commits

1. **Task 1 RED** (failing unit-grounding tests) — `62be81e` (test)
2. **Task 1 GREEN** (unit-aware + tolerance grounding) — `9fbde81` (feat)
3. **Task 2 RED** (failing confidence-rubric tests) — `7b26bfc` (test)
4. **Task 2 GREEN** (deterministic confidence rubric) — `47b08a2` (feat)

## Files Created/Modified

- `agent/nodes/cite_check.py` — added `_UNIT_SCALES`, `_SCALED_NUMBER_RE`, `_extract_scaled_numbers`, `_number_reconciles`, `_scaled_numbers_grounded`; wired exact-subset-OR-reconcile into the cite_check loop; imports `NUMERIC_GROUNDING_REL_TOLERANCE` (modified, additive — `_numbers_subset` signature unchanged)
- `pipelines/confidence.py` — `classify_confidence` + `confidence_for_field` + private rubric helpers (created)
- `tests/unit/test_numeric_grounding.py` — 3 locked tests flipped skip->green (modified)
- `tests/unit/test_confidence_rubric.py` — 4 locked tests flipped skip->green (modified)

## Decisions Made

- **Reconciliation runs after the exact-string short-circuit**, not by mutating `_numbers_subset` in place — keeps `_numbers_subset` backward-compatible (its existing callers/tests are untouched) and confines the new tolerance/unit logic to a dedicated, separately-testable helper.
- **"Verbatim" (high tier) is judged on the emitted value's numeric tokens**, not the full claim sentence, because a red-flag numeric value is almost never phrased word-for-word like the DRHP prose; the digit string being present verbatim is the honest "stated outright" signal.
- **tier->score is a fixed lookup, not a `token_set_ratio` derivation** — a stable, defensible per-tier score across fields/IPOs, surfaced only in the methodology pane (D3-02).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected arithmetically-wrong lakh/crore worked example in the plan's test premise**
- **Found during:** Task 1 (RED->GREEN)
- **Issue:** The plan/research worked example pairs "₹11,247 crore" with "1,12,470 lakh" as equal magnitudes. They are not: 11,247 crore = 1.1247e11, but 1,12,470 lakh = 1.1247e10 — off by 10x. A test asserting they reconcile would have forced an incorrect (10x-loose) tolerance or a broken unit map.
- **Fix:** Authored the `test_lakh_crore_reconciles` fixture with the correct equality — 11,247 crore == 11,24,700 lakh (both 1.1247e11) — so the test validates true unit reconciliation rather than encoding the off-by-10x error. The production code (`_extract_scaled_numbers` / `_number_reconciles`) is correct as written; only the example data was wrong.
- **Files modified:** tests/unit/test_numeric_grounding.py
- **Commit:** 9fbde81

**2. [Rule 3 - Blocking] Tightened test window prose so the fuzzy gate isolates the numeric-grounding behavior under test**
- **Found during:** Task 1 (GREEN)
- **Issue:** Early test windows used divergent prose; the pre-existing `token_set_ratio >= 80` gate (which runs BEFORE the numeric check) blocked the case at the prose level, masking whether the new numeric reconciliation worked.
- **Fix:** Made the claim/window share enough non-numeric tokens that the fuzzy gate passes on prose, leaving the numeric reconciliation as the actual thing exercised — which mirrors a real DRHP window (rich shared prose, the number expressed in a different unit). No change to the fuzzy gate itself (out of this plan's scope).
- **Files modified:** tests/unit/test_numeric_grounding.py
- **Commit:** 9fbde81

**3. [Rule 1 - Bug] Reworked the `test_light_parse_is_medium` fixture to a genuinely-reconcilable transformation**
- **Found during:** Task 2 (GREEN)
- **Issue:** The first medium fixture used "44.99%" against a span containing "4,499 crore" — these do NOT reconcile in magnitude (44.99 vs 4.499e10), so the rubric correctly did not classify it medium-via-reconcile.
- **Fix:** Used a value expressed in two different units of the SAME magnitude ("4,499 crore" claim vs "44,990 million" span; both 4.499e10) — not a verbatim digit string, but magnitude-reconcilable -> medium, which is exactly the "light parse / transformation" the rubric targets.
- **Files modified:** tests/unit/test_confidence_rubric.py
- **Commit:** 47b08a2

**Total deviations:** 3 auto-fixed (2 bugs in plan-supplied example data, 1 blocking test-isolation). All confined to test fixtures; production code matches the plan's `<action>` directives. No scope creep, no architectural change.

## TDD Gate Compliance

Both tasks followed RED -> GREEN with explicit commit pairs:
- Task 1: `62be81e` (test, RED — confirmed failing on the numeric subset) -> `9fbde81` (feat, GREEN).
- Task 2: `7b26bfc` (test, RED — confirmed failing on missing module) -> `47b08a2` (feat, GREEN).
No `feat` shipped behavior without a corresponding green test. No REFACTOR commit was needed (implementations were clean on first GREEN).

## Verification

- `pytest tests/unit/test_numeric_grounding.py tests/unit/test_confidence_rubric.py tests/unit/test_cite_check.py -q` — all green.
- `pytest -q` whole suite: **281 passed, 20 skipped, 7 xfailed, 1 failed** — the single failure is the pre-existing, out-of-scope `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` (missing `sentence-transformers`), documented as ignorable in STATE.md. No regression introduced by this plan.
- LLM-free grep gates (filtered `grep -v '^#'`) return 0 on both `agent/nodes/cite_check.py` and `pipelines/confidence.py`.
- `NUMERIC_GROUNDING_REL_TOLERANCE` imported from `agent.policies`; `_normalize`/`_extract_numbers` imported from `agent.nodes.cite_check` (single normalization path).

## Known Stubs

None. Both new code paths are fully wired and exercised by green tests. Downstream consumers (the redflag precompute loop in Plan 03) will call `confidence_for_field` per field; the numeric track in Plan 05 will call the extended grounding — those are separate plans' work, not stubs left here.

## Issues Encountered

- The plan's lakh/crore worked example was arithmetically off by 10x (see Deviation 1). The `.venv/bin/python -m pytest` runner was used throughout (plain `python` not on PATH, per the environment note).

## Self-Check: PASSED

- `pipelines/confidence.py` present on disk; `agent/nodes/cite_check.py`, `tests/unit/test_numeric_grounding.py`, `tests/unit/test_confidence_rubric.py` modified.
- Commits `62be81e`, `9fbde81`, `7b26bfc`, `47b08a2` present in git history.

---
*Phase: 03-structured-signal-extraction-red-flag-table*
*Completed: 2026-06-25*
