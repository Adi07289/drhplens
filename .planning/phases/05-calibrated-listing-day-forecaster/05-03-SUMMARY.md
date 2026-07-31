---
phase: 05-calibrated-listing-day-forecaster
plan: 03
subsystem: forecast
tags: [forecast-record, cache-only, isolation-audit, pydantic, allow-list, path-traversal, inspect-getsource, pytest]

# Dependency graph
requires:
  - phase: 05-calibrated-listing-day-forecaster
    provides: "05-01 committed seed render records (data/forecasts/{swiggy_2024_11,hyundai_2024_10}.json) that this schema must parse byte-for-byte; data.catalogue_loader.is_known_drhp_id allow-list (Phase 2) for the path gate"
provides:
  - "agent.forecast_schema.ForecastRecord — flat pydantic+stdlib-only record with nested ForecastInterval (low/high/median/width) + GLOBAL ForecastMetrics (coverage/mae/backtest_window/n/per_year_rmse); covered/abstain/missing first-class states; to_dict/to_json/from_dict/from_json codec"
  - "pipelines.forecast.load_forecast(drhp_id) — allow-list-gated cache reader that gates drhp_id via is_known_drhp_id BEFORE forming any data/forecasts/<id>.json path (path-traversal), returns a ForecastRecord, raises FileNotFoundError on a missing file (the render's honest not-covered state)"
  - "tests/unit/test_forecast_isolation.py — two-direction inspect.getsource import audit mirroring test_gmp_isolation.py (render imports no model; predictor imports no display signal), with 05-05/05-07 modules importorskip-guarded so it auto-runs when they land"
affects: [05-05, 05-06, 05-07, 05-10, 05-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cache-only isolation boundary: a flat pydantic record (pydantic + stdlib only, NO modeling library) is the single seam between the offline forecaster and the cache-only Streamlit render"
    - "First-class abstain/missing states: interval is None on abstain (never a fabricated band or metric); is_abstain property; missing file -> FileNotFoundError (honest not-covered), not a synthesized zero"
    - "Two-direction inspect.getsource import audit (mirror of Phase 4 test_gmp_isolation.py): render side imports no model module; predictor side imports no display/GMP signal — pinned both ways"
    - "Allow-list gate BEFORE path formation: is_known_drhp_id(drhp_id) runs before any data/forecasts/<id>.json path is constructed (path-traversal defense)"

key-files:
  created:
    - agent/forecast_schema.py
    - pipelines/forecast/__init__.py
    - tests/unit/test_forecast_schema.py
    - tests/unit/test_forecast_isolation.py
  modified: []

key-decisions:
  - "FORECASTS_DIR uses Path(__file__).resolve().parents[2] (repo-root data/forecasts), not the plan's literal .parent.parent which would resolve to pipelines/data/forecasts — the loader __init__ sits one level deeper than pipelines/gmp.py (Rule 1 fix, matches the RESEARCH sketch)"
  - "FCAST-02 left Pending: 05-03 delivers only the isolation clause (no display signal, pinned both directions) + the cache seam; the available_at feature-leakage half lands in 05-04/05-05 and the render half in 05-07 (mirrors 05-02 leaving FCAST-03 open — project honesty invariant)"
  - "Schema + loader deliberately avoid the literal substrings 'shap'/'gmp' in their own source so the token-level import audit stays green (the 'shape'->'shap' substring gotcha)"

patterns-established:
  - "importorskip-guarded forward audit: not-yet-built 05-05 (pipelines.forecast.model/walkforward, pipelines.features) and 05-07 (ui.forecast_block) modules are importorskip-skipped so the isolation test is green today and auto-executes the real cross-import check the moment they land"

requirements-completed: []

# Metrics
duration: ~20 min
completed: 2026-07-17
---

# Phase 5 Plan 03: ForecastRecord Cache-Only Contract + Two-Direction Isolation Audit

**Defined the `ForecastRecord` schema and the allow-list-gated `load_forecast(drhp_id)` reader that together form the single cache-only seam between the offline forecaster and the Streamlit render — importing NO modeling library, parsing the two 05-01 committed seeds byte-for-byte, treating covered/abstain/missing as first-class states, and pinned by a two-direction `inspect.getsource` isolation audit that mirrors the Phase 4 GMP test.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 4 (4 created, 0 modified)
- **Note:** the executor session was interrupted by a usage limit after both task commits landed and the STATE.md body was written but before the SUMMARY + tracking commit; the orchestrator closed the plan out manually per the safe-resume gate (both task commits verified present, full suite re-run green — no re-execution).

## Accomplishments
- `agent/forecast_schema.py` — a flat, import-light (`pydantic` + stdlib only) `ForecastRecord` with nested `ForecastInterval` (low/high/median/width) and a GLOBAL `ForecastMetrics` block (coverage/mae/backtest_window/n/per_year_rmse). Covered and abstain are first-class states (interval `None` on abstain — no fabricated numbers), an `is_abstain` property, `median_pct` kept a plain field (P21), and a `to_dict/to_json(indent=2, ensure_ascii=False)/from_dict/from_json` codec that parses the two committed `data/forecasts/*.json` seeds byte-for-byte.
- `pipelines/forecast/__init__.py` — `load_forecast(drhp_id)` gates `drhp_id` through `is_known_drhp_id` BEFORE forming any `data/forecasts/<id>.json` path (path-traversal, T-05-03-PATH), returns a `ForecastRecord`, and raises `FileNotFoundError` on a missing file (the render's honest not-covered state). `FORECASTS_DIR` uses `resolve().parents[2]` (Rule 1 fix — see Decisions).
- `tests/unit/test_forecast_schema.py` — round-trip + covered/abstain state + import-audit tests (7).
- `tests/unit/test_forecast_isolation.py` — the two-direction `inspect.getsource` audit mirroring `test_gmp_isolation.py`: the render imports no model; the predictor/loader/record imports no display/GMP signal; not-yet-built 05-05/05-07 modules `importorskip`-guarded; plus unknown-id `ValueError`, committed-seed reads, and missing-file `FileNotFoundError`.

## Task Commits

Each task was committed atomically:

1. **Task 1: ForecastRecord schema + codec + first-class abstain state** — `7fe818e` (feat)
2. **Task 2: allow-list-gated load_forecast + two-direction isolation audit** — `0d90ebd` (feat)

**Plan metadata:** committed with this SUMMARY (docs) — written by the orchestrator during safe-resume close-out.

## Files Created/Modified
- `agent/forecast_schema.py` (NEW) — `ForecastInterval`, `ForecastMetrics`, `ForecastRecord` (+ `is_abstain`), `to_dict/to_json/from_dict/from_json` codec.
- `pipelines/forecast/__init__.py` (NEW) — `load_forecast(drhp_id)` allow-list-gated cache reader; `FORECASTS_DIR = Path(__file__).resolve().parents[2] / "data" / "forecasts"`.
- `tests/unit/test_forecast_schema.py` (NEW) — 7 tests (codec round-trip on both seeds, covered/abstain states, no-modeling-import audit).
- `tests/unit/test_forecast_isolation.py` (NEW) — two-direction import audit + allow-list/path-traversal + missing-file behavior (11 tests, 4 importorskip-skipped pending 05-05/05-07).

## Decisions Made
- **`FORECASTS_DIR` = `resolve().parents[2]` (Rule 1 fix).** The plan's literal `.parent.parent` would resolve to `pipelines/data/forecasts`, because the loader `__init__.py` sits one directory deeper than `pipelines/gmp.py`. Corrected to repo-root `data/forecasts`, matching the RESEARCH sketch and the location of the committed seed records.
- **FCAST-02 left Pending (not marked complete).** 05-03 delivers the isolation clause (render imports no model; predictor imports no display signal, pinned both directions) plus the cache seam. FCAST-02's `available_at` feature-leakage half is built in 05-04/05-05 and the render half in 05-07 — marking it complete now would be dishonest (project honesty invariant), so it stays Pending, mirroring 05-02's FCAST-03 handling.
- **Avoided the `shape`→`shap` substring gotcha.** The schema and loader deliberately avoid the literal substrings `shap`/`gmp` in their own source so the token-level import audit stays green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Broken as Written] `FORECASTS_DIR` path depth**
- **Found during:** Task 2 (loader)
- **Issue:** The plan's literal `Path(__file__).parent.parent / "data" / "forecasts"` resolves to `pipelines/data/forecasts`, not the repo-root `data/forecasts` where the 05-01 seeds are committed, because `pipelines/forecast/__init__.py` is one level deeper than the `pipelines/gmp.py` the sketch was patterned on.
- **Fix:** `Path(__file__).resolve().parents[2] / "data" / "forecasts"`.
- **Verification:** `load_forecast("swiggy_2024_11")` and `load_forecast("hyundai_2024_10")` both parse the committed seeds; unknown ids raise `ValueError`, missing files raise `FileNotFoundError`.
- **Committed in:** `0d90ebd` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 broken-as-written path fix). **Impact on plan:** none to scope — the loader now reads the real committed records. No new dependencies; schema imports pydantic + stdlib only.

## Issues Encountered
- **Executor session interrupted by usage limit.** The gsd-executor hit a session/usage limit after both atomic task commits (`7fe818e`, `0d90ebd`) landed and the STATE.md body had been written (uncommitted), but before it wrote the SUMMARY and committed the tracking files. Per the GSD safe-resume gate (production commits present + SUMMARY missing → close out manually, do not re-execute), the orchestrator verified both commits contain the complete file set, re-ran the full unit suite green, and wrote this SUMMARY + committed the tracking files. No task work was re-done or duplicated.
- **Pre-existing (out of scope):** `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` still fails (`sentence-transformers is not installed`) — the documented ignorable embedder failure, not a regression. Suite went 376 passed → 390 passed (+14 new schema/isolation tests, minus the 4 importorskip skips), same single embedder failure throughout.

## User Setup Required
None — no external service configuration required. The schema and loader are pure offline code.

## Next Phase Readiness
- The cache-only contract is in place and offline-green: it parses the two 05-01 committed seeds verbatim, so the render slice (05-07) and the precompute writer (05-06) can build against the fixtures in parallel with the offline model.
- The forward isolation audit is `importorskip`-guarded on `ui.forecast_block` (05-07) and `pipelines.forecast.model`/`walkforward` + `pipelines.features` (05-05); it will auto-execute the real cross-import check the moment those modules land.
- **FCAST-02 remains Pending** in REQUIREMENTS.md (feature-leakage + render halves outstanding) — do not close it until 05-04/05-05/05-07 land.

## Self-Check: PASSED

- Created files verified on disk: `agent/forecast_schema.py`, `pipelines/forecast/__init__.py`, `tests/unit/test_forecast_schema.py`, `tests/unit/test_forecast_isolation.py` — all FOUND.
- Task commits verified in git log: `7fe818e` FOUND, `0d90ebd` FOUND.
- Plan verification re-run: `pytest tests/unit/test_forecast_schema.py tests/unit/test_forecast_isolation.py -q` → 14 passed, 4 skipped; full `pytest tests/unit -q` → 390 passed, 4 skipped, 1 pre-existing embedder failure; `forecast_schema.py` source contains no `xgboost/mapie/sklearn/mlflow/shap` reference.

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-17*
