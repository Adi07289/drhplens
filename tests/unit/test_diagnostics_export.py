"""Export siblings of the plot builders — same math, returned as JSON-able data so
the web can render native charts. Grid-derived (A8); honesty pins mirror the plot tests."""
from __future__ import annotations

from pipelines.forecast.diagnostics import (
    QUANTILE_GRID,
    calibration_points,
    pit_bins,
    shap_importances,
)
from pipelines.forecast.model import make_quantile_models
from tests.unit.fixtures.forecast_fixtures import oos_rows, synthetic_features, synthetic_panel

_LIGHT_PARAMS = {"n_estimators": 20, "max_depth": 2}


def test_calibration_points_pairs_nominal_and_empirical():
    pts = calibration_points(oos_rows())
    assert len(pts) == len(QUANTILE_GRID)
    assert pts[0]["nominal"] == round(float(QUANTILE_GRID[0]), 4)
    for p in pts:
        assert 0.0 <= p["empirical"] <= 1.0


def test_pit_bins_counts_sum_to_scored_n_and_uniform_is_mean():
    b = pit_bins(oos_rows())
    assert b["bins"] == 10
    assert len(b["counts"]) == 10
    total = sum(b["counts"])
    assert total > 0
    assert abs(b["uniform_level"] - total / 10) < 1e-6


def test_shap_importances_sorted_desc_and_covers_features():
    # NOTE: make_quantile_models(X_tr, y_tr, params) needs a fitted feature matrix +
    # target (not a raw panel), and returns [lower, upper, median] positionally (not
    # a dict keyed by quantile) — mirrors tests/unit/test_diagnostics_plots.py's
    # test_shap_summary_writes_nonempty_png_from_fitted_model fixture usage.
    panel = synthetic_panel(n=40)
    X = synthetic_features(panel)
    feat = X.drop(columns=["available_at"])
    y = panel["listing_day_return"].fillna(0.06)
    models = make_quantile_models(feat, y, _LIGHT_PARAMS)
    imps = shap_importances(models[2], feat, feature_names=list(feat.columns))  # median model
    assert imps, "expected at least one feature importance"
    vals = [r["mean_abs"] for r in imps]
    assert vals == sorted(vals, reverse=True)
    assert all("feature" in r and isinstance(r["mean_abs"], float) for r in imps)
    assert {r["feature"] for r in imps} == set(feat.columns)
