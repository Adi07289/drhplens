"""
tests/unit/test_interpret.py — the production-model interpretability seam
(05-11 SHAP residual).

``fit_median_model`` fits the ONE production median quantile regressor on the full
available panel (all rows with a non-NaN target) over the lean ``SELECTED_FEATURES``
design matrix — the "if we shipped one model trained on everything to date" global
model the SHAP plot explains (distinct from the as-of-T0 walk-forward that produces
the held-out metrics). ``feature_population`` reports which lean features actually
carry a value on a given panel — the honest input to the model card's "populated
live?" disclosure (on the live NSE panel only ``trailing_listing_gain`` is
populated; the DRHP/regime/anchor families were deferred at 05-11).
"""
from __future__ import annotations

import numpy as np

from pipelines.features.select import SELECTED_FEATURES
from pipelines.forecast.interpret import feature_population, fit_median_model
from tests.unit.fixtures.forecast_fixtures import synthetic_panel

_LIGHT = {"n_estimators": 20, "max_depth": 2}  # keep the fit fast in unit tests


def test_fit_median_model_returns_fitted_median_over_lean_features():
    panel = synthetic_panel(n=60)
    model, X_fit = fit_median_model(panel, params=_LIGHT)

    # the design matrix is exactly the lean SELECTED_FEATURES, in that order
    assert list(X_fit.columns) == list(SELECTED_FEATURES)
    # one row per IPO with a known target (the training rows the model saw)
    assert len(X_fit) == int(panel["listing_day_return"].notna().sum())
    # it is a FITTED regressor — predicts one value per row
    preds = np.asarray(model.predict(np.asarray(X_fit, dtype=float)))
    assert preds.shape[0] == len(X_fit)


def test_feature_population_flags_unpopulated_lean_features():
    panel = synthetic_panel(n=60)
    pop = feature_population(panel)

    assert set(pop) == set(SELECTED_FEATURES)
    # regime family (b) is derived from PRIOR listings — populated on a bare panel
    assert pop["trailing_listing_gain"] is True
    # DRHP-structure (a/c) + anchor (d) have no source on a bare panel -> all-NaN
    assert pop["issue_size_cr"] is False
    assert pop["anchor_book_cr"] is False
