"""
tests/unit/test_cqr_interval.py — FCAST-01 / D5-03: the prefit XGBoost-quantile +
MAPIE conformalized-quantile wrapper produces an ADAPTIVE-WIDTH 80% interval.

Offline + tiny: everything runs against the deterministic ``synthetic_panel`` /
``synthetic_features`` builders (no network, no real ~200-300-row panel), with
light trees so the whole file runs in seconds.

What is pinned here:
  * ``make_quantile_models`` returns exactly three FITTED regressors in MAPIE
    prefit-list order ``[lower(0.1), upper(0.9), median(0.5)]``, each with
    ``objective="reg:quantileerror"``.
  * ``fit_cqr`` builds ``ConformalizedQuantileRegressor(confidence_level=0.8,
    prefit=True)`` and conformalizes on the (disjoint) calibration slice.
  * ``predict_band`` yields ``high >= low`` on every held-out IPO AND an interval
    whose WIDTH VARIES across IPOs (adaptive / heteroscedastic — D5-03, not a
    constant-width split-conformal band).
  * importing ``pipelines.forecast.model`` does NOT import xgboost/mapie at module
    load (they are lazy, inside the functions).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from pipelines.forecast.model import (
    fit_cqr,
    make_quantile_models,
    predict_band,
)
from tests.unit.fixtures.forecast_fixtures import (
    synthetic_features,
    synthetic_panel,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# light trees keep the offline test fast; the wiring/adaptivity is what matters here
_TEST_PARAMS = {"n_estimators": 60, "max_depth": 2}


def _split():
    """A tiny expanding-style train / calibration / held-out split of the fixture.

    Ordered by listing_date (the walk-forward posture); calibration is a slice
    DISJOINT from the proper-train slice; the held-out tail has >= 2 IPOs.
    """
    panel = synthetic_panel()
    feats = synthetic_features(panel)
    feat_cols = [c for c in feats.columns if c != "available_at"]

    usable = panel[panel["listing_day_return"].notna()].sort_values("listing_date")
    n = len(usable)
    i_tr, i_cal = int(n * 0.6), int(n * 0.8)
    tr = usable.iloc[:i_tr]
    cal = usable.iloc[i_tr:i_cal]
    te = usable.iloc[i_cal:]

    def xy(sub):
        return feats.loc[sub.index, feat_cols], sub["listing_day_return"]

    return xy(tr), xy(cal), (feats.loc[te.index, feat_cols], te)


def test_make_quantile_models_order_and_objective():
    """Three fitted models in [lower(0.1), upper(0.9), median(0.5)] order, each a
    reg:quantileerror quantile regressor (the MAPIE prefit contract)."""
    (Xtr, ytr), _, _ = _split()
    models = make_quantile_models(Xtr, ytr, params=_TEST_PARAMS)

    assert len(models) == 3
    alphas = [m.get_params()["quantile_alpha"] for m in models]
    assert alphas == [0.1, 0.9, 0.5], "prefit list order must be [lower, upper, median]"
    for m in models:
        assert m.get_params()["objective"] == "reg:quantileerror"


def test_cqr_interval_is_adaptive_width_and_ordered():
    """The prefit CQR 80% interval has high>=low everywhere and a width that
    DIFFERS across at least two held-out IPOs (adaptive — D5-03, FCAST-01)."""
    (Xtr, ytr), (Xcal, ycal), (Xte, te) = _split()

    models = make_quantile_models(Xtr, ytr, params=_TEST_PARAMS)
    cqr = fit_cqr(models, Xcal, ycal)
    median, low, high = predict_band(cqr, Xte)

    # predicts one band per held-out IPO (>= 2 of them)
    assert len(low) == len(high) == len(median) == len(Xte)
    assert len(Xte) >= 2

    # every interval is ordered (rearrangement guarantees this even under crossing)
    assert np.all(high >= low), "every 80% interval must satisfy high >= low"

    # adaptive: the width is not constant across IPOs (>= 2 distinct widths)
    widths = high - low
    assert np.all(widths >= 0.0)
    assert np.unique(np.round(widths, 8)).size >= 2, (
        "interval width must VARY across IPOs (adaptive CQR, D5-03) — a constant "
        "width would mean a rejected split-conformal band"
    )


def test_calibration_slice_is_disjoint_from_train():
    """The calibration slice shares no index with the proper-train slice — a hard
    precondition of a valid conformal coverage guarantee."""
    (Xtr, _), (Xcal, _), _ = _split()
    assert set(Xtr.index).isdisjoint(set(Xcal.index))


def test_model_module_import_is_lazy_no_xgboost_or_mapie():
    """Importing pipelines.forecast.model must NOT import xgboost/mapie at module
    load — they are imported lazily inside the functions so collecting the unit
    suite (and the import-light loader package) never drags in the modelling stack.
    """
    code = (
        "import sys\n"
        "import pipelines.forecast.model  # noqa: F401\n"
        "assert 'xgboost' not in sys.modules, 'xgboost imported at module load'\n"
        "assert 'mapie' not in sys.modules, 'mapie imported at module load'\n"
        "print('lazy-ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"lazy-import check failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert "lazy-ok" in proc.stdout
