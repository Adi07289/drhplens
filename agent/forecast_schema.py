"""
agent/forecast_schema.py — ForecastRecord, the Phase 5 listing-day-forecast cache
schema (FCAST-01).

A ForecastRecord is the FLAT, cache-only ISOLATION BOUNDARY between the offline
forecaster and the cache-only Streamlit render (FCAST-02). It carries one IPO's
out-of-sample calibrated band plus the GLOBAL walk-forward metrics block, and it
imports ONLY pydantic + stdlib — no modelling library, no downstream pipeline.
The render reads this record (from data/forecasts/<drhp_id>.json) and NEVER
touches the model; the model writes this record and NEVER touches the render.

Three states are FIRST-CLASS, not error/edge cases (the honesty invariant, D5-09):
  - COVERED (abstain == False) — a real out-of-sample band exists: `interval`
    carries low_pct/high_pct/median_pct/width_pts and `metrics` carries the
    GLOBAL backtest numbers.
  - ABSTAIN (abstain == True) — not enough comparable history to calibrate an
    honest range. `interval` is None and NO interval number is fabricated;
    `abstain_reason` is one of {"insufficient_history", "out_of_support",
    "interval_too_wide"}. Surfaced by the render as the locked "not enough
    comparable history to calibrate an honest range" note (no band).
  - MISSING (no file on disk) — handled by the cache reader as FileNotFoundError,
    which the render maps to "no calibrated forecast available yet." This state is
    the ABSENCE of a record, so it is modelled outside the record itself.

median_pct is a PLAIN field (UI-SPEC P21): it is provenance/diagnostic detail,
never the record's headline. The honest headline is the calibrated RANGE
(low_pct..high_pct), not a point median — the schema keeps median_pct available
but the render must not promote it to a single-number prediction.

ISOLATION (FCAST-02): this module imports ONLY pydantic + stdlib. It pulls in NO
modelling library and NO prediction/feature/historical pipeline, and carries no
display-signal fields. The invariant is pinned in BOTH directions by
tests/unit/test_forecast_isolation.py (an inspect.getsource substring audit that
mirrors the Phase 4 display-isolation test): the render imports no model module,
and the predictor imports no display signal.

On-disk form (data/forecasts/<drhp_id>.json), a covered record:
  drhp_id, computed_at, model_version, as_of_listing_date, out_of_sample,
  walk_forward, abstain, abstain_reason, interval{low_pct,high_pct,median_pct,
  width_pts}, sector, metrics{coverage_empirical,mae_pts,backtest_window,n,
  per_year_rmse}. An abstain record is the identical layout with interval: null
  and abstain: true. This module does NOT create the directory and does NOT
  interpolate any untrusted id into a path — the cache reader gates <drhp_id>
  through the catalogue allow-list (is_known_drhp_id) BEFORE forming any path
  (T-05-03-PATH).
"""
from __future__ import annotations

import json

from pydantic import BaseModel


class ForecastInterval(BaseModel):
    """The per-IPO out-of-sample calibrated band (all percent / points, floats).

    low_pct/high_pct: the calibrated lower/upper listing-day-return bounds (%).
    median_pct: the central estimate (%). A PLAIN field only — UI-SPEC P21: never
        the record's headline. The honest headline is the RANGE, not this point.
    width_pts: high_pct - low_pct, the band width in percentage points (the
        honesty width — a wide band is an honest "we are uncertain").

    Only ever present on a COVERED record; an abstain record carries interval=None
    and fabricates none of these numbers.
    """

    low_pct: float
    high_pct: float
    median_pct: float
    width_pts: float


class ForecastMetrics(BaseModel):
    """The GLOBAL walk-forward backtest metrics block (D5-12).

    These are model-wide numbers, IDENTICAL across every IPO's record (they
    describe the backtested forecaster, not this one IPO). They are surfaced on
    both covered and abstain records — an abstain record still honestly reports
    how the forecaster scored in backtest even though it declines a band here.

    coverage_empirical: the empirical coverage of the calibrated band in
        walk-forward backtest (target ~0.80; the honest gap from target is shown).
    mae_pts: mean absolute error of the central estimate (percentage points).
    backtest_window: the ISO year span backtested, e.g. "2016-2025".
    n: the number of out-of-sample IPOs in the backtest.
    per_year_rmse: RMSE (percentage points) keyed by ISO year string.
    """

    coverage_empirical: float
    mae_pts: float
    backtest_window: str
    n: int
    per_year_rmse: dict[str, float]


class ForecastRecord(BaseModel):
    """The pre-computed listing-day-forecast cache record for one drhp_id.

    The single, flat, import-light seam between the offline forecaster and the
    cache-only render (FCAST-02). Covered and abstain are FIRST-CLASS states:
      - covered (abstain=False): interval is a ForecastInterval.
      - abstain (abstain=True): interval is None, abstain_reason names why — never
        a fabricated band.

    drhp_id: the catalogue id this forecast is for (the cache key).
    computed_at: ISO-8601 UTC stamp of when the record was written.
    model_version: pins the model + feature-set version that produced the band
        (provenance for D5-11 reproducibility).
    as_of_listing_date: the T0 listing date the forecast was made as-of
        (walk-forward provenance — no post-T0 information may inform the band).
    out_of_sample: True iff the band is a genuine out-of-sample prediction.
    walk_forward: True iff produced under the walk-forward (as-of-T0) protocol.
    abstain: True on the honest abstain state (no calibratable band).
    abstain_reason: one of {"insufficient_history","out_of_support",
        "interval_too_wide"} when abstain is True; None otherwise.
    interval: the ForecastInterval on a covered record; None on abstain.
    sector: the pooled sector label used for calibration (D5-10).
    metrics: the GLOBAL walk-forward metrics block (identical across IPOs, D5-12).
    """

    drhp_id: str
    computed_at: str
    model_version: str
    as_of_listing_date: str
    out_of_sample: bool
    walk_forward: bool
    abstain: bool
    abstain_reason: str | None = None
    interval: ForecastInterval | None = None
    sector: str
    metrics: ForecastMetrics

    @property
    def is_abstain(self) -> bool:
        """True on the honest abstain state — no calibratable band was produced."""
        return self.abstain

    def to_dict(self) -> dict:
        """Serialize to the flat on-disk dict layout (stable key order).

        A covered record emits a nested `interval` dict; an abstain record emits
        `interval: None` (never a fabricated band). The GLOBAL `metrics` block is
        always emitted.
        """
        return {
            "drhp_id": self.drhp_id,
            "computed_at": self.computed_at,
            "model_version": self.model_version,
            "as_of_listing_date": self.as_of_listing_date,
            "out_of_sample": self.out_of_sample,
            "walk_forward": self.walk_forward,
            "abstain": self.abstain,
            "abstain_reason": self.abstain_reason,
            "interval": (
                None
                if self.interval is None
                else {
                    "low_pct": self.interval.low_pct,
                    "high_pct": self.interval.high_pct,
                    "median_pct": self.interval.median_pct,
                    "width_pts": self.interval.width_pts,
                }
            ),
            "sector": self.sector,
            "metrics": {
                "coverage_empirical": self.metrics.coverage_empirical,
                "mae_pts": self.metrics.mae_pts,
                "backtest_window": self.metrics.backtest_window,
                "n": self.metrics.n,
                "per_year_rmse": dict(self.metrics.per_year_rmse),
            },
        }

    def to_json(self) -> str:
        """Serialize to a JSON string (indent=2 — diff-reviewable committed cache)."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, raw: dict) -> "ForecastRecord":
        """Reconstruct a ForecastRecord from the on-disk dict layout."""
        raw_interval = raw.get("interval")
        interval = (
            None if raw_interval is None else ForecastInterval.model_validate(raw_interval)
        )
        return cls(
            drhp_id=raw["drhp_id"],
            computed_at=raw["computed_at"],
            model_version=raw["model_version"],
            as_of_listing_date=raw["as_of_listing_date"],
            out_of_sample=raw["out_of_sample"],
            walk_forward=raw["walk_forward"],
            abstain=raw["abstain"],
            abstain_reason=raw.get("abstain_reason"),
            interval=interval,
            sector=raw["sector"],
            metrics=ForecastMetrics.model_validate(raw["metrics"]),
        )

    @classmethod
    def from_json(cls, text: str) -> "ForecastRecord":
        """Reconstruct a ForecastRecord from a JSON string."""
        return cls.from_dict(json.loads(text))
