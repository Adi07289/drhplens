"""
tests/unit/test_baselines_dm.py — Wave-0 FCAST-05 / P9: the four locked baselines
scored as-of-T0 + the inline Diebold–Mariano significance test (+ Wilcoxon
robustness), with NO fragile `dieboldmariano` dependency added.

Proves:
  * ``baselines_asof`` returns the four EXACT baselines (predict_zero / global_median
    / trailing_12 / sector_mean) computed only from the pool.
  * ``score_baselines`` rebuilds the SAME as-of-T0 pool the model used (a post-T0
    listing can never leak into a baseline) and 'Other'-pools a small-N sector so
    ``sector_mean`` uses the pooled bucket (D5-10).
  * ``dm_test`` returns dm<0 & p<0.05 when the model's errors are uniformly smaller
    (the model wins) and NO significance on a statistical tie (a known-tie case).
  * ``wilcoxon_robustness`` returns a paired signed-rank p (the A7 cross-check).
  * baselines.py is MODEL-FREE (imports no xgboost / mapie / shap) and names no GMP
    display signal (predictor-side isolation, T-05-09-ISO) — no network at import.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipelines.forecast import baselines as bl
from pipelines.forecast.baselines import (
    BASELINE_NAMES,
    baselines_asof,
    dm_test,
    score_baselines,
    wilcoxon_robustness,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# (a) baselines_asof — the four EXACT values from the pool
# ---------------------------------------------------------------------------
def _crafted_pool() -> pd.DataFrame:
    """15 prior listings (ascending listing_date) with a known sector split."""
    rets = [
        0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14,
        0.16, 0.18, 0.20, 0.22, 0.24, 0.26, 0.28,
    ]
    sectors = (
        ["Tech", "Other", "Other", "Tech", "Other", "Other", "Other", "Tech",
         "Other", "Other", "Other", "Other", "Other", "Other", "Other"]
    )
    dates = pd.to_datetime(
        [f"2019-{1 + i // 2:02d}-{1 + (i % 2) * 14:02d}" for i in range(15)]
    )
    return pd.DataFrame(
        {"listing_date": dates, "listing_day_return": rets, "sector": sectors}
    )


def test_baselines_asof_returns_the_four_exact_values() -> None:
    pool = _crafted_pool()
    res = baselines_asof(pool, "Tech")

    assert set(res) == set(BASELINE_NAMES)
    # predict_zero is a constant 0.0% return
    assert res["predict_zero"] == 0.0
    # global_median = median of the whole pool
    assert res["global_median"] == pytest.approx(
        float(np.median(pool["listing_day_return"]))
    )
    # trailing_12 = median of the 12 most-recent prior listings by listing_date
    last12 = pool.sort_values("listing_date")["listing_day_return"].tail(12)
    assert res["trailing_12"] == pytest.approx(float(np.median(last12)))
    # sector_mean = mean of the pool rows in the target's sector
    tech = pool.loc[pool["sector"] == "Tech", "listing_day_return"]
    assert res["sector_mean"] == pytest.approx(float(tech.mean()))


def test_baselines_asof_nan_when_pool_cannot_support_a_baseline() -> None:
    """An empty pool fabricates nothing — global/trailing/sector are NaN, and
    predict_zero stays a constant 0.0 (never a fabricated number)."""
    empty = pd.DataFrame(
        {"listing_date": pd.to_datetime([]), "listing_day_return": [], "sector": []}
    )
    res = baselines_asof(empty, "Tech")
    assert res["predict_zero"] == 0.0
    assert np.isnan(res["global_median"])
    assert np.isnan(res["trailing_12"])
    assert np.isnan(res["sector_mean"])


# ---------------------------------------------------------------------------
# (b) dm_test — significant when the model is uniformly better; tie otherwise
# ---------------------------------------------------------------------------
def test_dm_test_significant_when_model_errors_uniformly_smaller() -> None:
    """|e_model| uniformly below |e_base| -> dm<0 & p<0.05 (the model wins)."""
    rng = np.random.default_rng(0)
    e_model = 0.10 + rng.normal(0.0, 0.01, 40)  # errors clustered near 0.10
    e_base = 0.50 + rng.normal(0.0, 0.01, 40)   # errors clustered near 0.50
    dm, p = dm_test(e_model, e_base)
    assert dm < 0.0
    assert p < 0.05


def test_dm_test_no_significance_on_a_statistical_tie() -> None:
    """Model and baseline errors drawn from the SAME distribution -> p>=0.05."""
    rng = np.random.default_rng(3)
    e_model = rng.normal(0.0, 2.0, 40)
    e_base = rng.normal(0.0, 2.0, 40)
    _, p = dm_test(e_model, e_base)
    assert p >= 0.05


def test_dm_test_degenerate_tie_and_too_few_rows() -> None:
    """Identical-magnitude errors (zero-variance differential) -> (0.0, 1.0);
    fewer than two paired points -> (NaN, NaN)."""
    dm, p = dm_test([0.2, -0.3, 0.5], [0.2, -0.3, 0.5])
    assert dm == 0.0
    assert p == 1.0

    dm1, p1 = dm_test([0.1], [0.4])
    assert np.isnan(dm1) and np.isnan(p1)


def test_wilcoxon_robustness_paired_p() -> None:
    rng = np.random.default_rng(1)
    e_model = 0.1 + rng.normal(0.0, 0.02, 30)
    e_base = 0.6 + rng.normal(0.0, 0.02, 30)
    p = wilcoxon_robustness(e_model, e_base)
    assert 0.0 <= p <= 1.0
    # all-equal magnitudes -> nan (nothing to rank)
    assert np.isnan(wilcoxon_robustness([0.2, 0.3], [0.2, 0.3]))


# ---------------------------------------------------------------------------
# (c) score_baselines — as-of-T0 pool + D5-10 'Other'-pooled sector_mean
# ---------------------------------------------------------------------------
def _panel_with_small_sectors() -> pd.DataFrame:
    """40 prior listings across small-N sectors (each < 30 -> pooled to 'Other')."""
    dates = pd.to_datetime(
        [pd.Timestamp("2016-01-01") + pd.Timedelta(days=20 * i) for i in range(40)]
    )
    rng = np.random.default_rng(2)
    rets = np.round(rng.normal(0.06, 0.10, 40), 4)
    sectors = (["Pharma"] * 5) + (["Tech"] * 10) + (["Bank"] * 25)  # all < 30
    return pd.DataFrame(
        {
            "issuer": [f"Prior {i:02d}" for i in range(40)],
            "issue_date": dates - pd.Timedelta(days=7),
            "listing_date": dates,
            "listing_day_return": rets,
            "sector": sectors,
        }
    )


def _covered_oos_for(panel: pd.DataFrame, issuer: str, t0, actual: float,
                     median: float) -> pd.DataFrame:
    """One covered walk-forward row referencing an as-of-T0 pool inside ``panel``."""
    return pd.DataFrame(
        [{"issuer": issuer, "actual": actual, "median": median, "t0": t0,
          "abstain": False}]
    )


def test_score_baselines_sector_mean_uses_pooled_other_for_small_n_sector() -> None:
    panel = _panel_with_small_sectors()
    t0 = pd.Timestamp("2020-01-01")  # after every prior listing
    # target IPO is a Pharma name (a 5-IPO sector -> pooled to 'Other' at min_n=30)
    panel = pd.concat(
        [
            panel,
            pd.DataFrame(
                [{"issuer": "Target Pharma", "issue_date": t0,
                  "listing_date": t0 + pd.Timedelta(days=7),
                  "listing_day_return": 0.05, "sector": "Pharma"}]
            ),
        ],
        ignore_index=True,
    )
    oos = _covered_oos_for(panel, "Target Pharma", t0, actual=0.05, median=0.06)

    scored = score_baselines(panel, oos, min_n=30)
    assert len(scored) == 1

    pool = panel[(panel["listing_date"] < t0) & panel["listing_day_return"].notna()]
    # Pharma is small-N -> pooled to 'Other', so sector_mean averages the WHOLE pool
    assert scored["sector_mean_pred"].iloc[0] == pytest.approx(
        float(pool["listing_day_return"].mean())
    )

    # Contrast: with NO pooling (min_n=1) sector_mean averages ONLY the 5 Pharma rows
    scored_nopool = score_baselines(panel, oos, min_n=1)
    pharma = pool.loc[pool["sector"] == "Pharma", "listing_day_return"]
    assert scored_nopool["sector_mean_pred"].iloc[0] == pytest.approx(
        float(pharma.mean())
    )
    # the pooled and unpooled sector_mean genuinely differ (pooling changed the slice)
    assert scored["sector_mean_pred"].iloc[0] != pytest.approx(
        scored_nopool["sector_mean_pred"].iloc[0]
    )


def test_score_baselines_pool_is_strictly_as_of_t0() -> None:
    """A listing on/after the target's T0 can NEVER enter a baseline (P9)."""
    panel = _panel_with_small_sectors()
    t0 = panel["listing_date"].iloc[20]  # cut mid-panel
    # a poisoned FUTURE listing (after T0) with an absurd return
    panel = pd.concat(
        [
            panel,
            pd.DataFrame(
                [{"issuer": "Future Poison", "issue_date": t0 + pd.Timedelta(days=400),
                  "listing_date": t0 + pd.Timedelta(days=410),
                  "listing_day_return": 99.0, "sector": "Bank"}]
            ),
        ],
        ignore_index=True,
    )
    oos = _covered_oos_for(panel, "Prior 20", t0, actual=0.05, median=0.06)
    scored = score_baselines(panel, oos, min_n=30)

    pool = panel[(panel["listing_date"] < t0) & panel["listing_day_return"].notna()]
    # the poisoned future return is excluded -> global_median matches the pool only
    assert scored["global_median_pred"].iloc[0] == pytest.approx(
        float(pool["listing_day_return"].median())
    )
    assert scored["global_median_pred"].iloc[0] < 1.0  # not dragged toward 99.0


# ---------------------------------------------------------------------------
# isolation — baselines.py is model-free and names no GMP display signal
# ---------------------------------------------------------------------------
def test_baselines_is_model_free_and_display_isolated() -> None:
    """baselines.py source references no modelling library and no GMP display
    signal (T-05-09-ISO / T-05-09-SC): model-free, no fragile dieboldmariano dep."""
    src = inspect.getsource(bl)
    for token in ("xgboost", "mapie", "shap", "dieboldmariano"):
        assert token not in src, f"baselines.py must not reference {token!r}"
    for token in ("pipelines.gmp", "gmp_schema", "load_gmp", "data/gmp", "import gmp"):
        assert token not in src, f"baselines.py must not reference GMP display {token!r}"


def test_baselines_import_pulls_in_no_modelling_stack() -> None:
    """Importing pipelines.forecast.baselines must NOT drag in xgboost/mapie/shap
    at module load — it is a numpy/pandas/scipy-only, model-free module."""
    code = (
        "import sys\n"
        "import pipelines.forecast.baselines  # noqa: F401\n"
        "for lib in ('xgboost', 'mapie', 'shap'):\n"
        "    assert lib not in sys.modules, f'{lib} imported at module load'\n"
        "print('model-free-ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "model-free-ok" in proc.stdout
