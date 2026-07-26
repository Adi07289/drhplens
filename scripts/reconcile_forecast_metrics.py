"""
scripts/reconcile_forecast_metrics.py — reconcile the committed forecast records'
GLOBAL metrics block to the live 05-11 backtest.

The per-IPO forecast block on /snapshot rendered SEED global metrics (coverage
0.783, n=247, window 2016-2025) while /methodology shows the live run and the block
leads with the live P9-fail banner. The GLOBAL metrics are D5-12 "identical across
every page" and describe the model's REAL tested behavior, so they must be the live
walk-forward numbers. This script recomputes that block from the committed live OOS
frame and swaps it into each committed record, preserving the band / abstain /
model_version verbatim (the per-IPO band stays the honest illustrative seed — the
forecaster failed its gate, so no validated per-IPO band was regenerated, D5-01).

Deterministic + re-runnable. Writes via ``ForecastRecord.to_json()`` (the same
serializer precompute uses) + the records' trailing newline, so the diff is exactly
the metrics block — nothing else.

Usage:  PYTHONPATH=. .venv/bin/python scripts/reconcile_forecast_metrics.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipelines.forecast import load_forecast
from pipelines.forecast.reconcile import live_metrics, reconcile_record_metrics

_REPO = Path(__file__).resolve().parents[1]
_OOS = _REPO / "data" / "forecasts" / "_gate" / "oos_real.parquet"
_FORECASTS = _REPO / "data" / "forecasts"

# The committed catalogue records that carry a metrics block (covered + abstain).
_RECORDS = ("swiggy_2024_11", "hyundai_2024_10")


def main() -> None:
    if not _OOS.is_file():
        raise SystemExit(f"live OOS frame missing: {_OOS} — run the 05-11 crawl first.")

    oos = pd.read_parquet(_OOS)
    lm = live_metrics(oos)

    for drhp_id in _RECORDS:
        path = _FORECASTS / f"{drhp_id}.json"
        if not path.is_file():
            print(f"skip {drhp_id}: no committed record at {path}")
            continue
        reconciled = reconcile_record_metrics(load_forecast(drhp_id), lm)
        path.write_text(reconciled.to_json() + "\n", encoding="utf-8")
        print(
            f"reconciled {drhp_id}: coverage={lm.coverage_empirical} "
            f"mae={lm.mae_pts} n={lm.n} window={lm.backtest_window} "
            f"(band + abstain preserved)"
        )


if __name__ == "__main__":
    main()
