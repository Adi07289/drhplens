---
phase: 02-multi-ipo-catalogue-drhp-snapshot-surface
plan: 01
subsystem: testing
tags: [pytest, xfail, catalogue, snapshot, scaffolding]

requires:
  - phase: 01-foundation-mvp-a-cited-q-a-on-one-ipo
    provides: 219-test pytest baseline, GroundedAnswer/Claim schema, swiggy_2024_11 ingestion pattern
provides:
  - 12 collectible xfail test stubs, one per 02-VALIDATION.md Per-Task Verification Map row
  - data/catalogue.json schema stub with one fully-populated Swiggy canonical entry
  - data/snapshots/ directory tracked in git via .gitkeep
  - 02-VALIDATION.md nyquist_compliant: true, wave_0_complete: true
affects: [02-02-drhp_id-threading, 02-03-ingest-generalize, snapshot-precompute-waves]

tech-stack:
  added: []
  patterns:
    - "xfail stub pattern: module docstring naming requirement+threat, single test_<behavior> function, @pytest.mark.xfail(reason=..., strict=False), body raises NotImplementedError, no module-top-level imports of not-yet-existing Phase 2 modules"
    - "Integration xfail(run=False) gate mirrors tests/integration/test_qdrant_ingest.py (live-Qdrant deferred)"
    - "Eval skipif gate mirrors tests/eval/test_phase1_eval.py (--run-eval / RUN_EVAL env var)"

key-files:
  created:
    - tests/unit/test_drhp_id_threading.py
    - tests/unit/test_drhp_id_allowlist.py
    - tests/unit/test_catalogue.py
    - tests/unit/test_ingest_generalize.py
    - tests/unit/test_ingest_idempotent.py
    - tests/unit/test_parse_quality.py
    - tests/unit/test_snapshot_cache.py
    - tests/unit/test_snapshot_fields.py
    - tests/unit/test_ofs_fresh.py
    - tests/integration/test_second_ipo_e2e.py
    - tests/eval/test_snapshot_eval.py
    - tests/eval/test_p13_recall.py
    - data/catalogue.json
    - data/snapshots/.gitkeep
    - .planning/phases/02-multi-ipo-catalogue-drhp-snapshot-surface/02-01-INSTALL-NOTES.md
  modified:
    - .planning/phases/02-multi-ipo-catalogue-drhp-snapshot-surface/02-VALIDATION.md

key-decisions:
  - "fresh_vs_ofs kept as a nullable catalogue.json field (per plan-checker WARN) with an inline _fresh_vs_ofs_note documenting that the real source of truth is the per-IPO snapshot's ofs_fresh field, computed in Wave 3 from the use-of-proceeds GroundedAnswer — not this catalogue field"
  - "Documented the actual baseline as 226 passed / 1 pre-existing failure (sentence-transformers not installed) rather than the execution-context's assumed 219 — the 1 failure predates this plan and is out of scope (no embedder code touched in Wave 0)"

patterns-established:
  - "Wave 0 scaffold pattern: every later wave's <verify> command is resolvable from day one via xfail stubs; flipping a stub from xfail to a real assertion is the unit of work for each subsequent wave"

requirements-completed: [SNAP-01, SNAP-02, SNAP-03, SNAP-04, SNAP-05, SNAP-06, SNAP-07, OPS-01]

duration: 35min
completed: 2026-06-23
---

# Phase 2 Plan 01: Wave 0 Scaffold (Test Stubs + Catalogue Schema + Snapshot Dir) Summary

**12 xfail test stubs covering every 02-VALIDATION.md row, plus a one-IPO catalogue.json schema stub and tracked data/snapshots/ directory — the Nyquist scaffold that makes every later Phase 2 wave's verify command resolvable from day one.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-06-23T17:57:00Z
- **Completed:** 2026-06-23T18:32:46Z
- **Tasks:** 2/2
- **Files modified:** 15 (12 new test files, 1 new catalogue.json, 1 new .gitkeep, 1 modified VALIDATION.md, plus 1 install-notes doc)

## Accomplishments
- All 12 rows of the 02-VALIDATION.md Per-Task Verification Map now have a collectible, xfail-marked test stub (unit, integration, eval) — no production code touched.
- `data/catalogue.json` carries the canonical schema with a fully-populated Swiggy entry (`swiggy_2024_11`) matching every required key the Wave 1 loader will validate against.
- `data/snapshots/.gitkeep` tracks the (currently empty) snapshot cache directory that Wave 3's pre-compute pipeline will populate.
- `02-VALIDATION.md` front-matter flipped to `nyquist_compliant: true` + `wave_0_complete: true`.
- Phase 1 baseline (226 passed / 1 pre-existing unrelated failure) stayed exactly unchanged before and after both tasks; 9 new unit/integration xfails register cleanly (the 2 eval stubs are skipped, not xfailed, since `--run-eval` was not passed — expected).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the 12 test stubs (xfail-gated)** - `71a027f` (test)
2. **Task 2: Catalogue schema stub + snapshots dir + flip nyquist flags** - `b0e8050` (feat)

**Plan metadata:** pending (final docs commit follows this summary)

## Files Created/Modified
- `tests/unit/test_drhp_id_threading.py` - xfail stub for Wave 1 drhp_id GraphState threading
- `tests/unit/test_drhp_id_allowlist.py` - xfail stub for Wave 1 catalogue allow-list validation (V5)
- `tests/unit/test_catalogue.py` - xfail stub for Wave 1 catalogue.json loader/schema validation
- `tests/unit/test_ingest_generalize.py` - xfail stub for Wave 2 generalized `pipelines/ingest.py`
- `tests/unit/test_ingest_idempotent.py` - xfail stub for Wave 2 delete-by-filter re-ingest idempotency
- `tests/unit/test_parse_quality.py` - xfail stub for Wave 2 P14 parse-quality gate
- `tests/unit/test_snapshot_cache.py` - xfail stub for Wave 3 snapshot cache JSON round-trip
- `tests/unit/test_snapshot_fields.py` - xfail stub for Wave 3 6-field snapshot computation + honest refusal
- `tests/unit/test_ofs_fresh.py` - xfail stub for Wave 3 OFS-vs-fresh neutral split computation
- `tests/integration/test_second_ipo_e2e.py` - xfail(run=False) stub gated on live Qdrant, mirrors `test_qdrant_ingest.py`
- `tests/eval/test_snapshot_eval.py` - skipif(--run-eval) + xfail stub for Wave 5 financials faithfulness
- `tests/eval/test_p13_recall.py` - skipif(--run-eval) + xfail stub for Wave 5 Indian-finance recall probe
- `data/catalogue.json` - schema_version 1 + canonical Swiggy entry; 7 remaining IPOs deferred to Wave 1
- `data/snapshots/.gitkeep` - tracks the empty snapshot cache directory
- `.planning/phases/02-multi-ipo-catalogue-drhp-snapshot-surface/02-VALIDATION.md` - `nyquist_compliant: true`, `wave_0_complete: true`
- `.planning/phases/02-multi-ipo-catalogue-drhp-snapshot-surface/02-01-INSTALL-NOTES.md` - documents the actual 226/1-failure baseline vs. the assumed 219

## Decisions Made
- Kept `fresh_vs_ofs` in `catalogue.json` as a nullable field with an inline comment-field (`_fresh_vs_ofs_note`) rather than omitting it, per the plan's explicit instruction to keep it nullable while documenting that the snapshot's `ofs_fresh` is the real source of truth (Wave 3).
- Did not attempt to fix the pre-existing `sentence-transformers` missing-dependency failure — out of scope for a pure-scaffolding Wave 0 plan that touches no embedder code (Rule 3 exclusion: package installs are not auto-fixable, and this file isn't in this plan's file list anyway).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Baseline test count corrected from assumed 219 to actual 226**
- **Found during:** Setup (pre-task baseline check)
- **Issue:** The execution-context brief assumed a 219-test Phase 1 baseline; the actual `pytest tests/unit -q --timeout=15` baseline on this checkout is 226 passed + 1 pre-existing failure (`test_embedder.py::test_bge_m3_real_embed_query_1024_dim`, missing `sentence-transformers`).
- **Fix:** Documented the real baseline in `02-01-INSTALL-NOTES.md` and used "226 passed before == 226 passed after, no new failures" as this plan's actual regression bar instead of the stale 219 figure. No code changed — this is a documentation correction only.
- **Files modified:** `.planning/phases/02-multi-ipo-catalogue-drhp-snapshot-surface/02-01-INSTALL-NOTES.md`
- **Verification:** Ran `pytest tests/unit -q --timeout=15` before Task 1 (226 passed/1 failed) and after Task 2 (226 passed/1 failed/9 xfailed) — identical pass count, no regression.
- **Committed in:** N/A (install-notes doc committed in the final metadata commit, not a task commit, since it's not in this plan's `files_modified` list but is a Rule-1 documentation correction)

---

**Total deviations:** 1 auto-fixed (1 bug — stale baseline assumption corrected via documentation, no code change)
**Impact on plan:** No scope creep. The pre-existing `sentence-transformers` failure is unrelated to any file this plan touches and was left untouched per the Rule 3 package-install exclusion and the scope-boundary rule (out-of-scope failures are logged, not fixed).

## Issues Encountered
None beyond the baseline-count correction documented above.

## User Setup Required

None - no external service configuration required. Pure scaffolding: no API keys, no live Qdrant, no network calls. The pre-existing `sentence-transformers` gap (unrelated to this plan) would need `pip install sentence-transformers` in a future plan that touches the embedder, but is explicitly out of scope here.

## Next Phase Readiness

Wave 1 (02-02, drhp_id threading + catalogue allow-list + remaining 7 catalogue IPOs) is unblocked: `tests/unit/test_drhp_id_threading.py`, `test_drhp_id_allowlist.py`, and `test_catalogue.py` are in place as the concrete failing tests Wave 1 must flip to real assertions. `data/catalogue.json` schema is locked (`schema_version: 1` + required key set), so Wave 1 can append the remaining 7 IPOs (Hyundai, Ola Electric, Zomato, Nykaa, Paytm, LIC, Mamaearth) without a schema migration.

---
*Phase: 02-multi-ipo-catalogue-drhp-snapshot-surface*
*Completed: 2026-06-23*

## Self-Check: PASSED

All 14 created files verified present on disk; both task commits (`71a027f`, `b0e8050`) verified present in `git log`.
