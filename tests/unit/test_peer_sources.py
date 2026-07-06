"""
Unit test — the peer-multiples source-priority ladder (PEER-02, D4-05).

Fully offline: every source fetcher is monkeypatched — NO live network / HTTP
happens under tests/unit (CODE-NOW-DEFER; the live peer precompute is a deferred
human runbook step). Pins:
  - the ladder returns the FIRST available value per cell and records its source
    flag (screener `s` → yfinance `y` → NSE/BSE `n`)
  - a metric missing from every source is PeerCell(value=None, source=None) — never
    interpolated, never zero
  - yfinance 0/None/NaN for a ratio is coerced to missing (P15)
  - yfinance returnOnEquity is a FRACTION → stored as percent (×100)
  - a negative/undefined P/E is preserved as the NM sentinel (value None,
    not_meaningful True), a negative ROE stays a real value
  - only hard-coded source hostnames are referenced (no URL derived from input — SSRF)
"""
from __future__ import annotations

import pipelines.peer_sources as ps
from agent.peer_schema import PeerCell, PeerMetric


def _all_none() -> dict:
    return {"pe": None, "pb": None, "ev_ebitda": None, "roe": None}


def _patch_ladder(monkeypatch, *, screener, yfinance, nse) -> None:
    monkeypatch.setattr(ps, "screener_multiples", lambda name: screener, raising=True)
    monkeypatch.setattr(ps, "yfinance_multiples", lambda ticker: yfinance, raising=True)
    monkeypatch.setattr(ps, "nse_multiples", lambda ticker: nse, raising=True)


def _cell(metrics: list[PeerMetric], key: str) -> PeerCell:
    return next(m for m in metrics if m.metric == key).current


def test_ladder_prefers_screener_and_records_source(monkeypatch) -> None:
    screener = {**_all_none(), "pe": 25.0}
    yfinance = {**_all_none(), "pe": 99.0}  # must NOT win — screener has it
    _patch_ladder(monkeypatch, screener=screener, yfinance=yfinance, nse=_all_none())

    metrics = ps.resolve_multiples("Zomato Limited", ticker="ZOMATO.NS")
    pe = _cell(metrics, "pe")
    assert pe.value == 25.0
    assert pe.source == "s"
    assert pe.as_of == "current"


def test_falls_through_to_yfinance(monkeypatch) -> None:
    screener = _all_none()  # screener misses pe
    yfinance = {**_all_none(), "pe": 30.0}
    _patch_ladder(monkeypatch, screener=screener, yfinance=yfinance, nse=_all_none())

    pe = _cell(ps.resolve_multiples("X Ltd", ticker="X.NS"), "pe")
    assert pe.value == 30.0
    assert pe.source == "y"


def test_falls_through_to_nse(monkeypatch) -> None:
    nse = {**_all_none(), "pb": 4.2}
    _patch_ladder(monkeypatch, screener=_all_none(), yfinance=_all_none(), nse=nse)

    pb = _cell(ps.resolve_multiples("X Ltd", ticker="X.NS"), "pb")
    assert pb.value == 4.2
    assert pb.source == "n"


def test_missing_from_all_sources_is_none_cell(monkeypatch) -> None:
    _patch_ladder(monkeypatch, screener=_all_none(), yfinance=_all_none(), nse=_all_none())

    ev = _cell(ps.resolve_multiples("X Ltd", ticker="X.NS"), "ev_ebitda")
    assert ev.value is None
    assert ev.source is None
    assert ev.not_meaningful is False  # missing, NOT not-meaningful


def test_resolve_returns_all_four_metrics_in_order(monkeypatch) -> None:
    _patch_ladder(monkeypatch, screener=_all_none(), yfinance=_all_none(), nse=_all_none())
    metrics = ps.resolve_multiples("X Ltd", ticker="X.NS")
    assert [m.metric for m in metrics] == ["pe", "pb", "ev_ebitda", "roe"]


def test_negative_pe_becomes_nm_sentinel(monkeypatch) -> None:
    screener = {**_all_none(), "pe": -8.0}  # loss-making issuer
    _patch_ladder(monkeypatch, screener=screener, yfinance=_all_none(), nse=_all_none())

    pe = _cell(ps.resolve_multiples("X Ltd", ticker="X.NS"), "pe")
    assert pe.not_meaningful is True
    assert pe.value is None  # NM is never a fabricated / misleading number
    assert pe.source == "s"  # but we still record which source reported it


def test_negative_roe_stays_a_real_value(monkeypatch) -> None:
    screener = {**_all_none(), "roe": -12.3}  # a real negative ROE, not NM
    _patch_ladder(monkeypatch, screener=screener, yfinance=_all_none(), nse=_all_none())

    roe = _cell(ps.resolve_multiples("X Ltd", ticker="X.NS"), "roe")
    assert roe.value == -12.3
    assert roe.not_meaningful is False
    assert roe.source == "s"


# ---------------------------------------------------------------------------
# yfinance_multiples coercion (P15) — monkeypatch the Ticker, no live Yahoo
# ---------------------------------------------------------------------------


class _FakeTicker:
    def __init__(self, info: dict) -> None:
        self.info = info


def test_yfinance_zero_and_none_and_nan_coerced_to_missing(monkeypatch) -> None:
    info = {
        "trailingPE": 0,          # a "0 ratio" is treated as missing (P15)
        "priceToBook": None,      # absent
        "enterpriseToEbitda": float("nan"),  # NaN
        "returnOnEquity": 0.0,    # 0 fraction -> missing
    }
    import yfinance as yf

    monkeypatch.setattr(yf, "Ticker", lambda ticker: _FakeTicker(info), raising=True)
    out = ps.yfinance_multiples("RELIANCE.NS")
    assert out == {"pe": None, "pb": None, "ev_ebitda": None, "roe": None}


def test_yfinance_roe_fraction_converted_to_percent(monkeypatch) -> None:
    info = {
        "trailingPE": 22.12,
        "priceToBook": 1.98,
        "enterpriseToEbitda": 12.17,
        "returnOnEquity": 0.0914,  # FRACTION — must be ×100 for percent display
    }
    import yfinance as yf

    monkeypatch.setattr(yf, "Ticker", lambda ticker: _FakeTicker(info), raising=True)
    out = ps.yfinance_multiples("RELIANCE.NS")
    assert out["pe"] == 22.12
    assert out["pb"] == 1.98
    assert out["ev_ebitda"] == 12.17
    assert abs(out["roe"] - 9.14) < 1e-6  # 0.0914 -> 9.14 %


def test_yfinance_empty_info_all_none(monkeypatch) -> None:
    import yfinance as yf

    monkeypatch.setattr(yf, "Ticker", lambda ticker: _FakeTicker({}), raising=True)
    assert ps.yfinance_multiples("UNKNOWN.NS") == _all_none()


# ---------------------------------------------------------------------------
# SSRF control — only hard-coded hostnames are ever fetched
# ---------------------------------------------------------------------------


def test_only_hardcoded_source_hosts_no_input_derived_url() -> None:
    import inspect
    import re

    src = inspect.getsource(ps)
    # The primary source host is hard-coded, not derived from any argument.
    assert "screener.in" in src
    # Every literal http(s) URL in the module points at a hard-coded, known host
    # (SSRF control T-04-03-SSRF) — no scheme is ever assembled from user/DRHP input.
    allowed_hosts = ("screener.in", "nseindia.com", "bseindia.com")
    for url in re.findall(r"https?://[^\s\"')]+", src):
        assert any(h in url for h in allowed_hosts), f"non-allow-listed URL literal: {url}"


def test_import_is_network_safe() -> None:
    """Importing the module performs no network I/O and constructs no session at
    import time (all fetching is lazy, inside the fetchers)."""
    import importlib

    mod = importlib.reload(ps)
    assert hasattr(mod, "resolve_multiples")
    assert hasattr(mod, "screener_multiples")
