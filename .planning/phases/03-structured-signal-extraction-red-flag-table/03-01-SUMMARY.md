---
phase: 03-structured-signal-extraction-red-flag-table
plan: 01
subsystem: testing
tags: [pydantic, redflag-schema, policies, pytest, nyquist-scaffold, idf, confidence-rubric]

# Dependency graph
requires:
  - phase: 02-multi-ipo-catalogue-drhp-snapshot-surface
    provides: SnapshotRecord cache pattern, snapshot_queries dict shape, GroundedAnswer/RefusalResponse contract
  - phase: 01-foundation-mvp-a-cited-q-a-on-one-ipo
    provides: locked GroundedAnswer/Claim/RefusalResponse schemas, claim_id regex, agent/policies.py single-source-of-truth, cite_check primitives
provides:
  - "agent/redflag_schema.py — RedFlagField/RankedRisk/RedFlagRecord with {\"refusal\": ...} discriminator codec and a 7-key allow-list validator"
  - "pipelines/redflag_queries.py — REDFLAG_QUERIES (7 canonical keys, UI-SPEC order) synced to REDFLAG_FIELD_KEYS"
  - "agent/policies.py Phase 3 section — NUMERIC_GROUNDING_REL_TOLERANCE, IDF_BAND_THRESHOLDS, F1_NUMERIC_TOLERANCES, IDF_BOILERPLATE_FUZZ_THRESHOLD, NUMERIC_FAITHFULNESS_GATE=0.95"
  - "8 Wave 0 test files (23 LOCKED function names) + tests/eval/conftest.py with 3 shared fixtures"
affects: [03-02 confidence+numeric-grounding, 03-03 precompute+risk-idf, 03-04 extraction-f1, 03-05 release-gate, 03-06 methodology-pane]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Interface-first ordering: schema + query keys + policy constants fixed in Wave 0 so downstream waves build against a frozen contract"
    - "Nyquist Wave 0 scaffold: locked test function names that skip with named implementing-plan reasons, flip to real assertions per wave"
    - "Union-discriminator cache codec reused verbatim (no new JSON codec)"

key-files:
  created:
    - agent/redflag_schema.py
    - pipelines/redflag_queries.py
    - tests/eval/conftest.py
    - tests/unit/test_redflag_schema.py
    - tests/unit/test_redflag_precompute.py
    - tests/unit/test_confidence_rubric.py
    - tests/unit/test_numeric_grounding.py
    - tests/unit/test_risk_idf.py
    - tests/unit/test_methodology_pane.py
    - tests/eval/test_extraction_f1.py
    - tests/eval/test_release_gate.py
    - tests/eval/test_phase3_fixtures.py
  modified:
    - agent/policies.py

key-decisions:
  - "RedFlagRecord mirrors SnapshotRecord verbatim in shape; the {\"refusal\": ...} discriminator codec is copied, not reinvented"
  - "confidence_tier/confidence_score are None for not-disclosed (RefusalResponse) fields (D3-03)"
  - "NUMERIC_FAITHFULNESS_GATE locked at 0.95 (cross-phase invariant); other Phase 3 constants are placeholders to calibrate empirically per extraction_rubric.md"
  - "Schema interface test made self-contained (local record builder) instead of depending on the eval-scoped fixture, because conftest fixtures are not visible across the tests/unit ↔ tests/eval directory boundary"

patterns-established:
  - "Pattern: Phase 3 tunables live only in agent/policies.py with GATE1_THRESHOLD-style calibration comments"
  - "Pattern: shared eval fixtures (synthetic_redflag_record, tiny_extraction_labels, idf_corpus_3doc) locked at Wave 0 in tests/eval/conftest.py"

requirements-completed: [EXTRACT-01, EXTRACT-02, EVAL-03, METHOD-01]

# Metrics
duration: 18min
completed: 2026-06-25
---

# Phase 3 Plan 01: Phase 3 Contracts + Nyquist Wave 0 Test Scaffold Summary

**RedFlagRecord cache schema (SnapshotRecord mirror with the refusal discriminator), the 7 canonical red-flag canned queries, all five Phase 3 policy constants, and 8 Wave 0 test files (23 locked function names) + 3 shared eval fixtures — the frozen interface every downstream Phase 3 plan builds against.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-06-25
- **Completed:** 2026-06-25
- **Tasks:** 2
- **Files modified:** 13 (12 created, 1 modified)

## Accomplishments
- `RedFlagRecord` / `RedFlagField` / `RankedRisk` mirroring `SnapshotRecord`, reusing the `{"refusal": ...}` discriminator codec verbatim, with a `REDFLAG_FIELD_KEYS` 7-key allow-list validator that rejects unknown keys.
- `REDFLAG_QUERIES` — 7 plain-English canned queries in UI-SPEC R-1 fixed order, key-synced to the schema allow-list (the `key_links` contract).
- `agent/policies.py` extended with an append-only Phase 3 section: `NUMERIC_GROUNDING_REL_TOLERANCE`, `IDF_BAND_THRESHOLDS`, `F1_NUMERIC_TOLERANCES`, `IDF_BOILERPLATE_FUZZ_THRESHOLD`, `NUMERIC_FAITHFULNESS_GATE=0.95` — each with a calibration comment.
- 8 Wave 0 test files with 23 locked function names; the schema interface test is green now, the 7 implementation-pending modules skip with reasons naming their implementing plan (02–06).
- `tests/eval/conftest.py` with 3 locked shared fixtures + `tests/eval/test_phase3_fixtures.py` exercising them now.

## Task Commits

Each task was committed atomically:

1. **Task 1: RedFlagRecord schema + 7 canned red-flag queries + policy constants** - `0c740b2` (feat)
2. **Task 2: Wave 0 test stubs + shared Phase 3 fixtures (Nyquist scaffold)** - `c8520a1` (test)

_Note: Task 1 was marked `tdd="true"`; see TDD Gate Compliance below._

## Files Created/Modified
- `agent/redflag_schema.py` - RedFlagField/RankedRisk/RedFlagRecord + to_json/from_dict + 7-key validator (created)
- `pipelines/redflag_queries.py` - REDFLAG_QUERIES dict, 7 canonical keys (created)
- `agent/policies.py` - appended Phase 3 tunable-constants section (modified, additive-only)
- `tests/eval/conftest.py` - synthetic_redflag_record, tiny_extraction_labels, idf_corpus_3doc fixtures (created)
- `tests/unit/test_redflag_schema.py` - interface gate (green now): roundtrip, unknown-key reject, refusal-no-confidence (created)
- `tests/unit/test_redflag_precompute.py` - skip until Plan 03 (created)
- `tests/unit/test_confidence_rubric.py` - skip until Plan 02 (created)
- `tests/unit/test_numeric_grounding.py` - skip until Plan 02 (created)
- `tests/unit/test_risk_idf.py` - skip until Plan 03 (created)
- `tests/unit/test_methodology_pane.py` - skip until Plan 06 (created)
- `tests/eval/test_extraction_f1.py` - skip until Plan 04 (created)
- `tests/eval/test_release_gate.py` - skip until Plan 05 (created)
- `tests/eval/test_phase3_fixtures.py` - non-skipped fixture-contract test (created)

## Decisions Made
- RedFlagRecord copies SnapshotRecord's serialization shape; the field codec is the shared `{"refusal": ...}` discriminator — no new codec invented (03-PATTERNS.md §"Union-discriminator cache codec").
- The 7 keys are locked in UI-SPEC R-1 order in both the schema frozenset and the query dict; the validator enforces sync.
- `NUMERIC_FAITHFULNESS_GATE` is the locked 0.95 invariant; the other four constants are documented placeholders to calibrate empirically (procedure → `eval/gold/extraction_rubric.md`, created in a later plan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Schema interface test made self-contained instead of fixture-dependent**
- **Found during:** Task 2 (Wave 0 test stubs)
- **Issue:** The plan places the `synthetic_redflag_record` fixture in `tests/eval/conftest.py`, but the schema interface test lives in `tests/unit/test_redflag_schema.py`. pytest conftest fixtures are only visible within their directory subtree, so the unit test errored with "fixture not found" when it requested the eval-scoped fixture.
- **Fix:** Gave `test_redflag_schema.py` its own local record builder (`_grounded_answer`/`_record`) so the interface gate is self-contained, and added a dedicated non-skipped `tests/eval/test_phase3_fixtures.py` in the eval tree to satisfy the acceptance criterion that `synthetic_redflag_record` is exercised in a collected, passing test (it round-trips there).
- **Files modified:** tests/unit/test_redflag_schema.py, tests/eval/test_phase3_fixtures.py (new)
- **Verification:** `pytest` — the 3 schema interface tests pass; the 3 fixture-contract tests pass; full suite green.
- **Committed in:** `c8520a1` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to make the locked schema test runnable while keeping the shared fixtures where the plan placed them. No scope creep — the same fixtures and the same locked function names exist; one extra small fixture-contract test file was added to honor the acceptance criterion.

## TDD Gate Compliance

Task 1 was marked `tdd="true"`, but its `<verify>` is an import-assertion (interface presence) rather than a behavioral test, and the plan's explicit task ordering places the behavioral interface tests (`test_redflag_schema.py`) in Task 2. The plan therefore separates production (Task 1) from tests (Task 2) by design, so a strict per-task RED→GREEN commit pair was not applicable. Compliance was satisfied at the plan level: the Task 1 import assertion passed before commit, and the Task 2 interface tests assert real behavior against the Task 1 schema and pass (3 green schema tests). No `feat` shipped behavior that lacks a corresponding green test in this plan.

## Issues Encountered
- The repo uses `.venv/bin/python` (Python 3.11); the shell's default `python`/`python3` resolved to an unrelated conda env. Used the project venv interpreter for all test runs.

## User Setup Required
None - no external service configuration required. (The Phase 3 constants are placeholders to calibrate in later plans; no env vars or services added here.)

## Next Phase Readiness
- The Phase 3 interface is frozen: schema, the 7 query keys, and all policy constants exist. Plans 02–06 implement against them and flip their skipped Wave 0 tests to real assertions.
- Pre-existing out-of-scope failure: `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` (missing `sentence-transformers`) — documented in STATE.md as ignorable; untouched by this plan.
- No blockers.

## Self-Check: PASSED

All 13 created/modified files present on disk; both task commits (`0c740b2`, `c8520a1`) present in git history.

---
*Phase: 03-structured-signal-extraction-red-flag-table*
*Completed: 2026-06-25*
