"""
Unit test — ForecastRecord round-trips its calibrated band + GLOBAL walk-forward
metrics byte-stably, and treats COVERED (abstain=False, a real interval) and
ABSTAIN (abstain=True, interval None, no fabricated numbers) as FIRST-CLASS
states — never a fabricated band, never a fabricated metric.

Requirement: FCAST-01 (calibrated listing-day forecast record + honest abstain).
This mirrors the codec + first-class-state grammar of tests/unit/test_gmp_schema.py
and pins Task 1's schema contract NOW.

Isolation (FCAST-02) is pinned separately in tests/unit/test_forecast_isolation.py;
one lightweight import-audit is duplicated here so Task 1 is independently green.
"""
from __future__ import annotations

import inspect
import json

import agent.forecast_schema
from agent.forecast_schema import ForecastInterval, ForecastMetrics, ForecastRecord

_GLOBAL_METRICS = {
    "coverage_empirical": 0.783,
    "mae_pts": 11.4,
    "backtest_window": "2016-2025",
    "n": 247,
    "per_year_rmse": {
        "2016": 14.1,
        "2017": 12.8,
        "2018": 15.6,
        "2019": 13.2,
        "2020": 18.9,
        "2021": 21.4,
        "2022": 16.7,
        "2023": 12.1,
        "2024": 11.9,
        "2025": 13.5,
    },
}

_ABSTAIN_REASONS = {"insufficient_history", "out_of_support", "interval_too_wide"}


def _full_render_record() -> ForecastRecord:
    """A COVERED ForecastRecord carrying a real out-of-sample band (the swiggy seed)."""
    return ForecastRecord(
        drhp_id="swiggy_2024_11",
        computed_at="2026-07-15T00:00:00Z",
        model_version="cqr-xgb-seed-2026.07",
        as_of_listing_date="2024-11-13",
        out_of_sample=True,
        walk_forward=True,
        abstain=False,
        abstain_reason=None,
        interval=ForecastInterval(
            low_pct=-4.2, high_pct=21.7, median_pct=6.1, width_pts=25.9
        ),
        sector="Other",
        metrics=ForecastMetrics(**_GLOBAL_METRICS),
    )


def _abstain_record() -> ForecastRecord:
    """An ABSTAIN ForecastRecord — no band, honest reason, no fabricated numbers."""
    return ForecastRecord(
        drhp_id="hyundai_2024_10",
        computed_at="2026-07-15T00:00:00Z",
        model_version="cqr-xgb-seed-2026.07",
        as_of_listing_date="2024-10-22",
        out_of_sample=True,
        walk_forward=True,
        abstain=True,
        abstain_reason="insufficient_history",
        interval=None,
        sector="Automobiles",
        metrics=ForecastMetrics(**_GLOBAL_METRICS),
    )


def test_covered_record_roundtrips_byte_stable() -> None:
    """A covered ForecastRecord survives from_json(to_json()) equal AND byte-stable
    (indent=2, ensure_ascii=False) — the calibrated band + GLOBAL metrics intact."""
    rec = _full_render_record()
    text = rec.to_json()
    restored = ForecastRecord.from_json(text)

    assert restored == rec  # every field reconstructs equal
    assert restored.to_json() == text  # byte-stable re-serialization


def test_covered_record_exposes_interval_and_global_metrics() -> None:
    """A covered record surfaces interval.low_pct/high_pct/median_pct/width_pts and
    the GLOBAL metrics block (coverage_empirical/mae_pts/backtest_window/n/
    per_year_rmse)."""
    rec = ForecastRecord.from_json(_full_render_record().to_json())

    assert rec.is_abstain is False
    assert rec.interval is not None
    assert rec.interval.low_pct == -4.2
    assert rec.interval.high_pct == 21.7
    assert rec.interval.median_pct == 6.1
    assert rec.interval.width_pts == 25.9

    assert rec.metrics.coverage_empirical == 0.783
    assert rec.metrics.mae_pts == 11.4
    assert rec.metrics.backtest_window == "2016-2025"
    assert rec.metrics.n == 247
    assert rec.metrics.per_year_rmse["2020"] == 18.9


def test_abstain_record_is_first_class_no_fabricated_interval() -> None:
    """abstain=True is a FIRST-CLASS state: is_abstain is True, interval is None
    (no fabricated band), abstain_reason is in the locked domain — yet the GLOBAL
    metrics still round-trip (honest backtest numbers)."""
    rec = _abstain_record()
    restored = ForecastRecord.from_json(rec.to_json())

    assert restored.is_abstain is True
    assert restored.abstain is True
    assert restored.interval is None  # no fabricated numbers
    assert restored.abstain_reason in _ABSTAIN_REASONS
    # the honest backtest metrics survive even on an abstain record
    assert restored.metrics.n == 247
    assert restored.to_dict()["interval"] is None


def test_abstain_reason_domain_is_the_locked_set() -> None:
    """abstain_reason on an abstain record is one of the three locked reasons
    (insufficient_history | out_of_support | interval_too_wide)."""
    for reason in _ABSTAIN_REASONS:
        rec = ForecastRecord.from_json(
            ForecastRecord(
                drhp_id="hyundai_2024_10",
                computed_at="2026-07-15T00:00:00Z",
                model_version="cqr-xgb-seed-2026.07",
                as_of_listing_date="2024-10-22",
                out_of_sample=True,
                walk_forward=True,
                abstain=True,
                abstain_reason=reason,
                interval=None,
                sector="Automobiles",
                metrics=ForecastMetrics(**_GLOBAL_METRICS),
            ).to_json()
        )
        assert rec.abstain_reason == reason
        assert rec.interval is None


def test_median_pct_is_a_plain_field_not_a_headline() -> None:
    """median_pct is a PLAIN field (UI-SPEC P21): present and accessible on the
    interval, but it is not promoted — the honest headline is the RANGE. The test
    pins that it survives the codec as a plain value."""
    rec = ForecastRecord.from_json(_full_render_record().to_json())
    assert rec.interval is not None
    assert rec.interval.median_pct == 6.1
    # it round-trips inside the interval dict, alongside (not above) the band
    assert rec.to_dict()["interval"]["median_pct"] == 6.1


def test_to_dict_layout_is_flat_and_diff_reviewable() -> None:
    """to_dict emits the flat on-disk key set in stable order; to_json is indent=2
    for a diff-reviewable committed cache."""
    rec = _full_render_record()
    d = rec.to_dict()

    assert list(d.keys()) == [
        "drhp_id",
        "computed_at",
        "model_version",
        "as_of_listing_date",
        "out_of_sample",
        "walk_forward",
        "abstain",
        "abstain_reason",
        "interval",
        "sector",
        "metrics",
    ]
    assert set(d["interval"].keys()) == {
        "low_pct",
        "high_pct",
        "median_pct",
        "width_pts",
    }
    assert set(d["metrics"].keys()) == {
        "coverage_empirical",
        "mae_pts",
        "backtest_window",
        "n",
        "per_year_rmse",
    }
    # indent=2 committed-cache formatting
    text = rec.to_json()
    assert "\n  " in text
    assert json.loads(text)["drhp_id"] == "swiggy_2024_11"


def test_schema_imports_no_model_code() -> None:
    """agent/forecast_schema.py is the import-light RECORD boundary (FCAST-02):
    its source references NONE of the modelling libraries or downstream/display
    modules — it is pydantic + stdlib only (Task 1 acceptance criterion)."""
    src = inspect.getsource(agent.forecast_schema)
    forbidden = (
        "xgboost",
        "mapie",
        "sklearn",
        "shap",
        "pipelines.forecast",
        "pipelines.features",
        "pipelines.historical",
        "gmp",
    )
    for token in forbidden:
        assert token not in src, (
            f"agent/forecast_schema.py must not reference {token!r} "
            f"(FCAST-02: the record is the import-light isolation boundary between "
            f"the offline model and the cache-only render)."
        )
