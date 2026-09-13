"""The card_plots.json sidecar: calibration points, PIT bins, SHAP importances — built
deterministically from the committed OOS frame + the fitted median model."""
from __future__ import annotations

from scripts.regenerate_model_card import build_card_plots
from tests.unit.fixtures.forecast_fixtures import oos_rows, synthetic_panel


def test_build_card_plots_shape():
    doc = build_card_plots(synthetic_panel(), oos_rows())
    assert isinstance(doc["calibration"], list) and doc["calibration"]
    assert set(doc["calibration"][0]) == {"nominal", "empirical"}
    assert set(doc["pit"]) == {"counts", "uniform_level", "bins"}
    assert len(doc["pit"]["counts"]) == 10
    assert isinstance(doc["shap"], list) and set(doc["shap"][0]) == {"feature", "mean_abs"}
