---
phase: 05-calibrated-listing-day-forecaster
plan: 05
subsystem: forecast
tags: [xgboost, mapie, conformal, cqr, quantile-regression, walk-forward, as-of-t0, leakage, r2-alarm, adaptive-interval, fcast-01, fcast-03, d5-03, d5-11]

# Dependency graph
requires:
  - phase: 05-calibrated-listing-day-forecaster
    provides: "05-04 pipelines.features.build_features(panel) -> (X, available_at) leakage-gated design matrix + FEATURE_SPECS contract (the X this model consumes); 05-03 pipelines.forecast package (import-light loader __init__ the model wrappers live BESIDE, lazily imported) + the two-direction inspect.getsource isolation audit (model/walkforward reverse check now activates); 05-01 synthetic_panel/synthetic_features offline fixtures (the deterministic no-network test seam); pipelines.historical PANEL_COLUMNS + compute_listing_day_return (the target column semantics)"
provides:
  - "pipelines.forecast.model: make_quantile_models(X_tr, y_tr, params) -> [lower(0.1), upper(0.9), median(0.5)] reg:quantileerror XGBRegressors in MAPIE PREFIT list order; fit_cqr(models, X_cal, y_cal) -> ConformalizedQuantileRegressor(confidence_level=0.8, prefit=True).conformalize(...); predict_band(cqr, X) -> (median, low, high) with non-crossing rearrangement so high>=low; PARAMS default hyperparameters (small-N D5-07); xgboost/mapie imported LAZILY"
  - "pipelines.forecast.walkforward: walk_forward(panel, X, *, min_train, cal_frac, params) -> OOS DataFrame (one expanding-window as-of-T0 band per scorable IPO; pool = {listing_date < issue_date}, disjoint older-train/newer-calibration split, insufficient_history abstain below min_train or MIN_CAL) with per-fold no-lookahead provenance columns; r2_leakage_alarm(oos) -> (r2, flag|None) P4 gate; MIN_CAL/OOS_COLUMNS constants"
  - "tests/unit/test_cqr_interval.py — FCAST-01/D5-03 adaptive-width 80% interval proof; tests/unit/test_walkforward_no_lookahead.py — P4/D5-11 per-fold pool_max<T0 + disjoint-calibration proof + R²>0.5 alarm"
affects: [05-06, 05-08, 05-09, 05-10, 05-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MAPIE 1.x PREFIT conformalized-quantile path: train three XGBoost quantile models yourself, hand MAPIE the ORDERED [lower, upper, median] list with prefit=True, then conformalize on a disjoint calibration slice (XGBoost is NOT in MAPIE's non-prefit auto-clone list — prefit is mandatory)"
    - "Non-crossing quantile rearrangement (Chernozhukov+ 2010): per-row low=min/high=max of the two conformalized bounds guarantees high>=low under small-N quantile crossing while preserving adaptive width"
    - "Expanding-window as-of-T0 walk-forward: pool = {listing_date < issue_date}; split by listing-date quantile into older proper-train / newer calibration (both < T0_i, disjoint); one OOS band per IPO = displayed=backtested (D5-11), never KFold/shuffle"
    - "Per-fold PROVENANCE columns (t0/pool_max/train_max/cal_min/n_train/n_cal) make the no-lookahead invariant auditable against walk_forward's REAL selection (the test verifies the same code path, not a re-implementation)"
    - "(value, flag_or_None) alarm posture (mirrors validate.sanity_check_median): r2_leakage_alarm returns a plain-text string only when OOS median R²>0.5 — an automated P4 gate for the model card, not prose"
    - "Lazy modelling imports keep module load offline: xgboost/mapie/sklearn imported INSIDE functions so importing pipelines.forecast.* (and collecting the unit suite) never drags in the modelling stack"

key-files:
  created:
    - pipelines/forecast/model.py
    - pipelines/forecast/walkforward.py
    - tests/unit/test_cqr_interval.py
    - tests/unit/test_walkforward_no_lookahead.py
  modified: []

key-decisions:
  - "MAPIE 1.4.1 API matches the plan/RESEARCH exactly (ConformalizedQuantileRegressor(estimator, confidence_level, prefit) + conformalize(X,y) + predict_interval -> (points, intervals(n,2,1))) — verified live via inspect.signature; no downgrade, no reconciliation needed."
  - "predict_band applies a non-crossing REARRANGEMENT (Rule 2 correctness add): small-N XGBoost quantile models cross (MAPIE logs 'ill-sorted'), so raw intervals[:,0,0]/[:,1,0] can invert. Per-row min/max guarantees high>=low (the plan's acceptance criterion) while keeping the adaptive width."
  - "MIN_CAL guard (= ceil(2/(1-confidence_level)) = 10 for the 80% interval): MAPIE's predict_interval needs n_cal >= 1/tail = 10 to estimate the tail conformity quantile. A too-thin calibration slice ABSTAINS (insufficient_history) rather than crashing (Rule 3 blocking fix)."
  - "FCAST-01 and FCAST-03 left PENDING (not marked complete): the interval + walk-forward are proven OFFLINE on the 05-01 synthetic fixtures only; the per-IPO records over the real ~200-300-row panel land in 05-06/05-11. Closing them now would be dishonest (mirrors 05-02/03/04 leaving requirements Pending until every half lands)."
  - "walk_forward returns a superset of the plan's record columns: the core (drhp_id/issuer/actual/low/high/median/listing_year/abstain) PLUS per-fold provenance so the no-lookahead test is provable against the real selection. drhp_id/sector are carried through only when present (the synthetic panel has neither); listing_year is derived from listing_date."

patterns-established:
  - "Prefit-CQR wrapper: make_quantile_models -> fit_cqr -> predict_band is the single model seam the walk-forward loop and 05-06 precompute both call"
  - "Abstain-not-crash on thin calibration: the loop guards both min_train (prior count) and MIN_CAL (calibration-slice floor) and emits insufficient_history rather than fabricating or erroring"

requirements-completed: []

# Metrics
duration: ~8 min
completed: 2026-07-18
---

# Phase 5 Plan 05: XGBoost-Quantile + MAPIE CQR + As-of-T0 Walk-Forward Summary

**Built the phase's modeling keystone — a prefit XGBoost-quantile + MAPIE ConformalizedQuantileRegressor wrapper producing an adaptive-width 80% interval (D5-03), and an expanding-window as-of-T0 walk-forward loop that emits exactly one provably-lookahead-free out-of-sample band per IPO (displayed band = backtested band, D5-11) with an automated R²>0.5 leakage alarm (P4) — all proven offline against the 05-01 synthetic fixtures, with the 05-03 reverse isolation audit now fully active and green.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-07-18T21:50:01Z
- **Completed:** 2026-07-18T21:58:25Z
- **Tasks:** 2
- **Files modified:** 4 (4 created, 0 modified)

## Accomplishments
- `pipelines/forecast/model.py` — the mandatory MAPIE **prefit** path: `make_quantile_models` fits three `XGBRegressor(objective="reg:quantileerror", tree_method="hist")` at `quantile_alpha` 0.1/0.9/0.5 returned in MAPIE's `[lower, upper, median]` list order (NOT ascending); `fit_cqr` wraps them in `ConformalizedQuantileRegressor(confidence_level=0.8, prefit=True)` and `.conformalize`s on the disjoint calibration slice; `predict_band` returns `(median, low, high)` from `predict_interval` with a non-crossing rearrangement so `high >= low` always holds; xgboost/mapie imported lazily; the prefit-only anti-pattern documented in the module docstring.
- `pipelines/forecast/walkforward.py` — `walk_forward(panel, X)` orders scorable IPOs by `listing_date`, builds `pool = {listing_date < issue_date}` (T0 = issue-open, D5-01), splits it by listing-date quantile into an older proper-train and a newer calibration slice (both strictly < T0_i, disjoint), fits + conformalizes + predicts ONE out-of-sample band per IPO, and abstains (`insufficient_history`) below `min_train` or `MIN_CAL`; `r2_leakage_alarm` computes the OOS median R² and returns a plain-text alarm above 0.5 (P4).
- Two offline tests (10 cases total): `test_cqr_interval.py` proves the interval is adaptive-width and ordered + the model order/objective + the lazy-import posture; `test_walkforward_no_lookahead.py` proves — per fold, against the loop's own provenance columns — that `pool_max_listing_date < T0`, the calibration slice is disjoint from and newer than proper-train, thin-history IPOs abstain, and the R² alarm fires on a leak but stays quiet on the honest fixture.
- Activated the 05-03 two-direction isolation audit's previously-`importorskip`-guarded model/walkforward cases: both now run and pass (the predictor references no display signal — FCAST-02 Direction 2).

## Task Commits

Each task was committed atomically:

1. **Task 1: XGBoost-quantile + MAPIE CQR (prefit) wrapper** — `533b292` (feat)
2. **Task 2: Expanding-window as-of-T0 walk-forward loop + no-lookahead test + R²>0.5 alarm** — `eee4f80` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

_Note: MVP mode ON / TDD mode OFF per the execution brief — each task's module + its test were committed together in one atomic `feat` commit (no separate RED/GREEN commits)._

## Files Created/Modified
- `pipelines/forecast/model.py` (NEW) — `PARAMS`/`QUANTILE_ALPHAS`/`CONFIDENCE_LEVEL`; `make_quantile_models`, `fit_cqr`, `predict_band`; lazy xgboost/mapie; non-crossing rearrangement; prefit-only anti-pattern documented.
- `pipelines/forecast/walkforward.py` (NEW) — `MIN_TRAIN_DEFAULT`/`CAL_FRAC_DEFAULT`/`R2_LEAKAGE_THRESHOLD`/`MIN_CAL`/`OOS_COLUMNS`; `walk_forward` (expanding-window as-of-T0 loop + abstain) with per-fold provenance; `r2_leakage_alarm`; lazy sklearn.
- `tests/unit/test_cqr_interval.py` (NEW) — 4 tests: adaptive-width + high>=low, model order/objective, calibration disjointness, subprocess lazy-import proof.
- `tests/unit/test_walkforward_no_lookahead.py` (NEW) — 6 tests: per-fold pool_max<T0, disjoint cal>train, insufficient_history abstain, R² alarm fires-on-leak/quiet-on-honest, NaN-on-too-few-rows, subprocess lazy-import proof.

## Decisions Made
- **MAPIE 1.4.1 API confirmed to match the plan** (`ConformalizedQuantileRegressor(estimator, confidence_level, prefit)` + `conformalize(X, y)` + `predict_interval -> (points, intervals(n,2,1))`) via `inspect.signature` on the installed package — no downgrade and no API reconciliation were needed (the modeling constraint's escape hatch was not triggered).
- **`predict_band` rearranges the two bounds** (per-row `low=min`, `high=max`) — see Deviation 1.
- **`MIN_CAL` calibration-slice guard** derived from `confidence_level` — see Deviation 2.
- **FCAST-01 / FCAST-03 left Pending.** The model and walk-forward are proven only offline on the synthetic fixtures; the calibrated per-IPO records over the real survivorship panel are produced by 05-06 (precompute) + 05-11 (live build). Following the phase's established honesty posture (05-02 left FCAST-03 Pending, 05-03/05-04 left FCAST-02 Pending), neither is closed here.
- **`walk_forward` returns provenance columns** beyond the plan's record inputs so the no-lookahead test can verify the loop's actual pool/train/calibration boundaries rather than a re-implementation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Non-crossing rearrangement in `predict_band` to guarantee `high >= low`**
- **Found during:** Task 1 (CQR interval smoke test)
- **Issue:** The RESEARCH §Pattern 1 sketch reads the bounds as `low = intervals[:,0,0]` / `high = intervals[:,1,0]` directly. On a small sample the independently-trained 0.1 and 0.9 XGBoost quantile models CROSS (MAPIE logs "The predictions are ill-sorted"), so the raw upper bound can fall below the raw lower bound — violating the plan's acceptance criterion "`high >= low` everywhere."
- **Fix:** `predict_band` applies the standard non-crossing rearrangement (Chernozhukov, Fernández-Val & Galichon 2010): per-row `low = min(bound_a, bound_b)`, `high = max(bound_a, bound_b)`. This guarantees `high >= low` while preserving the ADAPTIVE (per-IPO-varying) width that is the whole point of D5-03.
- **Files modified:** `pipelines/forecast/model.py`
- **Verification:** `test_cqr_interval_is_adaptive_width_and_ordered` asserts `high >= low` on every held-out IPO AND `>= 2` distinct widths.
- **Committed in:** `533b292` (Task 1 commit)

**2. [Rule 3 - Blocking] `MIN_CAL` calibration-slice guard (abstain instead of MAPIE crash)**
- **Found during:** Task 2 (first walk-forward run)
- **Issue:** MAPIE's `predict_interval` for an 80% interval requires the calibration set to be large enough to estimate the tail (0.1) conformity quantile — `n_cal >= 1/0.1 = 10`. The plan's `min_train=60`/`cal_frac=0.25` yields `>= 10` in production, but the earliest expanding-window folds (and lighter test params) can produce a calibration slice of 8, which raises `ValueError: Number of samples of the score is too low`.
- **Fix:** Added `MIN_CAL = ceil(2/(1-confidence_level))` (= 10 for the 80% interval) and an abstain guard: a pool whose newest slice is thinner than `MIN_CAL` emits an `insufficient_history` abstain row (D5-09) rather than crashing or fabricating a band. This generalizes correctly if the confidence level ever changes.
- **Files modified:** `pipelines/forecast/walkforward.py`
- **Verification:** the full walk-forward over the fixture now runs cleanly with no MAPIE errors; abstain rows carry `insufficient_history` and no band.
- **Committed in:** `eee4f80` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing-critical correctness, 1 blocking). **Impact on plan:** Both are necessary to satisfy the plan's own acceptance criteria (`high >= low` everywhere; a working walk-forward over the fixture) and strengthen honesty (valid interval geometry; abstain-not-crash on thin calibration). No scope creep; no new dependencies; the module surface matches the plan's `must_haves.artifacts` and `key_links`.

## Issues Encountered
- **MAPIE "ill-sorted" INFO logs** are emitted during fitting on the tiny fixture (the quantile-crossing MAPIE detects). They are harmless (rearrangement handles the crossing) and do not affect pass/fail.
- **Pre-existing (out of scope):** `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` still fails with `RuntimeError: sentence-transformers is not installed` — the documented, ignorable embedder failure, unrelated to this plan. Not a regression: the suite went 417→429 passed (+10 new modeling tests, +2 previously-`importorskip`-skipped isolation cases now running/passing; skipped 2→0), same single embedder failure throughout.

## User Setup Required
None - no external service configuration required. The model + walk-forward are offline-only (consume the 05-04 feature matrix / the 05-01 synthetic fixture); xgboost/mapie/sklearn are already installed in `.venv`. The real live-panel fit remains the deferred 05-11 checkpoint step.

## Next Phase Readiness
- The prefit CQR wrapper + as-of-T0 walk-forward are built, offline-green, and importable. **05-06** can call `walk_forward(build_features(panel)...)` to compute the GLOBAL coverage/MAE/per-year-RMSE metrics (D5-12/FCAST-04) and precompute the per-IPO `data/forecasts/<id>.json` records the render reads; **05-08** adds the regime/DRHP/anchor feature families on top of the same `X` contract; **05-09** wires the four baselines + Diebold–Mariano gate and tunes `min_train`/`cal_frac` (D5-09) alongside the `r2_leakage_alarm` P4 gate; **05-10** builds the model card (calibration/PIT/SHAP) over the walk-forward output; **05-11** runs the whole chain over the real survivorship panel.
- **FCAST-01 and FCAST-03 remain Pending** in REQUIREMENTS.md — do not close them until the calibrated per-IPO records are written over the real panel (05-06/05-11). This plan delivered only the (offline-proven) modeling engine.
- The 05-03 two-direction isolation audit is now FULLY ACTIVE (no `importorskip` skips) and green: the predictor (`model.py` + `walkforward.py`) imports no display signal; the render imports no model module.

## Self-Check: PASSED

- Created files verified on disk: `pipelines/forecast/model.py`, `pipelines/forecast/walkforward.py`, `tests/unit/test_cqr_interval.py`, `tests/unit/test_walkforward_no_lookahead.py` — all FOUND.
- Task commits verified in git log: `533b292` FOUND, `eee4f80` FOUND.
- Plan verification re-run: `pytest tests/unit/test_cqr_interval.py tests/unit/test_walkforward_no_lookahead.py -q` → 10 passed; `pytest tests/unit/test_forecast_isolation.py -q` → 11 passed / 0 skipped (model + walkforward reverse audit active); full `pytest tests/unit -q` → 429 passed / 0 skipped / 1 pre-existing ignorable embedder failure (no regression).

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-18*
