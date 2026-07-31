"""
tests/unit/test_walkforward_abstention.py — D5-09 / FCAST-01: the walk-forward's
two conformal-native abstention halves (``out_of_support`` extrapolation +
``interval_too_wide`` width guard) complete the three first-class ForecastRecord
abstain reasons, and never fabricate a band.

Proves (on tiny, deterministic, offline panels):
  * an IPO whose feature vector sits OUTSIDE the proper-train ``[q01, q99]`` support
    abstains ``out_of_support`` when ``check_support=True`` (the extrapolation half).
  * an IPO whose calibrated 80% band is wider than ``max_width`` (and, separately,
    wider than ``width_iqr_mult`` × the training-return IQR) abstains
    ``interval_too_wide`` (the width half).
  * an in-support, tight-interval IPO is SCORED (covered) — the guards decline only
    the genuinely un-honest cases.
  * the two D5-09 guards are OPT-IN: with the defaults, an out-of-support IPO is
    still covered (so the existing no-lookahead fixture is behaviourally unchanged).
  * every abstain row carries NO band (low/high/median all NaN), and the reason is
    one of the exact ForecastRecord enum strings.
"""
from __future__ import annotations

import pandas as pd

from agent.forecast_schema import ForecastRecord  # noqa: F401 - enum-source reference
from pipelines.forecast.walkforward import walk_forward

# light trees keep the offline loop fast; the abstention logic is model-agnostic.
_LIGHT = {"n_estimators": 40, "max_depth": 2}
_MIN_TRAIN = 20
_CAL_FRAC = 0.5  # a fat calibration slice so a small panel still clears MIN_CAL(=10)

# the three first-class abstain reasons, exactly as ForecastRecord declares them.
_ABSTAIN_REASONS = {"insufficient_history", "out_of_support", "interval_too_wide"}


def _build(
    target_feats: dict[str, float],
    *,
    n_prior: int = 32,
    ret_center: float = 0.05,
    ret_noise: float = 0.01,
    seed: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A tiny panel of ``n_prior`` tight-feature priors + one TARGET listed last.

    Prior features are drawn tight in ``[1.0, 2.0]`` so the proper-train support is a
    narrow ``[q01, q99]``; the TARGET's features are whatever the scenario needs
    (in-support or far outside). Returns cluster near ``ret_center`` with
    ``ret_noise`` spread so the calibrated band is narrow unless the scenario widens
    it. ``panel`` and ``X`` share a RangeIndex (aligned by position, as walk_forward
    expects).
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2016-01-01")
    prows: list[dict] = []
    frows: list[dict] = []
    for i in range(n_prior):
        ld = start + pd.Timedelta(days=20 * i)
        issue = ld - pd.Timedelta(days=7)
        prows.append(
            {
                "issuer": f"Prior {i:03d}",
                "issue_date": issue,
                "listing_date": ld,
                "listing_day_return": float(ret_center + rng.normal(0.0, ret_noise)),
            }
        )
        frows.append(
            {
                "f0": float(rng.uniform(1.0, 2.0)),
                "f1": float(rng.uniform(1.0, 2.0)),
                "available_at": issue,
            }
        )

    t_ld = start + pd.Timedelta(days=20 * n_prior + 40)  # strictly after every prior
    t_issue = t_ld - pd.Timedelta(days=7)
    prows.append(
        {
            "issuer": "TARGET",
            "issue_date": t_issue,
            "listing_date": t_ld,
            "listing_day_return": float(ret_center),
        }
    )
    frows.append({**target_feats, "available_at": t_issue})

    return pd.DataFrame(prows), pd.DataFrame(frows)


def _target_row(oos: pd.DataFrame) -> pd.Series:
    hit = oos[oos["issuer"] == "TARGET"]
    assert len(hit) == 1, "the TARGET IPO must be scored exactly once"
    return hit.iloc[0]


def _assert_no_band(row: pd.Series) -> None:
    assert bool(row["abstain"]) is True
    assert row["abstain_reason"] in _ABSTAIN_REASONS
    assert pd.isna(row["low"]) and pd.isna(row["high"]) and pd.isna(row["median"])


# ---------------------------------------------------------------------------
# (a) out_of_support — the extrapolation half
# ---------------------------------------------------------------------------
def test_out_of_support_ipo_abstains_when_support_checked() -> None:
    # f0=50 sits far outside the tight [1,2] training support.
    panel, X = _build({"f0": 50.0, "f1": 1.5}, seed=1)
    oos = walk_forward(
        panel, X, min_train=_MIN_TRAIN, cal_frac=_CAL_FRAC,
        check_support=True, params=_LIGHT,
    )
    target = _target_row(oos)
    _assert_no_band(target)
    assert target["abstain_reason"] == "out_of_support"


def test_out_of_support_is_opt_in_default_covers_the_ipo() -> None:
    # SAME out-of-support target, but with the default (check_support=False) it is
    # scored — proving the D5-09 support guard is opt-in (existing fixture unchanged).
    panel, X = _build({"f0": 50.0, "f1": 1.5}, seed=1)
    oos = walk_forward(
        panel, X, min_train=_MIN_TRAIN, cal_frac=_CAL_FRAC, params=_LIGHT
    )
    target = _target_row(oos)
    assert bool(target["abstain"]) is False
    assert pd.isna(target["abstain_reason"])  # covered row carries no abstain reason


# ---------------------------------------------------------------------------
# (b) interval_too_wide — the width half (absolute + IQR-relative forms)
# ---------------------------------------------------------------------------
def test_wide_interval_ipo_abstains_on_absolute_max_width() -> None:
    # a moderate-noise panel -> a real (non-trivial) band; a tiny max_width trips it.
    panel, X = _build({"f0": 1.5, "f1": 1.5}, ret_noise=0.05, seed=2)
    oos = walk_forward(
        panel, X, min_train=_MIN_TRAIN, cal_frac=_CAL_FRAC,
        max_width=0.02, params=_LIGHT,
    )
    target = _target_row(oos)
    _assert_no_band(target)
    assert target["abstain_reason"] == "interval_too_wide"


def test_wide_interval_ipo_abstains_on_iqr_relative_guard() -> None:
    # the plan's "derived from the training-return IQR" form: a small multiplier of
    # the training IQR is narrower than the calibrated band -> interval_too_wide.
    panel, X = _build({"f0": 1.5, "f1": 1.5}, ret_noise=0.05, seed=2)
    oos = walk_forward(
        panel, X, min_train=_MIN_TRAIN, cal_frac=_CAL_FRAC,
        width_iqr_mult=0.1, params=_LIGHT,
    )
    target = _target_row(oos)
    _assert_no_band(target)
    assert target["abstain_reason"] == "interval_too_wide"


# ---------------------------------------------------------------------------
# (c) in-support + tight interval -> the IPO is SCORED (covered)
# ---------------------------------------------------------------------------
def test_in_support_tight_interval_ipo_is_scored() -> None:
    panel, X = _build({"f0": 1.5, "f1": 1.5}, ret_noise=0.01, seed=3)
    oos = walk_forward(
        panel, X, min_train=_MIN_TRAIN, cal_frac=_CAL_FRAC,
        check_support=True, max_width=10.0, width_iqr_mult=100.0, params=_LIGHT,
    )
    target = _target_row(oos)
    assert bool(target["abstain"]) is False
    assert pd.isna(target["abstain_reason"])  # covered row carries no abstain reason
    assert not pd.isna(target["low"]) and not pd.isna(target["high"])
    assert target["high"] >= target["low"]  # non-crossing band (D5-03)
