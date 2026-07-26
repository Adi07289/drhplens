---
quick_id: "260727-reconcile-forecast-metrics"
status: complete
completed: 2026-07-27
---

# Summary: reconcile forecast records' global metrics to the live backtest

## What changed
The committed forecast records showed SEED global metrics on `/snapshot` (coverage
0.783, n=247, window 2016-2025) while `/methodology` shows the live backtest. Swapped
ONLY the global-metrics block of both records to the live walk-forward numbers, so the
"How this was tested" strip matches the model card. Band + abstain posture preserved.

## Deliverables
- `pipelines/forecast/reconcile.py` (TDD) — `live_metrics(oos_df) -> ForecastMetrics`
  (global_metrics + a `backtest_window` derived as the scored-year span) and
  `reconcile_record_metrics(record, metrics)` (replaces ONLY the metrics block via
  `model_copy`; band/abstain/model_version/sector preserved). Model-side; render
  isolation (FCAST-02) unaffected.
- `scripts/reconcile_forecast_metrics.py` — deterministic, re-runnable; writes via
  `ForecastRecord.to_json() + "\n"` so the diff is exactly the metrics block.
- `tests/unit/test_reconcile_forecast_metrics.py` (+2) — live_metrics matches
  global_metrics + year span; reconcile preserves band/abstain/version.
- Regenerated `data/forecasts/{swiggy_2024_11,hyundai_2024_10}.json`: coverage
  0.783→0.8004, mae 11.4→0.43, n 247→1132, window 2016-2025→2003-2026, per-year RMSE
  → live.
- Updated 2 stale seed-value assertions (`test_forecast_block_render.py` 78.3%→80.0%
  + years; `test_forecast_isolation.py` n 247→1132). Band assertion (low_pct -4.2)
  kept — band preserved.

## Verification (fresh)
- Full unit suite: **525 passed, 1 skipped, 0 failed**.
- Live app: `/snapshot?drhp_id=swiggy_2024_11` "How this was tested" strip now shows
  `80.0%` · MAE `0.4` · `2003-2026 · n = 1132` + live per-year RMSE; no seed values
  (78.3 / 247 / 2016). Screenshot: `/tmp/snap_forecast_reconciled.png`.

## Notes / out of scope
- `model_version` stays `cqr-xgb-seed-2026.07` (per the explicit "only the metrics
  block" scope). The record is now a deliberate hybrid: honest illustrative SEED band
  (the forecaster failed its P9 gate, so no validated per-IPO band was regenerated,
  D5-01) + live GLOBAL metrics + the live P9-fail banner leading the block. The
  seed band (25.9 pts wide) reads large next to the live MAE (0.4 pts) — that gap is
  covered by the "not a validated call" banner; flag for the user if a live per-IPO
  band is wanted later.
- STATE.md "Quick Tasks Completed" row deferred to prompt #6 (STATE.md is mid-
  reconciliation; that prompt owns all STATE updates).
