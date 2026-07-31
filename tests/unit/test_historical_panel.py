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

import datetime as dt
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
from pipelines.historical import sources as _S
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
# 4. Two-source survivorship merge (D5-04 / 05-02) — fetchers monkeypatched,
#    NO live network. Asserts the withdrawn overlay survives the merge (P3),
#    dedupe collapses a duplicate issuer, and a NaN-return row is RETAINED.
# ---------------------------------------------------------------------------


def _d(iso: str) -> dt.date:
    return dt.datetime.strptime(iso, "%Y-%m-%d").date()


def _fake_nse_past_issues(from_date, to_date) -> list[dict]:
    """Source A stand-in (listed core). Includes an issuer that ALSO appears in the
    withdrawn overlay (to exercise dedupe) — with a real listing price."""
    return [
        {  # listed_alive, +8%
            "issuer": "Listed Core Alpha Ltd",
            "issue_date": _d("2019-03-01"),
            "listing_date": _d("2019-03-12"),
            "issue_price": 100.0,
            "listing_day_close": 108.0,
            "status_raw": "listed",
        },
        {  # delisted, +4% (a genuine non-survivor in the listed core)
            "issuer": "Listed Core Gamma Ltd",
            "issue_date": _d("2018-06-01"),
            "listing_date": _d("2018-06-15"),
            "issue_price": 150.0,
            "listing_day_close": 156.0,
            "status_raw": "delisted",
        },
        {  # collides with a withdrawn-overlay row (same issuer+issue_date), +7%
            "issuer": "Both Sources Ltd",
            "issue_date": _d("2020-05-01"),
            "listing_date": _d("2020-05-14"),
            "issue_price": 200.0,
            "listing_day_close": 214.0,
            "status_raw": "listed",
        },
    ]


def _fake_sebi_withdrawn() -> list[dict]:
    """Source B stand-in (the P3 withdrawn/pulled overlay). One overlay-only issuer
    (must survive) + one that collides with the listed core (must be deduped)."""
    return [
        {  # overlay-only: never listed -> withdrawn survives, NaN return, RETAINED
            "issuer": "Withdrawn Only Ltd",
            "issue_date": _d("2021-02-01"),
            "listing_date": None,
            "issue_price": 120.0,
            "listing_day_close": None,
            "status_raw": "withdrawn",
        },
        {  # collides with "Both Sources Ltd" — listed core must win (its price kept)
            "issuer": "Both Sources Ltd",
            "issue_date": _d("2020-05-01"),
            "listing_date": None,
            "issue_price": None,
            "listing_day_close": None,
            "status_raw": "withdrawn",
        },
    ]


def test_two_source_merge_yields_survivorship_panel(monkeypatch):
    """build_panel merges NSE listed-core (Source A) with the SEBI/withdrawn overlay
    (Source B); the built panel keeps withdrawn AND a listed/delisted mix (P3)."""
    from pipelines.historical import build

    monkeypatch.setattr(
        build._sources, "fetch_nse_past_issues", _fake_nse_past_issues, raising=True
    )
    monkeypatch.setattr(
        build._sources, "fetch_sebi_withdrawn", _fake_sebi_withdrawn, raising=True
    )
    # Guard: no live network under pytest — the primary chittorgarh path is retired.
    monkeypatch.setattr(
        build._sources,
        "fetch_chittorgarh_index",
        lambda: (_ for _ in ()).throw(AssertionError("primary path must not be called")),
        raising=True,
    )

    df = build.build_panel(write=False)

    counts = df["status"].value_counts().to_dict()
    # P3: the withdrawn overlay survives the merge (non-zero withdrawn count).
    assert counts.get("withdrawn", 0) > 0
    # A real listed/delisted mix from the listed core — NOT a survivor-only universe.
    assert counts.get("delisted", 0) > 0
    assert counts.get("listed_alive", 0) > 0

    # Dedupe by (issuer, issue_date): the issuer present in BOTH sources collapses to
    # one row, and the listed-core row wins (its listing price is kept, not the
    # overlay's NaN) — so its return is the +7% listed value, status listed_alive.
    both = df.loc[df["issuer"] == "Both Sources Ltd"]
    assert len(both) == 1
    assert both.iloc[0]["status"] == "listed_alive"
    assert both.iloc[0]["listing_day_return"] == pytest.approx(0.07)

    # Row count == inputs minus the single dedupe collision only
    # (3 listed + 2 withdrawn - 1 collision = 4). Nothing dropped for NaN.
    assert len(df) == 4

    # Replace-with-NaN survivorship: the withdrawn-only IPO is RETAINED as a NaN row.
    zeta = df.loc[df["issuer"] == "Withdrawn Only Ltd"].iloc[0]
    assert math.isnan(zeta["listing_day_return"])
    assert df["listing_day_return"].isna().any()
    # (The primary chittorgarh path is guarded above — build_panel calling it would
    #  have raised AssertionError before we got here, proving the D5-04 repoint.)


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
    not _SAMPLE_PARQUET.exists(),
    reason="panel parquet not built yet (Task 2 / 05-11 live crawl)",
)
def test_committed_panel_valid_taxonomy_survivorship_and_a_nan_row():
    # The committed data/historical/ipo_panel.parquet is the REAL 05-11 live
    # survivorship panel (the hand-crafted seed SAMPLE was replaced by the live
    # crawl). It need NOT carry every taxonomy value — the real NSE + withdrawn
    # universe produced only {listed_alive, withdrawn} — but it MUST use only valid
    # statuses, MUST retain non-survivors (P3), and MUST keep a NaN-return row.
    df = coerce_panel(pd.read_parquet(_SAMPLE_PARQUET))
    assert list(df.columns) == list(PANEL_COLUMNS)
    # Only valid taxonomy values (never a fabricated status).
    assert set(df["status"].dropna().unique()) <= STATUS_VALUES
    # Survivorship overlay is non-empty: at least one non-survivor row is retained
    # (P3 — a pure listed_alive panel would BE the survivorship bias this guards).
    assert set(df["status"].dropna().unique()) - {"listed_alive"}
    assert df["listing_day_return"].isna().any()  # survivorship NaN retained
    # The committed panel's median stays within the ~7% MAAR sanity band (no flag).
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


# ---------------------------------------------------------------------------
# 5. Live-source contract fixes (05-11) — confirmed at the live pull, proven
#    OFFLINE here (canned payloads / monkeypatched fetchers, no network):
#      - coerce_date handles the DD-Mon-YYYY shape both live sources use
#      - the NSE parser maps the CONFIRMED keys (ipoStartDate) and keeps `symbol`
#      - the chittorgarh withdrawn overlay is parsed from the webnodejs JSON API
#      - build_panel enriches the listing-day close (the previously-unwired target)
# ---------------------------------------------------------------------------


def test_coerce_date_parses_dd_mon_yyyy_from_both_live_sources():
    # NSE past-issues DD-MON-YYYY (uppercase) + chittorgarh DD-Mon-YYYY.
    assert _S.coerce_date("14-JUL-2026") == dt.date(2026, 7, 14)
    assert _S.coerce_date("19-Aug-2024") == dt.date(2024, 8, 19)
    assert _S.coerce_date("01-May-2025") == dt.date(2025, 5, 1)
    # Still None on junk (never fabricated).
    assert _S.coerce_date("-") is None
    assert _S.coerce_date("not a date") is None


def test_parse_nse_past_issue_maps_confirmed_keys_and_keeps_symbol():
    row = _S._parse_nse_past_issue(
        {
            "company": "Example Foods Limited",
            "symbol": "EXFOODS",
            "htmSym": "exfoods",
            "ipoStartDate": "05-AUG-2024",
            "listingDate": "12-AUG-2024",
            "issuePrice": "240",
            "priceRange": "Rs.230 to Rs.240",
            "securityType": "EQ",
        }
    )
    assert row["issuer"] == "Example Foods Limited"
    assert row["symbol"] == "EXFOODS"  # threaded for listing-day-close enrichment
    assert row["issue_date"] == dt.date(2024, 8, 5)  # ipoStartDate — NOT None
    assert row["listing_date"] == dt.date(2024, 8, 12)
    assert row["issue_price"] == pytest.approx(240.0)
    # A not-yet-priced upcoming row: issuePrice/listingDate "-" => None (never faked).
    upcoming = _S._parse_nse_past_issue(
        {
            "company": "Upcoming Ltd",
            "symbol": "UPC",
            "ipoStartDate": "14-JUL-2026",
            "listingDate": "-",
            "issuePrice": "-",
        }
    )
    assert upcoming["issue_date"] == dt.date(2026, 7, 14)
    assert upcoming["listing_date"] is None
    assert upcoming["issue_price"] is None


_CHITTORGARH_202_PAYLOAD = {
    "msg": 1,
    "reportTableData": [
        {
            "Company": (
                '<a href="https://www.chittorgarh.com/ipo/ecom-express-ipo/2235/" '
                'title="Ecom Express Ltd. IPO Offer Document Withdrawn">'
                "Ecom Express Ltd. </a>"
            ),
            "Offer Type": "IPO",
            "Offer Document Filed with SEBI": "19-Aug-2024",
            "Offer Document Withdrawn": "01-May-2025",
        },
        {
            "Company": '<a href="/ipo/foo/1/">Foo Industries Ltd</a>',
            "Offer Type": "IPO",
            "Offer Document Filed with SEBI": "03-Feb-2023",
        },
    ],
}


def test_parse_chittorgarh_withdrawn_payload_extracts_issuer_and_marks_withdrawn():
    rows = _S.parse_chittorgarh_withdrawn_payload(_CHITTORGARH_202_PAYLOAD)
    assert len(rows) == 2
    assert rows[0]["issuer"] == "Ecom Express Ltd."  # from the HTML anchor text
    assert rows[0]["issue_date"] == dt.date(2024, 8, 19)  # DD-Mon-YYYY parsed
    assert all(r["status_raw"] == "withdrawn" for r in rows)
    # Empty / non-dict payloads yield no rows (never fabricated).
    assert _S.parse_chittorgarh_withdrawn_payload({}) == []
    assert _S.parse_chittorgarh_withdrawn_payload(None) == []


def test_recent_fy_end_years_are_contiguous_indian_fys():
    yrs = _S._recent_fy_end_years(back=5)
    assert len(yrs) == 5
    assert yrs == sorted(yrs)
    assert yrs[-1] - yrs[0] == 4


def test_fetch_chittorgarh_withdrawn_dedupes_across_fys(monkeypatch):
    import json as _json

    # Same payload for every FY -> the two issuers must collapse (dedupe), not
    # multiply by the number of financial years iterated.
    monkeypatch.setattr(
        _S, "_get", lambda url, **kw: _json.dumps(_CHITTORGARH_202_PAYLOAD), raising=True
    )
    monkeypatch.setattr(_S, "_save_raw", lambda *a, **k: None, raising=True)
    rows = _S._fetch_chittorgarh_withdrawn()
    assert {r["issuer"] for r in rows} == {"Ecom Express Ltd.", "Foo Industries Ltd"}
    assert all(r["status_raw"] == "withdrawn" for r in rows)


def test_build_panel_enriches_listing_closes_into_the_target(monkeypatch):
    """The 05-11 fix: NSE past-issues carries no listing close, so build_panel must
    enrich it per symbol — otherwise listing_day_return is all-NaN and the
    walk-forward has zero scorable rows."""
    from pipelines.historical import build

    def _nse(from_date, to_date):
        return [
            {
                "issuer": "Enrich Me Ltd",
                "symbol": "ENRICH",
                "issue_date": _d("2023-05-01"),
                "listing_date": _d("2023-05-10"),
                "issue_price": 100.0,
                "listing_day_close": None,
                "status_raw": "listed",
            },
            {
                "issuer": "No Symbol Ltd",
                "symbol": None,  # can't be enriched -> stays NaN (retained)
                "issue_date": _d("2023-06-01"),
                "listing_date": _d("2023-06-10"),
                "issue_price": 50.0,
                "listing_day_close": None,
                "status_raw": "listed",
            },
        ]

    closes = {"ENRICH": 115.0}  # +15%; unknown symbols => None (miss, retained NaN)
    monkeypatch.setattr(build._sources, "fetch_nse_past_issues", _nse, raising=True)
    monkeypatch.setattr(build._sources, "fetch_sebi_withdrawn", lambda: [], raising=True)
    monkeypatch.setattr(
        build._sources, "fetch_listing_day_close",
        lambda sym, d: closes.get(sym), raising=True,
    )

    df = build.build_panel(write=False)
    enrich = df.loc[df["issuer"] == "Enrich Me Ltd"].iloc[0]
    assert enrich["listing_day_close"] == pytest.approx(115.0)
    assert enrich["listing_day_return"] == pytest.approx(0.15)  # target now KNOWN
    # The symbol-less row can't be enriched -> stays NaN (retained, never fabricated).
    nosym = df.loc[df["issuer"] == "No Symbol Ltd"].iloc[0]
    assert math.isnan(nosym["listing_day_return"])
