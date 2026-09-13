"""Export siblings of the plot builders — same math, returned as JSON-able data so
the web can render native charts. Grid-derived (A8); honesty pins mirror the plot tests."""
from __future__ import annotations

from unittest import mock

import numpy as np

import pipelines.forecast.diagnostics as diag
from pipelines.forecast.diagnostics import (
    QUANTILE_GRID,
    _calibration_curve,
    _pit_array,
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


# --- PNG <-> data parity: the exports are thin serializers over shared seams, and
# the PNG builders consume the SAME seams, so the committed card_plots.json can never
# silently desync from calibration.png / pit.png (mirrors _lean_importances/SHAP). ---


def test_calibration_points_is_thin_serializer_over_shared_curve():
    df = oos_rows()
    nominal, empirical = _calibration_curve(df)
    pts = calibration_points(df)
    assert len(pts) == len(nominal) == len(QUANTILE_GRID)
    for p, n, e in zip(pts, nominal, empirical):
        assert p["nominal"] == round(float(n), 4)
        assert p["empirical"] == round(float(e), 4)


def test_pit_bins_is_thin_serializer_over_shared_pit_array():
    df = oos_rows()
    pit = _pit_array(df)
    b = pit_bins(df)
    counts, _ = np.histogram(pit, bins=10, range=(0.0, 1.0))
    assert b["counts"] == [int(c) for c in counts]
    assert b["uniform_level"] == round(float(pit.size / 10), 4)
    assert b["bins"] == 10
    assert sum(b["counts"]) == pit.size


def test_calibration_plot_consumes_the_shared_curve(tmp_path):
    """The PNG builder derives its curve from the SAME helper the export serializes —
    re-inlining the math into the plot builder (a desync risk) fails this."""
    with mock.patch.object(
        diag, "_calibration_curve", wraps=diag._calibration_curve
    ) as spy:
        diag.calibration_plot(oos_rows(), tmp_path / "cal.png")
    spy.assert_called_once()


def test_pit_histogram_consumes_the_shared_pit_array(tmp_path):
    """The PNG builder histograms the SAME finite PIT values the export bins."""
    with mock.patch.object(diag, "_pit_array", wraps=diag._pit_array) as spy:
        diag.pit_histogram(oos_rows(), tmp_path / "pit.png")
    spy.assert_called_once()
