"""
pipelines/forecast/model.py — the XGBoost-quantile + MAPIE conformalized-quantile
wrapper (the D5-03 adaptive-width 80% interval), built via the MANDATORY prefit path.

Three XGBoost quantile regressors (``objective="reg:quantileerror"`` at
``quantile_alpha`` 0.1 / 0.9 / 0.5) are trained on the proper-train slice, then
wrapped in a MAPIE ``ConformalizedQuantileRegressor(prefit=True)`` and calibrated
(``conformalize``) on a disjoint, still-pre-T0 slice. The result is an interval
whose WIDTH VARIES per IPO (adaptive / heteroscedastic — the whole point of D5-03;
constant-width split-conformal was rejected).

Why prefit (the single load-bearing wiring detail)
--------------------------------------------------
MAPIE's *non-prefit* conformalized-quantile path only auto-clones a small set of
sklearn-family quantile estimators (``QuantileRegressor`` / ``GradientBoosting`` /
``HistGradientBoosting`` / ``LGBMRegressor``). **XGBoost is NOT on that list**, so
we MUST train the three quantile models ourselves and hand MAPIE an ORDERED list
``[lower, upper, median]`` with ``prefit=True``.

ANTI-PATTERN (never do this): passing a *single* ``XGBRegressor`` to
``ConformalizedQuantileRegressor(prefit=False)`` — MAPIE cannot clone-and-set the
quantile level for an XGBoost estimator, so it will fail or silently misbehave.
Always use the prefit path with the ordered three-model list below.

Estimator-list order (MAPIE prefit contract): ``[lower(0.1), upper(0.9), median(0.5)]``
— NOT ascending. ``confidence_level=0.8`` ⇒ the underlying nominal quantiles are
0.1 / 0.5 / 0.9 (a marginal 80% interval).

NO NETWORK / NO MODEL AT IMPORT
-------------------------------
``xgboost`` and ``mapie`` are imported LAZILY, *inside* the functions — importing
this module (or collecting the unit suite) never drags in the modelling stack, and
the sibling loader package ``pipelines/forecast/__init__.py`` stays import-light.
Module-level imports here are stdlib + numpy only.

Quantile crossing (why ``predict_band`` rearranges)
---------------------------------------------------
Independently-trained quantile regressors can *cross* (the 0.9 model predicting
below the 0.1 model) on small samples — MAPIE logs "The predictions are ill-sorted"
when it happens. ``predict_band`` applies the standard non-crossing REARRANGEMENT
(Chernozhukov, Fernández-Val & Galichon 2010: a monotone rearrangement of an
estimated quantile curve cannot increase estimation error) — a per-row
``low = min(bound_a, bound_b)`` / ``high = max(bound_a, bound_b)`` — so the returned
interval always satisfies ``high >= low`` while its adaptive width is preserved.

ISOLATION (FCAST-02, Direction 2): this module references NOTHING from the display
signal — the model never sees it. Pinned by tests/unit/test_forecast_isolation.py.
"""
from __future__ import annotations

from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Default hyperparameters (D5-07 lean/interpretable + small-N)
# ---------------------------------------------------------------------------
# Tuned for the ~200-300-row verified panel (D5-05): SHALLOW trees (max_depth=3),
# a modest ensemble, gentle learning rate, and per-tree/row subsampling to curb
# overfitting on a small, noisy, pre-apply (no-demand) signal. These are honest
# defaults, not p-hacked to beat a baseline (P9); the model is expected to be
# humble (a high R² is a leakage red flag, P4). Callers (e.g. the walk-forward
# loop, tests) may override any of these via the ``params`` argument.
PARAMS: dict[str, Any] = {
    "n_estimators": 200,
    "max_depth": 3,
    "learning_rate": 0.05,
    "min_child_weight": 5,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "random_state": 0,
    "n_jobs": 1,
}

# The MAPIE prefit estimator-list order and the 80% interval's nominal quantiles.
QUANTILE_ALPHAS: tuple[float, float, float] = (0.1, 0.9, 0.5)  # [lower, upper, median]
CONFIDENCE_LEVEL: float = 0.8


def _as_2d_float(X: Any) -> np.ndarray:
    """Coerce feature input to a 2-D float ndarray (drops pandas feature names).

    Passing bare ndarrays to XGBoost + MAPIE keeps fit/predict feature spaces
    consistent (no feature-name mismatch warnings) and lets XGBoost treat NaN as
    its native "missing" — the replace-with-NaN honesty carried from the panel.
    """
    arr = np.asarray(X, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


def make_quantile_models(X_tr: Any, y_tr: Any, params: dict[str, Any] | None = None) -> list:
    """Fit the three XGBoost quantile regressors in MAPIE prefit-list order.

    Args:
        X_tr: proper-train design matrix (array-like / DataFrame; NaN allowed —
            XGBoost handles it natively).
        y_tr: proper-train target (the listing-day return).
        params: optional overrides merged over ``PARAMS`` (e.g. lighter trees in
            unit tests).

    Returns:
        ``[m_low, m_high, m_med]`` — three FITTED ``XGBRegressor``s at
        ``quantile_alpha`` 0.1 / 0.9 / 0.5, each with
        ``objective="reg:quantileerror"``, IN THAT ORDER (the prefit contract:
        lower, upper, median — NOT ascending).
    """
    from xgboost import XGBRegressor  # lazy: module import stays offline

    common = dict(
        objective="reg:quantileerror",
        tree_method="hist",
        **{**PARAMS, **(params or {})},
    )
    Xa = _as_2d_float(X_tr)
    ya = np.asarray(y_tr, dtype=float)

    models = [
        XGBRegressor(quantile_alpha=alpha, **common).fit(Xa, ya)
        for alpha in QUANTILE_ALPHAS
    ]
    return models  # [lower(0.1), upper(0.9), median(0.5)]


def fit_cqr(models: list, X_cal: Any, y_cal: Any):
    """Wrap the prefit quantile models in a conformalized-quantile regressor.

    Builds ``ConformalizedQuantileRegressor(estimator=models,
    confidence_level=0.8, prefit=True)`` and calibrates it via ``.conformalize``
    on the (disjoint, still-pre-T0) calibration slice — the split-conformal step
    that turns three raw quantile curves into a marginal-coverage 80% interval.

    Args:
        models: the ordered ``[lower, upper, median]`` list from
            ``make_quantile_models``.
        X_cal: calibration design matrix (disjoint from the proper-train slice).
        y_cal: calibration target.

    Returns:
        A conformalized ``ConformalizedQuantileRegressor`` ready for
        ``predict_band``.
    """
    from mapie.regression import ConformalizedQuantileRegressor  # lazy

    cqr = ConformalizedQuantileRegressor(
        estimator=models,
        confidence_level=CONFIDENCE_LEVEL,
        prefit=True,
    )
    cqr.conformalize(_as_2d_float(X_cal), np.asarray(y_cal, dtype=float))
    return cqr


def predict_band(cqr, X: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Predict the adaptive-width 80% band for held-out rows.

    Unpacks MAPIE's ``predict_interval`` (``intervals`` shape ``(n, 2, 1)``) and
    applies the non-crossing REARRANGEMENT so ``high >= low`` always holds even
    when the underlying quantile models cross on a small sample (see module
    docstring). The interval WIDTH still varies per row (adaptive — D5-03).

    Args:
        cqr: a conformalized ``ConformalizedQuantileRegressor`` from ``fit_cqr``.
        X: held-out design matrix (one or more rows).

    Returns:
        ``(median, low, high)`` — three 1-D float ndarrays of length ``n``:
          - ``median`` — the 0.5-quantile point (the UI's faint tick; P21 — never
            a headline point estimate),
          - ``low`` / ``high`` — the conformalized 80%-interval bounds, rearranged
            so ``high >= low`` everywhere.
    """
    points, intervals = cqr.predict_interval(_as_2d_float(X))
    intervals = np.asarray(intervals, dtype=float)

    bound_a = intervals[:, 0, 0]
    bound_b = intervals[:, 1, 0]
    low = np.minimum(bound_a, bound_b)   # non-crossing rearrangement (Chernozhukov+ 2010)
    high = np.maximum(bound_a, bound_b)

    median = np.asarray(points, dtype=float).reshape(-1)
    return median, low, high


__all__ = [
    "PARAMS",
    "QUANTILE_ALPHAS",
    "CONFIDENCE_LEVEL",
    "make_quantile_models",
    "fit_cqr",
    "predict_band",
]
