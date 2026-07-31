---
phase: 05-calibrated-listing-day-forecaster
plan: 06
subsystem: forecast
tags: [walk-forward, coverage, mae, per-year-rmse, precompute, forecast-record, mlflow, local-file-backend, allow-list, path-traversal, code-now-defer, fcast-01, fcast-04, d5-11, d5-12, p17]

# Dependency graph
requires:
  - phase: 05-calibrated-listing-day-forecaster
    provides: "05-05 pipelines.forecast.walkforward.walk_forward(panel, X) -> OOS DataFrame (one as-of-T0 band per scorable IPO + abstain rows + provenance) and the model constants (PARAMS/QUANTILE_ALPHAS/CONFIDENCE_LEVEL); 05-04 pipelines.features.build.build_features(panel) -> (X, available_at) leakage-gated design matrix; 05-03 agent.forecast_schema.ForecastRecord/ForecastInterval/ForecastMetrics codec + pipelines.forecast._forecast_path allow-list-gated write path + load_forecast reader; 05-01 committed data/forecasts/<id>.json seed shape + the tests/unit/fixtures/forecast_fixtures offline builders; data.catalogue_loader (catalogue + is_known_drhp_id allow-list)"
provides:
  - "pipelines.forecast.diagnostics.global_metrics(oos_df) -> {coverage_empirical, mae_pts, per_year_rmse, mean_width, n} — the GLOBAL walk-forward honesty metrics (D5-12), computed ONCE over the OOS rows; RAW coverage (never clamped to 0.80, P17); abstain/band-less rows excluded; per_year_rmse keyed only by years present (no fabricated year); pandas+stdlib only"
  - "pipelines.forecast.precompute.precompute_forecasts(*, panel, write, track, only, min_train, cal_frac, params) -> {drhp_id: ForecastRecord} — runs build_features -> walk_forward -> global_metrics ONCE and writes one data/forecasts/<id>.json per catalogue IPO (own OOS band D5-11 or first-class abstain + identical global metrics D5-12 + as-of/OOS provenance + pinned model_version), fraction->percentage-points at the boundary, allow-list-gated write, per-IPO failure isolation (P14), single computation wrapped in a local-file-backend mlflow.start_run(); + precompute-one/precompute-all Typer CLI"
  - "tests/unit/test_forecast_metrics.py (6) + tests/unit/test_forecast_precompute.py (7) — coverage/MAE/per-year-RMSE correctness + honesty; precompute own-band/shared-metrics/abstain/path-gate/isolation/round-trip + local MLflow tracking (tmp dir, no server)"
affects: [05-08, 05-09, 05-10, 05-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Global-metrics-once, per-record-shared (D5-12): compute coverage/MAE/per-year-RMSE ONCE over the whole walk-forward, then bake the IDENTICAL block into every IPO's record — the 'how this was tested' numbers describe the forecaster, not one IPO"
    - "RAW empirical coverage (P17 / anti-calibration-theater): coverage = mean((actual>=low)&(actual<=high)) reported as-is; the only rounding is 4-dp display precision that can never move a non-0.80 value TO 0.80; abstain rows are NOT 0%-error rows and contribute to no statistic"
    - "Fraction->percentage-points at the model->record boundary (RETURN_TO_PCT=100): the walk-forward speaks fraction listing_day_return, the record + UI speak points, so precompute multiplies the band + realized return by 100 once — keeping records at the swiggy-seed scale and the 05-07 render working"
    - "Single-walk-forward, per-catalogue-IPO writer (mirrors gmp/snapshot precompute): one heavy computation shared across the catalogue loop; own band per IPO or first-class abstain; allow-list-gated write via _forecast_path; per-IPO failure isolation (log-and-skip, P14)"
    - "Corrupt-band guard: a covered OOS row carrying a NaN band RAISES (isolated) rather than fabricating a NaN interval — honesty over silent coercion"
    - "MLflow local-file backend, lazily imported (T-05-06-MLF): the single metrics computation is wrapped in mlflow.start_run() on the default mlruns/ file store (no server, no DB, no remote URI); mlflow imported inside the function so module import + test collection stay offline"

key-files:
  created:
    - pipelines/forecast/diagnostics.py
    - pipelines/forecast/precompute.py
    - tests/unit/test_forecast_metrics.py
    - tests/unit/test_forecast_precompute.py
  modified: []

key-decisions:
  - "global_metrics returns RAW coverage (rounded only to 4 dp for a diff-reviewable committed record) — 4-dp precision can never clamp a non-0.80 value to 0.80, so it honors P17 strictly while keeping the record clean. mae/mean_width/per_year_rmse rounded to 2 dp; n is the scored-row count."
  - "Units conversion added at the model->record boundary (RETURN_TO_PCT=100). walk_forward emits (close-issue)/issue = FRACTION; the ForecastRecord interval + ForecastMetrics + the 05-07 render + the swiggy seed are all percentage POINTS. precompute multiplies the band + realized return by 100 BEFORE computing metrics/writing intervals. Not spelled out in the plan; required for the real 05-11 records to be honest (a 6.1% band, not 0.061%). global_metrics itself stays scale-agnostic (percentage points in, points out) so the oos_rows fixture and hand-constructed metric frames are authored directly in points."
  - "as_of_listing_date + sector are sourced from the CATALOGUE (CatalogueIPO.listing_date / .sector), not the OOS frame — the walk-forward OOS frame carries listing_year + t0(issue_date) but no full listing date, and the catalogue is the canonical per-IPO listing-date/sector source. (Current catalogue listing_date is month-precision, e.g. '2024-11'; the field accepts any ISO date string so a future full-date catalogue refines it automatically.)"
  - "MLflow 3.14 put the local file store into MAINTENANCE MODE (raises unless MLFLOW_ALLOW_FILE_STORE=true). CLAUDE.md + 05-RESEARCH lock the local file backend (mlruns/, no server). precompute opts in via os.environ.setdefault('MLFLOW_ALLOW_FILE_STORE','true') before start_run (Rule 3 blocking fix) — keeps the locked, server-less architecture on MLflow 3.x without switching to a DB backend."
  - "FCAST-04 left PENDING (not marked complete). The precompute is CODE-NOW-DEFER — metrics + records are proven only OFFLINE by monkeypatching walk_forward over the synthetic fixture; the REAL committed records + the committed mlruns/ run regenerate from the live survivorship panel at 05-11. Closing FCAST-04 (or re-seeding real records) now would be dishonest, mirroring 05-05/05-07's Pending posture. FCAST-01 was already marked Complete upstream and is left untouched."
  - "precompute_forecasts returns {drhp_id: ForecastRecord} only for catalogue IPOs that produced a record; an IPO with no OOS row (not in the panel) is skipped (-> the render's honest 'no calibrated forecast available yet' missing-file state), distinct from a first-class abstain. An `only` set restricts which records are written while the global walk-forward + metrics still run over the whole panel (used by precompute-one)."

patterns-established:
  - "diagnostics.global_metrics is the single metrics seam the model card (05-10) and the precompute both call; it takes any frame with actual/low/high/median/listing_year (+ optional abstain)"
  - "precompute._to_percent_frame is the one place fraction->points conversion happens; downstream (records, metrics, MLflow) all read points"

requirements-completed: []

# Metrics
duration: ~15 min
completed: 2026-07-19
---

# Phase 5 Plan 06: Global Walk-Forward Metrics + Per-IPO ForecastRecord Precompute CLI + MLflow Summary

**Built the model→record bridge: `global_metrics` aggregates the as-of-T0 walk-forward into the GLOBAL honesty numbers (empirical coverage, MAE, per-year RMSE) computed ONCE and identical on every IPO page (D5-12), with coverage kept as the RAW held-out value (never clamped to the 0.80 target, P17); and `precompute_forecasts` runs the walk-forward + metrics once and writes one `data/forecasts/<id>.json` per catalogue IPO — each carrying its OWN out-of-sample band (D5-11) or a first-class abstain plus the shared metrics block + as-of/OOS provenance — all offline-tested by monkeypatching the walk-forward, with the single computation tracked to a local-file-backend MLflow run (`mlruns/`, no server).**

## Performance

- **Duration:** ~15 min (active; wall-clock spanned a session-idle boundary across the date rollover)
- **Tasks:** 2
- **Files modified:** 4 (4 created, 0 modified)

## Accomplishments
- `pipelines/forecast/diagnostics.py` — `global_metrics(oos_df)` returns `{coverage_empirical, mae_pts, per_year_rmse, mean_width, n}`: coverage is the RAW held-out mean `mean((actual>=low)&(actual<=high))` (never clamped to 0.80 — P17); `mae_pts` = mean |actual−median|; `per_year_rmse` = `{str(year): sqrt(mean(se))}` keyed ONLY by the years actually present (no fabricated year); abstain rows and band-less rows contribute to no statistic; `n` counts scored rows. pandas + stdlib only (no sklearn) so it stays offline and light.
- `pipelines/forecast/precompute.py` — `precompute_forecasts(*, panel, write, track, only, ...)` runs `build_features(panel) → walk_forward(...) → global_metrics(...)` ONCE, converts the band + realized return from fraction to percentage points (`RETURN_TO_PCT=100`), then loops the catalogue building one `ForecastRecord` per IPO: its own OOS band (`ForecastInterval` low/high/median/width, D5-11) or a first-class abstain (`interval=None` + honest reason), plus the IDENTICAL global metrics block (D5-12), `as_of_listing_date` + `out_of_sample`/`walk_forward` provenance, and a pinned `model_version="cqr-xgb-2026.07-v1"`. Writes via the allow-list-gated `_forecast_path` (T-05-06-PATH); per-IPO failure isolation (P14, `# noqa: BLE001`); a covered-but-NaN-band row RAISES rather than fabricating an interval. `precompute-one`/`precompute-all` Typer CLI mirror `pipelines/gmp.py`.
- MLflow tracking — the single `walk_forward + global_metrics` computation is wrapped in `mlflow.start_run()` on the LOCAL FILE backend (default `mlruns/`, no remote URI), logging `coverage_empirical`/`mae_pts`/`mean_width`/`n` + per-year `rmse_<year>` + the key CQR/XGBoost params (quantile alphas 0.1/0.5/0.9, `confidence_level=0.8`, `min_train`, `cal_frac`, `n_estimators`, `max_depth`, `model_version`). mlflow is imported LAZILY inside the function; `MLFLOW_ALLOW_FILE_STORE` is opted-in for MLflow 3.x's maintenance-mode file store (see Deviation 2).
- Two offline test files (13 cases): `test_forecast_metrics.py` (6) pins exact coverage (3-of-4=0.75, NOT 0.80)/MAE/per-year-RMSE + all-covered=1.0-not-clamped + abstain-excluded + empty=NaN; `test_forecast_precompute.py` (7) pins own-band + shared-metrics (D5-12), abstain-fabricates-no-interval, path-gate rejects traversal, per-IPO isolation of a corrupt row (P14), `load_forecast` round-trip through the 05-03 codec, and a local-file-backend MLflow run logging coverage/MAE to a tmp `mlruns/` (no server).

## Task Commits

Each task was committed atomically:

1. **Task 1: global_metrics — coverage / MAE / per-year RMSE (D5-12)** — `5b05ec1` (feat)
2. **Task 2: precompute CLI — per-IPO record writer + MLflow tracking (FCAST-01, D5-11)** — `4078df5` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

_Note: MVP mode ON / TDD mode OFF per the execution brief — each task's module + its test were committed together in one atomic `feat` commit (no separate RED/GREEN commits)._

## Files Created/Modified
- `pipelines/forecast/diagnostics.py` (NEW) — `global_metrics(oos_df)`; RAW coverage (P17), abstain/band-less excluded, no fabricated year; `_BAND_COLUMNS`; pandas+stdlib only.
- `pipelines/forecast/precompute.py` (NEW) — `precompute_forecasts` + `_to_percent_frame`/`_backtest_window`/`_build_record`/`_write_record`/`_run_and_score`/`_log_run`/`_load_panel`; `MODEL_VERSION`/`RETURN_TO_PCT`; `precompute-one`/`precompute-all` CLI; local-file-backend MLflow wiring.
- `tests/unit/test_forecast_metrics.py` (NEW) — 6 tests.
- `tests/unit/test_forecast_precompute.py` (NEW) — 7 tests (offline, walk_forward monkeypatched; MLflow → tmp dir).

## Decisions Made
- **RAW coverage, 4-dp display rounding only** — honors P17 (never clamp to 0.80) while keeping a diff-reviewable committed record. See key-decisions.
- **Units conversion at the model→record boundary (`RETURN_TO_PCT=100`)** — see Deviation 1.
- **MLflow file-store opt-in (`MLFLOW_ALLOW_FILE_STORE`)** — see Deviation 2.
- **`as_of_listing_date` + `sector` sourced from the catalogue** — the OOS frame lacks a full listing date; the catalogue is the canonical source (month-precision today, ISO-string-compatible for a future refine).
- **FCAST-04 left Pending; FCAST-01 untouched (already Complete upstream).** The precompute is CODE-NOW-DEFER — proven offline over the synthetic fixture only; real records + `mlruns/` regenerate at 05-11. Closing FCAST-04 now would be dishonest (mirrors 05-05/05-07's Pending posture).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical] Fraction→percentage-points conversion at the model→record boundary**
- **Found during:** Task 2 (precompute record construction)
- **Issue:** `walk_forward` emits `listing_day_return = (close − issue) / issue` — a FRACTION (e.g. `0.061` for +6.1%) — because it trains/predicts on the panel's fraction target. But `ForecastRecord.interval` (`*_pct`), `ForecastMetrics` (`mae_pts`), the 05-07 render, and the hand-seeded `data/forecasts/swiggy_2024_11.json` (`median_pct: 6.1`, `mae_pts: 11.4`) are all in percentage POINTS. Writing the raw fraction band would produce a dishonest `median_pct: 0.061` (a 0.06% band) at the real 05-11 run and break the render's scale.
- **Fix:** `precompute._to_percent_frame` multiplies the band + realized return (`actual/low/high/median`) by `RETURN_TO_PCT=100` ONCE, at the single model→record boundary, BEFORE computing global metrics or building intervals. `global_metrics` itself stays scale-agnostic (points in, points out), so the `oos_rows` fixture and the hand-constructed metric frames are authored directly in points.
- **Files modified:** `pipelines/forecast/precompute.py`
- **Verification:** `test_records_carry_own_band_and_shared_global_metrics` crafts a fraction band `low=-0.042/median=0.061/high=0.217` and asserts the record carries `-4.2 / 6.1 / 21.7` (width `25.9`) — the exact swiggy-seed scale.
- **Committed in:** `4078df5` (Task 2 commit)

**2. [Rule 3 — Blocking] `MLFLOW_ALLOW_FILE_STORE` opt-in for MLflow 3.x's maintenance-mode file store**
- **Found during:** Task 2 (the MLflow tracking test)
- **Issue:** MLflow 3.14.0 puts the local filesystem tracking backend into "maintenance mode" and RAISES `MlflowException` on `start_run()` against a `file://` store unless `MLFLOW_ALLOW_FILE_STORE=true` is set (it steers users to a SQLite/DB backend). CLAUDE.md and 05-RESEARCH LOCK the local file backend (`mlruns/`, committed, no server, no DB) — so a DB backend is not an option; this is exactly the "MLflow 3.x API divergence" the brief flagged, but it has a documented, first-party opt-out.
- **Fix:** `precompute_forecasts` calls `os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")` immediately before the lazy `import mlflow` / `start_run()` — opting into the locked file backend via MLflow's own env var (respecting an explicit user override). The architecture is unchanged: local file store, no server, no credentials, no network egress (T-05-06-MLF).
- **Files modified:** `pipelines/forecast/precompute.py`
- **Verification:** `test_track_true_logs_global_metrics_to_local_mlflow` sets a tmp `file://.../mlruns` tracking URI, runs the precompute, and asserts the `mlruns/` run dir exists and `mlflow.search_runs()` returns the logged `coverage_empirical` (0.75) + `mae_pts` + `confidence_level` param.
- **Committed in:** `4078df5` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing-critical units correctness, 1 blocking MLflow-3.x opt-in). **Impact on plan:** both are required for the plan's own acceptance criteria (records at the seed scale; a working local-file-backend MLflow run) and strengthen honesty (a real-scale band; the locked server-less tracking backend). No scope creep; no new dependencies; the module surface matches the plan's `must_haves.artifacts` and `key_links`.

## Issues Encountered
- **MLflow file-store maintenance-mode gate** (MLflow 3.14) — resolved via the first-party `MLFLOW_ALLOW_FILE_STORE` opt-out (Deviation 2); no architecture change.
- **Pre-existing (out of scope):** `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` still fails (`sentence-transformers is not installed`) — the documented ignorable embedder failure, unrelated to this plan. Not a regression: the suite went 429 → 442 passed (+13 new tests: 6 metrics + 7 precompute), 0 skipped, same single embedder failure throughout.

## User Setup Required
None — no external service configuration required. `global_metrics` + `precompute_forecasts` are offline code; xgboost/mapie/mlflow are already installed in `.venv`. The MLflow runs land under the default `mlruns/` local file store (no server, no credentials). The REAL live-panel precompute (real committed records + `mlruns/`) is the deferred 05-11 checkpoint.

## Next Phase Readiness
- The model→record bridge is built, offline-green, and importable: **05-10** (model card) can call `global_metrics` for the calibration/coverage numbers and layer PIT/SHAP on top of the same walk-forward output; **05-08** adds the regime/DRHP/anchor feature families on the same `build_features` `X` contract that `precompute_forecasts` consumes; **05-09** wires the four baselines + Diebold–Mariano gate and tunes `min_train`/`cal_frac` (the precompute already threads those through); **05-11** runs `precompute_forecasts` (+ `track=True`) over the REAL survivorship panel to regenerate the committed `data/forecasts/<id>.json` records and the committed `mlruns/` run.
- **FCAST-04 remains Pending** in REQUIREMENTS.md — the metrics + records are proven only over the synthetic fixture; do not close it until the real records/metrics are written at 05-11. **FCAST-01** is already marked Complete upstream and was left untouched.
- The 05-03 two-direction isolation audit stays green: `diagnostics.py` (pandas+stdlib) and `precompute.py` (lazy mlflow) are NOT scanned by the audit, and neither the loader `__init__` nor the model/feature modules were touched — the predictor still imports no display signal.

## Self-Check: PASSED

- Created files verified on disk: `pipelines/forecast/diagnostics.py`, `pipelines/forecast/precompute.py`, `tests/unit/test_forecast_metrics.py`, `tests/unit/test_forecast_precompute.py` — all FOUND.
- Task commits verified in git log: `5b05ec1` FOUND, `4078df5` FOUND.
- Plan verification re-run: `pytest tests/unit/test_forecast_metrics.py tests/unit/test_forecast_precompute.py -q` → 13 passed; with `test_forecast_isolation.py` → 24 passed (isolation audit still green); full `pytest tests/unit -q` → 442 passed / 0 skipped / 1 pre-existing ignorable embedder failure (no regression; 429 → 442 = +13 new tests).

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-19*
