"""
pipelines/forecast/reconcile.py — reconcile a committed forecast record's GLOBAL
metrics block to the live backtest (05-11 quick task).

The forecaster FAILED its P9 release gate, so the per-IPO records were intentionally
NOT regenerated — their bands stay the honest illustrative SEED interval and the
snapshot block leads with the P9-fail banner (D5-01 posture). But the GLOBAL metrics
block (coverage / MAE / per-year RMSE / n / backtest_window) is D5-12 "identical
across every page" and describes the MODEL's real tested behavior — so it must be the
live walk-forward numbers, or the "How this was tested" strip contradicts the model
card. This module recomputes that block from the committed live OOS frame and swaps
it into a record, preserving the band / abstain / model_version / everything-else
verbatim.

MODEL-side utility (imports ``global_metrics`` + the record schema); never imported
by the render side, so the FCAST-02 Direction-1 isolation audit is unaffected.
"""
from __future__ import annotations

import pandas as pd

from agent.forecast_schema import ForecastMetrics, ForecastRecord
from pipelines.forecast.diagnostics import global_metrics


def live_metrics(oos_df: pd.DataFrame) -> ForecastMetrics:
    """Build the D5-12 GLOBAL ``ForecastMetrics`` from the committed live OOS frame.

    Wraps ``diagnostics.global_metrics`` (coverage / MAE / per-year RMSE / n — the
    REAL held-out numbers, never clamped, P17) and derives ``backtest_window`` as the
    SPAN of the listing years actually attributed a per-year RMSE (min-max) — never a
    fabricated range. When no year is present the window is an honest em-dash.
    """
    gm = global_metrics(oos_df)
    years = sorted(int(y) for y in gm["per_year_rmse"])
    window = f"{years[0]}-{years[-1]}" if years else "—"
    return ForecastMetrics(
        coverage_empirical=gm["coverage_empirical"],
        mae_pts=gm["mae_pts"],
        backtest_window=window,
        n=gm["n"],
        per_year_rmse=dict(gm["per_year_rmse"]),
    )


def reconcile_record_metrics(
    record: ForecastRecord, metrics: ForecastMetrics
) -> ForecastRecord:
    """Return a copy of ``record`` with ONLY its global metrics block replaced.

    The ``interval`` (per-IPO band), ``abstain`` / ``abstain_reason``,
    ``model_version``, ``sector`` and every other field are preserved verbatim — the
    honest per-IPO band + abstain posture is intentionally kept (the forecaster failed
    its gate; no validated per-IPO band was regenerated, D5-01).
    """
    return record.model_copy(update={"metrics": metrics})


__all__ = ["live_metrics", "reconcile_record_metrics"]
