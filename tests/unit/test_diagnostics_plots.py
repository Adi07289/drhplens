"""
tests/unit/test_diagnostics_plots.py — the FCAST-03 committed-artifact builders
(05-10): calibration reliability diagram, PIT histogram, SHAP importance.

Each builder must write a NON-EMPTY PNG (headless Agg backend) and return the path,
built DETERMINISTICALLY from the shared offline fixtures so the artifacts are
reproducible. The honesty pins: the calibration annotation reports the REAL held-out
empirical coverage (never rounded to 0.80, P17); matplotlib / shap are imported
LAZILY (module import triggers no plotting / no display backend); the SHAP builder
falls back to ``feature_importances_`` when SHAP cannot explain the estimator.
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np

from pipelines.forecast.diagnostics import (
    calibration_plot,
    empirical_coverage,
    global_metrics,
    pit_histogram,
    shap_summary,
)
from pipelines.forecast.model import make_quantile_models
from tests.unit.fixtures.forecast_fixtures import (
    oos_rows,
    synthetic_features,
    synthetic_panel,
)

_LIGHT_PARAMS = {"n_estimators": 20, "max_depth": 2}


def _nonempty(path) -> bool:
    return path.exists() and path.stat().st_size > 0


def test_calibration_plot_writes_nonempty_png(tmp_path):
    out = calibration_plot(oos_rows(), tmp_path / "calibration.png")
    assert out == tmp_path / "calibration.png"
    assert _nonempty(out)


def test_calibration_annotation_reports_raw_coverage_not_rounded():
    """The calibration diagnostic annotates the REAL held-out 80% coverage — the
    same raw ``global_metrics`` number, NEVER clamped to the 0.80 target (P17)."""
    df = oos_rows()
    raw = global_metrics(df)["coverage_empirical"]
    # the fixture is authored so coverage is a realistic value strictly below 1.0
    assert 0.0 < raw < 1.0
    assert raw != 0.80  # honest raw number, not a rounded-to-target fiction
    # the plot's annotation seam IS that raw number (one shared coverage seam).
    assert empirical_coverage(df) == raw


def test_pit_histogram_writes_nonempty_png(tmp_path):
    out = pit_histogram(oos_rows(), tmp_path / "pit.png")
    assert out == tmp_path / "pit.png"
    assert _nonempty(out)


def test_shap_summary_writes_nonempty_png_from_fitted_model(tmp_path):
    panel = synthetic_panel(n=40)
    X = synthetic_features(panel)
    feat = X.drop(columns=["available_at"])
    y = panel["listing_day_return"].fillna(0.06)
    models = make_quantile_models(feat, y, _LIGHT_PARAMS)
    out = shap_summary(models[2], feat, tmp_path / "shap.png")  # median model
    assert _nonempty(out)


def test_shap_summary_falls_back_to_feature_importances(tmp_path):
    """A non-tree-explainable estimator carrying ``feature_importances_`` still
    produces the importance PNG (the fallback path)."""

    class _DummyModel:
        feature_importances_ = np.array([0.5, 0.3, 0.2, 0.0, 0.0])

    panel = synthetic_panel(n=12)
    feat = synthetic_features(panel).drop(columns=["available_at"])  # 5 columns
    out = shap_summary(_DummyModel(), feat, tmp_path / "shap_fallback.png")
    assert _nonempty(out)


def test_global_metrics_behavior_unchanged():
    """The 05-06 metrics-only function is untouched — raw coverage + no fabricated
    year still hold on the fixture."""
    m = global_metrics(oos_rows())
    assert set(m) == {"coverage_empirical", "mae_pts", "per_year_rmse", "mean_width", "n"}
    assert m["n"] > 0
    assert 0.0 <= m["coverage_empirical"] <= 1.0


def test_module_import_does_no_plotting_lazily():
    """Importing the diagnostics module must NOT drag in matplotlib.pyplot or shap
    (they are imported lazily inside the builders — offline / CI-safe at import)."""
    code = (
        "import sys; import pipelines.forecast.diagnostics as d; "
        "assert 'matplotlib.pyplot' not in sys.modules, 'pyplot imported at module load'; "
        "assert 'shap' not in sys.modules, 'shap imported at module load'; "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
