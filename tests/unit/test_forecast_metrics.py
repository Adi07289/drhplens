"""
Unit test — the GLOBAL walk-forward honesty metrics (D5-12 / FCAST-04).

``pipelines.forecast.diagnostics.global_metrics`` computes empirical coverage, MAE
and per-year RMSE ONCE over the out-of-sample walk-forward rows; the same block is
baked into every IPO's record (identical across pages, D5-12). These tests pin the
correctness AND the honesty posture (P17 — calibration theater):

  - coverage is the RAW held-out number (3 of 4 covered -> exactly 0.75), never
    silently rounded to the 0.80 target;
  - MAE and per-year RMSE match hand-computed values, with no fabricated year;
  - abstain rows contribute to NO statistic and are excluded from ``n``.

Everything is a hand-constructed frame (or the deterministic offline ``oos_rows``
fixture) — no model, no network.
"""
from __future__ import annotations

import math

import pandas as pd

from pipelines.forecast.diagnostics import global_metrics
from tests.unit.fixtures.forecast_fixtures import oos_rows


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Coverage / MAE / per-year RMSE correctness on known rows
# ---------------------------------------------------------------------------


def test_coverage_mae_and_per_year_rmse_are_exact() -> None:
    """A known 4-row frame (3 of 4 covered) yields coverage 0.75, MAE 7.0, and the
    hand-computed per-year RMSE — all in percentage points."""
    frame = _frame(
        [
            # 2016 — covered (10 in [-5, 20]); |10-6| = 4; se = 16
            {"actual": 10.0, "low": -5.0, "high": 20.0, "median": 6.0, "listing_year": 2016},
            # 2016 — covered (-5 in [-10, 0]); |-5-(-3)| = 2; se = 4
            {"actual": -5.0, "low": -10.0, "high": 0.0, "median": -3.0, "listing_year": 2016},
            # 2017 — NOT covered (30 > 25); |30-12| = 18; se = 324
            {"actual": 30.0, "low": 0.0, "high": 25.0, "median": 12.0, "listing_year": 2017},
            # 2017 — covered (8 in [-2, 18]); |8-12| = 4; se = 16
            {"actual": 8.0, "low": -2.0, "high": 18.0, "median": 12.0, "listing_year": 2017},
        ]
    )

    m = global_metrics(frame)

    # 3 of 4 covered -> exactly 0.75 (raw, NOT the 0.80 target) — P17.
    assert m["coverage_empirical"] == 0.75
    # MAE = mean(4, 2, 18, 4) = 7.0 points.
    assert m["mae_pts"] == 7.0
    # per-year RMSE: 2016 = sqrt((16+4)/2) = sqrt(10) ; 2017 = sqrt((324+16)/2) = sqrt(170)
    assert m["per_year_rmse"] == {
        "2016": round(math.sqrt(10.0), 2),
        "2017": round(math.sqrt(170.0), 2),
    }
    # mean width = mean(25, 10, 25, 20) = 20.0
    assert m["mean_width"] == 20.0
    assert m["n"] == 4


def test_per_year_rmse_keys_are_only_years_present_no_fabrication() -> None:
    """``per_year_rmse`` is keyed only by the listing years actually present — a year
    with no scored IPO is absent, never a fabricated 0.0."""
    frame = _frame(
        [
            {"actual": 5.0, "low": -5.0, "high": 15.0, "median": 4.0, "listing_year": 2019},
            {"actual": 12.0, "low": 0.0, "high": 20.0, "median": 8.0, "listing_year": 2023},
        ]
    )

    m = global_metrics(frame)

    assert set(m["per_year_rmse"].keys()) == {"2019", "2023"}
    # No fabricated intervening years (2020/2021/2022) appear.
    assert "2020" not in m["per_year_rmse"]
    assert "2021" not in m["per_year_rmse"]


# ---------------------------------------------------------------------------
# Honesty: coverage is never silently clamped to the 0.80 target (P17)
# ---------------------------------------------------------------------------


def test_all_covered_coverage_is_one_not_clamped_to_target() -> None:
    """An all-covered frame reports coverage 1.0 — it is NOT silently rounded down to
    the 0.80 target (P17 / calibration-theater guard)."""
    frame = _frame(
        [
            {"actual": 3.0, "low": -5.0, "high": 10.0, "median": 2.0, "listing_year": 2020},
            {"actual": 7.0, "low": -1.0, "high": 15.0, "median": 6.0, "listing_year": 2021},
            {"actual": -2.0, "low": -8.0, "high": 4.0, "median": -1.0, "listing_year": 2022},
        ]
    )

    m = global_metrics(frame)

    assert m["coverage_empirical"] == 1.0
    assert m["coverage_empirical"] != 0.80


def test_offline_oos_fixture_coverage_is_real_and_below_one() -> None:
    """The deterministic ``oos_rows`` fixture (actual inside the band for most rows,
    outside for some) yields a realistic coverage strictly between 0 and 1 — a real
    held-out number, not the fabricated exact 0.80 (P17)."""
    m = global_metrics(oos_rows())

    assert 0.0 < m["coverage_empirical"] < 1.0
    assert m["coverage_empirical"] != 0.80
    assert m["n"] == len(oos_rows())
    # every listing year in the fixture surfaces a per-year RMSE
    assert set(m["per_year_rmse"].keys()) == {
        str(int(y)) for y in oos_rows()["listing_year"].unique()
    }


# ---------------------------------------------------------------------------
# Abstain rows are excluded from every statistic
# ---------------------------------------------------------------------------


def test_abstain_rows_are_excluded_from_all_statistics() -> None:
    """An abstain row (no band) contributes to NO statistic and is not counted in
    ``n`` — a no-band row is not a 0%-error row (D5-09 honesty)."""
    frame = _frame(
        [
            {"actual": 5.0, "low": -5.0, "high": 15.0, "median": 4.0, "listing_year": 2020,
             "abstain": False},
            {"actual": 2.0, "low": -10.0, "high": 12.0, "median": 3.0, "listing_year": 2020,
             "abstain": False},
            # abstain — NaN band; must NOT be counted or scored
            {"actual": 40.0, "low": float("nan"), "high": float("nan"),
             "median": float("nan"), "listing_year": 2021, "abstain": True},
        ]
    )

    m = global_metrics(frame)

    # only the two scored rows count — the abstain row is invisible to every stat
    assert m["n"] == 2
    assert m["coverage_empirical"] == 1.0  # both scored rows covered
    assert set(m["per_year_rmse"].keys()) == {"2020"}
    # the abstained 2021 row did NOT fabricate a 2021 RMSE bucket
    assert "2021" not in m["per_year_rmse"]


def test_empty_frame_returns_honest_nan_not_zero() -> None:
    """A frame with zero scored rows returns NaN coverage/MAE and n=0 — an honest
    absence, never a fabricated 0.0 coverage."""
    frame = _frame(
        [
            {"actual": 1.0, "low": float("nan"), "high": float("nan"),
             "median": float("nan"), "listing_year": 2020, "abstain": True},
        ]
    )

    m = global_metrics(frame)

    assert m["n"] == 0
    assert math.isnan(m["coverage_empirical"])
    assert math.isnan(m["mae_pts"])
    assert m["per_year_rmse"] == {}
