---
phase: 05-calibrated-listing-day-forecaster
plan: 01
subsystem: infra
tags: [xgboost, mapie, scikit-learn, mlflow, matplotlib, shap, pandas, numpy, pytest, fixtures, forecasting]

# Dependency graph
requires:
  - phase: 04-historical-ipo-dataset-peer-comparator-gmp
    provides: "pipelines.historical column contract (PANEL_COLUMNS/PANEL_DTYPES/STATUS_VALUES/assemble_panel); GMP seed-fixture CODE-NOW-DEFER posture; catalogue allow-list (is_known_drhp_id)"
provides:
  - "Installed + import-verified non-LLM modeling stack (xgboost/mapie/scikit-learn/mlflow/matplotlib/shap) in the .venv"
  - "tests/unit/fixtures/forecast_fixtures.py — pure, offline, deterministic synthetic_panel/synthetic_features/oos_rows builders"
  - "forecast_* pytest fixtures in tests/unit/conftest.py wrapping the builders"
  - "Two committed data/forecasts/*.json render records: swiggy_2024_11 (full-render) + hyundai_2024_10 (abstain)"
affects: [05-02, 05-03, 05-04, 05-05, 05-06, 05-07, 05-08, 05-09, 05-10, 05-11]

# Tech tracking
tech-stack:
  added: ["xgboost 3.2.0", "mapie 1.4.1", "scikit-learn 1.9.0", "mlflow 3.14.0", "matplotlib 3.11.0", "shap 0.51.0", "libomp (Homebrew, xgboost OpenMP runtime)"]
  patterns: ["Pure offline deterministic test-data builders (seeded, no-network) shared across a wave", "Hand-seeded committed cache records (CODE-NOW-DEFER) to unblock the render slice before the real run"]

key-files:
  created:
    - tests/unit/fixtures/__init__.py
    - tests/unit/fixtures/forecast_fixtures.py
    - data/forecasts/swiggy_2024_11.json
    - data/forecasts/hyundai_2024_10.json
  modified:
    - pyproject.toml
    - tests/unit/conftest.py

key-decisions:
  - "numpy stepped 2.4.6->2.3.5 (still 2.x) so shap imports (shap->numba hard-caps numpy<2.4; no numba release supports numpy 2.4); pandas KEPT at 3.0.3 (mlflow's pandas<3 is a soft cap, imports fine)"
  - "Installed Homebrew libomp to satisfy xgboost's @rpath/libomp.dylib OpenMP dependency on this Intel-macOS venv"
  - "Global metrics block is identical across both forecast records (D5-12); the abstain record carries interval:null and fabricates no per-IPO numbers"
  - "Forecast records are hand-seeded (CODE-NOW-DEFER), regenerated from the real walk-forward run in 05-06/05-11"

patterns-established:
  - "Shared offline builders: seeded numpy RNG -> deterministic pandas frames matching the pipelines.historical contract; socket-blocked to prove no network"
  - "Feature no-leakage stamp: every feature row carries available_at <= issue_date (FCAST-02)"

requirements-completed: [FCAST-01]

# Metrics
duration: ~40 min
completed: 2026-07-16
---

# Phase 5 Plan 01: Modeling Deps + Shared Offline Fixtures Summary

**Installed and import-verified the CLAUDE.md-locked non-LLM modeling stack (xgboost 3.2.0 / mapie 1.4.1 / scikit-learn 1.9.0 / mlflow 3.14.0 / matplotlib 3.11.0 / shap 0.51.0) against pandas 3.0.3 + numpy 2.3.5, and committed the two shared offline assets every later Phase 5 slice consumes: a deterministic synthetic-panel/feature/OOS test fixture and two hand-seeded forecast render records (full + abstain).**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-16T18:08Z
- **Tasks:** 2
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- Declared six ML/forecasting deps in `pyproject.toml` (floors per RESEARCH version-reconciliation) and installed them into the existing `.venv`; all six import cleanly.
- Resolved RESEARCH Assumption A6 (very-new pandas 3.0 / numpy 2.4) empirically: kept pandas at 3.0.3, stepped numpy to 2.3.5 (the newest numpy shap→numba supports — still numpy 2.x), and installed `libomp` for xgboost's OpenMP runtime.
- Built `tests/unit/fixtures/forecast_fixtures.py` — pure, offline, deterministic `synthetic_panel` (full `PANEL_COLUMNS` schema, every `STATUS_VALUES` member incl. `withdrawn`+`delisted`, heteroscedastic ~-20%..+60% returns), `synthetic_features` (issue-structure X with `available_at <= issue_date`), and `oos_rows`.
- Added `forecast_*` pytest fixtures to `tests/unit/conftest.py` without clobbering the existing `synthetic_redflag_record` re-export.
- Committed two hand-seeded `data/forecasts/*.json` render records: `swiggy_2024_11` (full-render band + global metrics, coverage 0.783 ≠ 0.80) and `hyundai_2024_10` (abstain, `insufficient_history`, `interval:null`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add and verify the locked modeling dependencies** — `180ba1c` (chore)
2. **Task 2: Shared offline fixtures + committed forecast records** — `5bc6382` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified
- `pyproject.toml` — added the six ML/forecasting deps under a `# ML / forecasting (Phase 5)` comment; Phase 4 pins (yfinance/requests-cache/jugaad-data) untouched; no `nse`/Diebold-Mariano deps.
- `tests/unit/fixtures/__init__.py` — package marker + intent docstring.
- `tests/unit/fixtures/forecast_fixtures.py` — the three offline builders (synthetic_panel/synthetic_features/oos_rows).
- `tests/unit/conftest.py` — `forecast_synthetic_panel` / `forecast_synthetic_features` / `forecast_oos_rows` pytest fixtures.
- `data/forecasts/swiggy_2024_11.json` — hand-seeded full-render ForecastRecord.
- `data/forecasts/hyundai_2024_10.json` — hand-seeded abstain ForecastRecord.

## Decisions Made
- **numpy 2.4.6 → 2.3.5 (forced), pandas kept at 3.0.3.** `shap` depends on `numba`, which hard-caps `numpy<2.4` at import time; no numba release supports numpy 2.4, so shap literally cannot import under numpy 2.4.6. numpy 2.3.5 is the newest numpy that lets shap import and is still numpy 2.x (satisfies must_have truth "pandas 3.0 / numpy 2.x"). `mlflow` metadata caps `pandas<3`, but that cap is precautionary — mlflow imports and runs fine with pandas 3.0.3 (verified), so pandas was NOT downgraded.
- **libomp installed via Homebrew.** `libxgboost.dylib` links `@rpath/libomp.dylib` with rpath `/usr/local/opt/libomp/lib` (the Homebrew prefix); this Intel-macOS venv had no system libomp. `brew install libomp` placed it exactly on that rpath; xgboost then imports cleanly.
- **Global metrics identical on both records (D5-12); abstain record carries no fabricated numbers.** The abstain record sets `interval:null` and reuses only the global backtest metrics block.
- **Forecast records are seed-only (CODE-NOW-DEFER).** Mirrors the Phase 4 GMP seed posture; both are regenerated from the real walk-forward run in 05-06/05-11.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] numpy downgraded 2.4.6 → 2.3.5 to let shap import (pandas kept at 3.0.3)**
- **Found during:** Task 1 (dependency install/verify)
- **Issue:** The plan instructs "never downgrade pandas/numpy" and its RESEARCH A6 remedy was "pin narrower xgboost/mapie." The real conflict was NOT xgboost/mapie: `shap → numba` hard-caps `numpy<2.4` (numba raises `ImportError: Numba needs NumPy 2.3 or less` at import, and no numba release supports numpy 2.4), and `mlflow` metadata caps `pandas<3`. A clean `pip install` therefore downgraded numpy→2.3.5 AND pandas→2.3.3.
- **Fix:** Restored pandas to 3.0.3 (mlflow's `pandas<3` is a soft/precautionary cap — mlflow imports and its tracking API works fine under pandas 3.0.3, verified). Accepted numpy 2.3.5 (the newest numpy shap→numba supports) as unavoidable — it is still numpy 2.x, which satisfies the authoritative must_have truth "imports cleanly against pandas 3.0 / numpy 2.x."
- **Files modified:** `.venv` (not tracked); resolved versions recorded in `pyproject.toml` comment + here.
- **Verification:** `import xgboost, mapie, sklearn, mlflow, matplotlib, shap` exits 0 under pandas 3.0.3 / numpy 2.3.5; `pytest tests/unit -q` → 375 passed (no import regression).
- **Committed in:** `180ba1c` (Task 1 commit)

**2. [Rule 3 - Blocking] Installed Homebrew libomp for xgboost's OpenMP runtime**
- **Found during:** Task 1 (import verification)
- **Issue:** `import xgboost` failed with `XGBoost Library (libxgboost.dylib) could not be loaded ... OpenMP runtime is not installed`. `libxgboost.dylib` links `@rpath/libomp.dylib` (rpath `/usr/local/opt/libomp/lib`), and this Intel-macOS venv had no libomp there.
- **Fix:** `brew install libomp` (LLVM OpenMP runtime — a legitimate, well-known system package, keg-only at exactly the rpath xgboost expects).
- **Files modified:** system (Homebrew Cellar); not tracked.
- **Verification:** `import xgboost` now exits 0; `xgboost.__version__ == 3.2.0`.
- **Committed in:** N/A (system package; documented here)

---

**Total deviations:** 2 auto-fixed (2 blocking). **Impact on plan:** Both were unavoidable environment realities the plan's RESEARCH A6 remedy did not cover (the numpy blocker is shap→numba, not xgboost/mapie; xgboost also needed a macOS OpenMP runtime). The resolution keeps pandas at 3.0.3 and numpy at 2.x, so the authoritative must_have ("imports cleanly against pandas 3.0 / numpy 2.x") is satisfied. No scope creep; no app regression (unit suite unchanged at 375 passed).

## Issues Encountered
- **Pre-existing (out of scope):** `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` fails with `RuntimeError: sentence-transformers is not installed`. This is the pre-existing "1 ignorable embedder failure" STATE.md already documents — `sentence-transformers` is absent from this venv and is unrelated to the Phase 5 modeling deps. Not fixed (scope boundary). The `.venv` also lacks `llama-index`/`pdfplumber` (pre-existing partial venv state); neither affects tests/unit collection (376 collected clean) nor this plan's deliverables.

## User Setup Required
None - no external service configuration required. (One host-level note: `brew install libomp` was run to satisfy xgboost's OpenMP runtime on macOS; a fresh clone on macOS will need the same one-time `brew install libomp`.)

## Next Phase Readiness
- Wave 2+ is unblocked: the modeling stack imports and the shared synthetic-panel/feature/OOS fixture + the full-render and abstain forecast records are committed.
- Downstream isolation note for 05-03/05-07: the render slice reads only `data/forecasts/*.json` (+ `data/gmp/*.json`); the forecast records here carry no model objects and no GMP fields, consistent with FCAST-02.
- Carry-over (does NOT block Phase 5): 04-07 real historical-panel build is still blocked on chittorgarh source rot (fix in `data/historical/README.md`); the synthetic fixture covers the tests until the real panel is needed.

## Self-Check: PASSED

- Created files verified on disk: `tests/unit/fixtures/__init__.py`, `tests/unit/fixtures/forecast_fixtures.py`, `data/forecasts/swiggy_2024_11.json`, `data/forecasts/hyundai_2024_10.json` — all FOUND.
- Task commits verified in git log: `180ba1c` FOUND, `5bc6382` FOUND.
- Plan verification re-run: six-import exits 0; `pytest tests/unit -q` → 375 passed / 1 pre-existing embedder failure; both `data/forecasts/*.json` parse and satisfy their abstain/interval/coverage state assertions.

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-16*
