"""
Unit test — survivorship-corrected historical IPO panel (04-07-PLAN.md, FCAST-03).

Pins the three P3 survivorship-bias controls, all OFFLINE (small hand-built
in-memory DataFrames / row dicts — NO live SEBI/chittorgarh/NSE network, no
network at import):

  1. The full `status` taxonomy (withdrawn / listed_alive / delisted / merged /
     name_changed) round-trips through assembly, and an unknown status is
     rejected (never silently coerced into a survivor).
  2. Replace-with-NaN survivorship: a row whose listing-day price is unavailable
     keeps `listing_day_return = NaN` and is RETAINED — the panel row count is
     preserved, the absence is counted, never dropped.
  3. The ~7% median MAAR sanity-check fires a plain-text divergence flag above
     the survivor-inflation band and stays quiet in-band.

Also exercises the committed offline SAMPLE artifact (Task 2) when present:
the sample parquet loads, carries the full taxonomy, and includes a NaN row.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from pipelines.historical import (
    PANEL_COLUMNS,
    STATUS_VALUES,
    assemble_panel,
    coerce_panel,
    compute_listing_day_return,
)
from pipelines.historical.validate import (
    BAND_UPPER,
    MAAR_BASELINE,
    sanity_check_median,
)

# ---------------------------------------------------------------------------
# Fixtures — tiny hand-built rows (no network)
# ---------------------------------------------------------------------------


def _base_rows() -> list[dict]:
    """One row per status value; the withdrawn + one listed row have no listing
    price (replace-with-NaN survivorship). Returns chosen so the median of the
    scored rows sits in-band (~7%)."""
    return [
        # listed_alive, +8%
        {
            "issuer": "Sample Alpha Ltd",
            "issue_date": "2018-03-01",
            "listing_date": "2018-03-12",
            "issue_price": 100.0,
            "listing_day_close": 108.0,
            "status": "listed_alive",
        },
        # delisted, +4%
        {
            "issuer": "Sample Gamma Ltd",
            "issue_date": "2015-06-01",
            "listing_date": "2015-06-15",
            "issue_price": 150.0,
            "listing_day_close": 156.0,
            "status": "delisted",
        },
        # merged, +7%
        {
            "issuer": "Sample Delta Ltd",
            "issue_date": "2016-09-01",
            "listing_date": "2016-09-14",
            "issue_price": 300.0,
            "listing_day_close": 321.0,
            "status": "merged",
        },
        # name_changed, +7.5%
        {
            "issuer": "Sample Epsilon Ltd",
            "issue_date": "2019-01-10",
            "listing_date": "2019-01-22",
            "issue_price": 80.0,
            "listing_day_close": 86.0,
            "status": "name_changed",
        },
        # withdrawn — never listed: no price => NaN return, RETAINED
        {
            "issuer": "Sample Zeta Ltd",
            "issue_date": "2020-02-01",
            "listing_date": None,
            "issue_price": 120.0,
            "listing_day_close": None,
            "status": "withdrawn",
        },
        # listed_alive but listing-day price UNAVAILABLE => NaN return, RETAINED
        {
            "issuer": "Sample Eta Ltd",
            "issue_date": "2021-11-01",
            "listing_date": "2021-11-15",
            "issue_price": 120.0,
            "listing_day_close": None,
            "status": "listed_alive",
        },
    ]


# ---------------------------------------------------------------------------
# 1. Status taxonomy
# ---------------------------------------------------------------------------


def test_status_taxonomy_is_the_five_survivorship_categories():
    assert STATUS_VALUES == {
        "withdrawn",
        "listed_alive",
        "delisted",
        "merged",
        "name_changed",
    }


def test_full_status_taxonomy_round_trips_through_assembly():
    df = assemble_panel(_base_rows())
    # Every one of the five status values must be representable in a panel.
    present = set(df["status"].dropna().unique())
    assert {"withdrawn", "delisted", "merged", "name_changed"} <= present
    assert set(df["status"].unique()) <= STATUS_VALUES
    assert list(df.columns) == list(PANEL_COLUMNS)


def test_unknown_status_is_rejected_never_coerced_into_a_survivor():
    bad = _base_rows()
    bad.append({"issuer": "Bad Co", "issue_price": 10.0, "status": "ipo_hype"})
    with pytest.raises(ValueError, match="invalid status"):
        assemble_panel(bad)


# ---------------------------------------------------------------------------
# 2. Replace-with-NaN survivorship (never drop)
# ---------------------------------------------------------------------------


def test_missing_listing_price_stays_as_nan_row_and_is_retained():
    rows = _base_rows()
    df = assemble_panel(rows)

    # Row count preserved — absence is counted, not dropped.
    assert len(df) == len(rows)

    # The withdrawn IPO and the price-unavailable listed IPO are RETAINED as NaN.
    zeta = df.loc[df["issuer"] == "Sample Zeta Ltd"].iloc[0]
    eta = df.loc[df["issuer"] == "Sample Eta Ltd"].iloc[0]
    assert math.isnan(zeta["listing_day_return"])
    assert math.isnan(eta["listing_day_return"])

    # At least one NaN return exists in the panel (survivorship retained).
    assert df["listing_day_return"].isna().any()


def test_listing_day_return_computes_from_prices():
    assert compute_listing_day_return(100.0, 108.0) == pytest.approx(0.08)
    # Missing / non-positive inputs => NaN, never 0.0.
    assert math.isnan(compute_listing_day_return(100.0, None))
    assert math.isnan(compute_listing_day_return(None, 108.0))
    assert math.isnan(compute_listing_day_return(0.0, 108.0))

    df = assemble_panel(_base_rows())
    alpha = df.loc[df["issuer"] == "Sample Alpha Ltd"].iloc[0]
    assert alpha["listing_day_return"] == pytest.approx(0.08)


# ---------------------------------------------------------------------------
# 3. ~7% median MAAR sanity-check divergence flag
# ---------------------------------------------------------------------------


def test_median_flag_quiet_in_band():
    df = assemble_panel(_base_rows())
    median, flag = sanity_check_median(df)
    # scored returns: [0.08, 0.04, 0.07, 0.075] -> median 0.0725, in-band
    assert median == pytest.approx(0.0725, abs=1e-6)
    assert flag is None


def test_median_flag_fires_above_survivor_inflation_band():
    # An inflated survivor-only universe: every return ~40% (well above 20%).
    inflated = [
        {
            "issuer": f"Inflated {i}",
            "issue_price": 100.0,
            "listing_day_close": 140.0,
            "status": "listed_alive",
        }
        for i in range(5)
    ]
    df = assemble_panel(inflated)
    median, flag = sanity_check_median(df)
    assert median > BAND_UPPER
    assert flag is not None
    assert "survivorship" in flag.lower()
    # Plain text, not a widget / not a red-green token.
    assert "<" not in flag and ">" not in flag


def test_median_flag_fires_below_floor():
    depressed = [
        {
            "issuer": f"Depressed {i}",
            "issue_price": 100.0,
            "listing_day_close": 80.0,  # -20%
            "status": "listed_alive",
        }
        for i in range(5)
    ]
    df = assemble_panel(depressed)
    median, flag = sanity_check_median(df)
    assert median < 0
    assert flag is not None


def test_sanity_check_excludes_nan_rows_from_the_statistic_but_they_stay_in_panel():
    df = assemble_panel(_base_rows())
    scored = df["listing_day_return"].dropna()
    # 4 scored + 2 NaN rows retained
    assert len(scored) == 4
    assert len(df) == 6
    median, _ = sanity_check_median(df)
    assert median == pytest.approx(float(scored.median()))


def test_baseline_is_the_shah_mehta_maar():
    assert MAAR_BASELINE == pytest.approx(0.0719)


# ---------------------------------------------------------------------------
# Committed offline SAMPLE artifact (Task 2) — exercised when present
# ---------------------------------------------------------------------------

_SAMPLE_PARQUET = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "historical"
    / "ipo_panel.parquet"
)
_SAMPLE_CSV = _SAMPLE_PARQUET.with_suffix(".csv")


@pytest.mark.skipif(
    not _SAMPLE_PARQUET.exists(), reason="sample parquet not built yet (Task 2)"
)
def test_committed_sample_parquet_has_full_taxonomy_and_a_nan_row():
    df = coerce_panel(pd.read_parquet(_SAMPLE_PARQUET))
    assert list(df.columns) == list(PANEL_COLUMNS)
    assert set(df["status"].unique()) == STATUS_VALUES  # all five present
    assert df["listing_day_return"].isna().any()  # survivorship NaN retained
    # The sample must be sane enough not to trip its own divergence flag.
    _, flag = sanity_check_median(df)
    assert flag is None


@pytest.mark.skipif(
    not _SAMPLE_CSV.exists(), reason="sample CSV not built yet (Task 2)"
)
def test_committed_sample_csv_mirror_matches_parquet_rows():
    csv_df = coerce_panel(pd.read_csv(_SAMPLE_CSV))
    pq_df = coerce_panel(pd.read_parquet(_SAMPLE_PARQUET))
    assert len(csv_df) == len(pq_df)
    assert set(csv_df["status"].unique()) == set(pq_df["status"].unique())
