"""
pipelines/forecast/interpret.py — the production-model interpretability seam
(05-11 SHAP residual).

The as-of-T0 walk-forward trains a DIFFERENT model per expanding-window fold, so
there is no single "the model" to explain. For a global SHAP feature-attribution
plot the honest object is ONE median quantile regressor fit on the FULL available
panel (every row with a known target), using the production ``model.PARAMS`` — the
"if we shipped one model trained on everything to date, this is what it keys on"
model. That is explicitly DISTINCT from the held-out metrics (coverage / MAE / DM
gate), which stay the as-of-T0 walk-forward numbers; the model card labels the SHAP
plot as global interpretability so the two are never conflated.

``feature_population`` reports which lean features actually carry a value on a given
panel — the honest input to the model card's "populated live?" disclosure. On the
live NSE survivorship panel only ``trailing_listing_gain`` (regime family b, derived
from prior listings) is populated; the DRHP-structure (a/c), market-regime VIX/nifty
(b) and anchor (d) sources were deferred at the 05-11 live build, so those columns
are all-NaN — which is WHY the live model is humble and fails the P9 gate (D5-01).

ISOLATION: this is a MODEL-side module (it imports build/select/model). It carries
no display signal and is never imported by the render side (FCAST-02, Direction 2).
``xgboost`` stays lazily imported via ``model.make_quantile_models`` — importing this
module does not drag in the training stack until a fit is requested.
"""
from __future__ import annotations

import pandas as pd

from pipelines.features.build import build_features
from pipelines.features.select import SELECTED_FEATURES
from pipelines.forecast.model import make_quantile_models

# The target column the walk-forward regresses on (the listing-day return).
_TARGET = "listing_day_return"


def _lean_design_matrix(panel: pd.DataFrame) -> pd.DataFrame:
    """Build the leakage-gated feature matrix and restrict it to the lean set.

    Runs the SAME ``build_features`` T0 leakage gate the walk-forward uses, then
    selects exactly ``SELECTED_FEATURES`` (in that order). Missing sources stay
    NaN-retained (XGBoost treats NaN as native missing) — never fabricated.
    """
    x, _available_at = build_features(panel)
    return x.loc[:, list(SELECTED_FEATURES)]


def fit_median_model(panel: pd.DataFrame, *, params: dict | None = None):
    """Fit the production median quantile regressor on the full available panel.

    Args:
        panel: an assembled historical panel carrying ``issue_date`` (T0) and the
            ``listing_day_return`` target.
        params: optional overrides merged over the production ``model.PARAMS``
            (unit tests pass lighter trees; production passes ``None``).

    Returns:
        ``(median_model, X_fit)``:
          - ``median_model`` — the FITTED 0.5-quantile ``XGBRegressor`` (the median
            estimator of the ``[lower, upper, median]`` prefit list), trained on
            every row with a known target,
          - ``X_fit`` — the lean ``SELECTED_FEATURES`` design matrix for exactly
            those training rows (the data the model saw — the SHAP explanation set).
    """
    x_lean = _lean_design_matrix(panel)
    mask = panel[_TARGET].notna()
    x_fit = x_lean.loc[mask]
    y_fit = panel.loc[mask, _TARGET]

    # make_quantile_models returns [lower(0.1), upper(0.9), median(0.5)]; index 2 is
    # the median point model — the one a global feature-attribution plot explains.
    models = make_quantile_models(x_fit, y_fit, params)
    return models[2], x_fit


def feature_population(panel: pd.DataFrame) -> dict[str, bool]:
    """Report which lean features actually carry a value on ``panel`` (D5-11 honesty).

    Returns ``{feature: True/False}`` over ``SELECTED_FEATURES`` — True iff the built
    column has at least one non-NaN value. An all-NaN column (its source deferred /
    absent) is honestly False; the model card surfaces this as the "populated live?"
    disclosure so the schema-vs-populated gap is explicit.
    """
    x_lean = _lean_design_matrix(panel)
    return {feat: bool(x_lean[feat].notna().any()) for feat in SELECTED_FEATURES}


__all__ = ["fit_median_model", "feature_population"]
