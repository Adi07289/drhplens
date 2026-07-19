"""
Unit test — lean walk-forward feature selection + the training-support helper
(05-08-PLAN.md Task 3, D5-07 + the D5-09 out_of_support input).

Everything here is OFFLINE and deterministic (the 05-01 synthetic builders; a light
XGBoost fit on the tiny fixture; no network):

  (a) select_features returns at most max_k features, ranked by importance/stability,
      with an importance/stability table row per candidate (D5-07).
  (b) is_out_of_support returns True for a feature vector pushed outside the training
      [q01, q99] support and False for an in-support one (the D5-09 abstention input);
      a MISSING feature is not out-of-support.
  (c) SELECTED_FEATURES is an importable lean subset of the candidate pool.
  (d) importing pipelines.features.select triggers no xgboost import at module load.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from pipelines.features import FEATURE_COLUMNS
from pipelines.features.select import (
    SELECTED_FEATURES,
    is_out_of_support,
    select_features,
    training_support,
)
from tests.unit.fixtures.forecast_fixtures import synthetic_features, synthetic_panel

# Light XGBoost params so the walk-forward fold fits stay fast on the tiny fixture.
_LIGHT_PARAMS = {"n_estimators": 20, "max_depth": 2}


# ---------------------------------------------------------------------------
# (a) select_features — lean set (<= max_k), ranked, table row per candidate
# ---------------------------------------------------------------------------


def test_select_features_returns_lean_ranked_set_with_table():
    """select_features caps at max_k, ranks by score, and tables every candidate."""
    panel = synthetic_panel(n=80, seed=0)
    X = synthetic_features(panel, seed=1)
    candidates = [c for c in X.columns if c != "available_at"]

    selected, table = select_features(
        panel, X, max_k=3, min_train=20, max_folds=4, params=_LIGHT_PARAMS
    )

    # lean cap honored (D5-07)
    assert len(selected) <= 3
    # every candidate feature gets a table row (the model-card input)
    assert set(table.index) == set(candidates)
    # the table is ordered by score descending
    assert list(table["score"]) == sorted(table["score"], reverse=True)
    # the selected features are exactly the table rows flagged selected, and are
    # drawn from the candidate pool
    assert set(selected) <= set(candidates)
    assert set(selected) == set(table.index[table["selected"]])
    # the importance/stability columns the model card documents are present
    for col in ("mean_importance", "stability", "score", "selected"):
        assert col in table.columns


def test_select_features_requires_walkforward_panel_columns():
    """A panel missing the walk-forward columns raises (no silent mis-selection)."""
    panel = synthetic_panel(n=20, seed=2).drop(columns=["listing_day_return"])
    X = synthetic_features(panel, seed=3)
    with pytest.raises(ValueError, match="listing_day_return"):
        select_features(panel, X, min_train=5)


# ---------------------------------------------------------------------------
# (b) is_out_of_support — the D5-09 extrapolation trigger
# ---------------------------------------------------------------------------


def test_is_out_of_support_flags_extrapolation_only():
    """Out-of-[q01,q99] -> True; an in-support vector and a missing value -> False."""
    panel = synthetic_panel(n=60, seed=4)
    X = synthetic_features(panel, seed=5)
    support = training_support(X)

    # support is computed over the numeric features (available_at dropped)
    assert "available_at" not in support
    assert "issue_size_cr" in support

    # an in-support vector: the training median of each feature is inside [q01,q99]
    feat = X.drop(columns=["available_at"])
    in_support = {col: float(feat[col].median()) for col in feat.columns}
    assert is_out_of_support(in_support, support) is False

    # push one feature far above its q99 -> out of support
    lo, hi = support["issue_size_cr"]
    out = dict(in_support)
    out["issue_size_cr"] = hi + abs(hi) * 10.0 + 1.0
    assert is_out_of_support(out, support) is True

    # a MISSING (NaN) feature is not out-of-support (nothing to extrapolate)
    missing = dict(in_support)
    missing["issue_size_cr"] = float("nan")
    assert is_out_of_support(missing, support) is False


# ---------------------------------------------------------------------------
# (c) SELECTED_FEATURES — importable lean subset of the candidate pool
# ---------------------------------------------------------------------------


def test_selected_features_is_lean_subset_of_candidate_pool():
    """SELECTED_FEATURES is a lean (~8–15) importable subset of FEATURE_COLUMNS."""
    assert set(SELECTED_FEATURES) <= set(FEATURE_COLUMNS)
    assert 8 <= len(SELECTED_FEATURES) <= 15
    assert len(set(SELECTED_FEATURES)) == len(SELECTED_FEATURES)  # no dupes


# ---------------------------------------------------------------------------
# (d) importing the module triggers no xgboost import (lazy)
# ---------------------------------------------------------------------------


def test_importing_select_does_not_import_xgboost():
    """Module load stays offline: no xgboost at import (lazy in-function only)."""
    code = (
        "import sys; import pipelines.features.select as s; "
        "assert 'xgboost' not in sys.modules, 'xgboost imported at module load'; "
        "assert 'mapie' not in sys.modules, 'mapie imported at module load'; "
        "print('lazy ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "lazy ok" in result.stdout
