"""
pipelines/forecast/diagnostics.py — the GLOBAL walk-forward honesty metrics
(D5-12 / FCAST-04), computed ONCE over the out-of-sample walk-forward rows.

``global_metrics(oos_df)`` aggregates the per-IPO out-of-sample bands the
walk-forward emitted into the three model-wide numbers the forecast page shows on
EVERY IPO (identical across pages, D5-12): empirical coverage, mean absolute error,
and per-year RMSE — plus the mean band width and the scored-row count. These are
the "how this was tested" figures baked into every ``ForecastRecord.metrics`` block
(``agent.forecast_schema.ForecastMetrics``).

Honesty invariants (P17 — calibration theater is the pitfall this guards):
  * **Empirical coverage is the REAL held-out number** — ``mean((actual >= low) &
    (actual <= high))`` over the scored rows. It is NEVER clamped to the 0.80
    target; a coverage of 0.74 or 0.86 is reported as-is (P17). The only rounding
    applied is display precision (4 dp) which can never move a non-0.80 value TO
    0.80.
  * **Abstain rows contribute NOTHING** — an ``abstain=True`` row (no calibratable
    band) is excluded from coverage, MAE, RMSE, width and the count. A no-band row
    is not a 0%-error row; counting it would fabricate calibration quality.
  * **No fabricated year** — ``per_year_rmse`` is keyed only by the listing years
    actually present among the scored rows. A year with no scored IPO is simply
    absent, never a fabricated 0.0.

UNITS: the caller passes rows already in **percentage points** (e.g. a +6.1%
listing-day return is ``6.1``, not ``0.061``). The walk-forward emits the raw
FRACTION return, so ``pipelines.forecast.precompute`` multiplies by 100 at the
model→record boundary BEFORE calling this; the ``oos_rows`` test fixture is likewise
authored in percentage points. Coverage is scale-free; MAE / RMSE / width inherit
the caller's units (hence ``mae_pts`` — points).

This module is metrics-only for now; the calibration/PIT/SHAP diagnostic PLOTS land
in 05-10. It imports only pandas + stdlib (no sklearn, no modelling library) so
importing it stays offline and light.
"""
from __future__ import annotations

import pandas as pd

# The band columns every scored row must carry to contribute a statistic. A row
# missing any of these has no computable band and is dropped from the aggregate
# (an honest "not scored", never a fabricated zero-error contribution).
_BAND_COLUMNS = ("actual", "low", "high", "median")


def global_metrics(oos_df: pd.DataFrame) -> dict:
    """Aggregate the out-of-sample walk-forward rows into the GLOBAL metrics (D5-12).

    Args:
        oos_df: a walk-forward out-of-sample frame — one row per scored IPO with
            ``actual``, ``low``, ``high``, ``median`` (all in **percentage points**)
            and ``listing_year``, plus an optional ``abstain`` flag column. Abstain
            rows (and any row missing a band value) are excluded from every
            statistic.

    Returns:
        A dict with:
          - ``coverage_empirical`` — ``mean((actual >= low) & (actual <= high))``
            over the scored rows, the REAL held-out number (never clamped to 0.80,
            P17); ``float('nan')`` when there are no scored rows.
          - ``mae_pts`` — mean absolute error of the median vs the realized return,
            in points.
          - ``per_year_rmse`` — ``{str(year): rmse}`` of the median's RMSE grouped
            by listing year; keys are only the years actually present.
          - ``mean_width`` — mean band width ``high - low`` (points).
          - ``n`` — the number of scored (non-abstain, banded) rows.
    """
    scored = oos_df
    if "abstain" in scored.columns:
        scored = scored[~scored["abstain"].astype(bool)]
    scored = scored.dropna(subset=list(_BAND_COLUMNS))

    n = int(len(scored))
    if n == 0:
        # No scored rows — honestly empty, never a fabricated coverage/MAE.
        return {
            "coverage_empirical": float("nan"),
            "mae_pts": float("nan"),
            "per_year_rmse": {},
            "mean_width": float("nan"),
            "n": 0,
        }

    actual = scored["actual"].astype(float)
    low = scored["low"].astype(float)
    high = scored["high"].astype(float)
    median = scored["median"].astype(float)

    covered = (actual >= low) & (actual <= high)
    # RAW empirical coverage — the real held-out number (P17). Rounded only to 4 dp
    # for a diff-reviewable committed record; 4 dp can never move a non-0.80 value
    # to 0.80, so this is display precision, NOT target-clamping.
    coverage_empirical = round(float(covered.mean()), 4)
    mae_pts = round(float((actual - median).abs().mean()), 2)
    mean_width = round(float((high - low).mean()), 2)

    # Per-year RMSE of the median. Rows without a listing_year cannot be attributed
    # to a year and are dropped from THIS statistic only (never bucketed as a
    # fabricated year); coverage/MAE above still counted them.
    squared_error = (actual - median) ** 2
    year_frame = pd.DataFrame(
        {"listing_year": scored["listing_year"].to_numpy(), "se": squared_error.to_numpy()}
    ).dropna(subset=["listing_year"])
    per_year = year_frame.groupby("listing_year")["se"].mean().pow(0.5)
    per_year_rmse = {
        str(int(year)): round(float(rmse), 2) for year, rmse in per_year.items()
    }

    return {
        "coverage_empirical": coverage_empirical,
        "mae_pts": mae_pts,
        "per_year_rmse": per_year_rmse,
        "mean_width": mean_width,
        "n": n,
    }


__all__ = ["global_metrics"]
