"""
Integration smoke — jugaad-data 0.33.1 NSE endpoints (04-01).

Validates the exact endpoints the historical panel builder (04-07
`pipelines/historical/sources.py`) needs: a listing-day / historical equity candle
via `stock_df`, and an NSE bhavcopy for a known past trading date. On failure the
test FAILS with a maintainer-facing verdict — "jugaad-data endpoints broken as of
<run>; the historical builder must fall back to yfinance price data" (P15 / Pitfall-4
posture) — rather than silently degrading a precompute run.

Live network + package required, so it is SKIPPED unless `NSE_LIVE_SMOKE=1`. It runs
in the nightly `nightly-nse.yml` workflow and in the 04-01 Task 3 live spike.
"""
from __future__ import annotations

import datetime as _dt
import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("NSE_LIVE_SMOKE") != "1",
        reason="live NSE smoke — set NSE_LIVE_SMOKE=1 to run (nightly CI / 04-01 spike)",
    ),
]

# A known past NSE trading day (a Wednesday) — adjust if NSE calendar rejects it.
_KNOWN_TRADING_DAY = _dt.date(2024, 11, 20)


def test_jugaad_stock_df_returns_candles() -> None:
    """A historical equity candle series for a liquid symbol (the shape 04-07
    reads for a listing-day close)."""
    nse = pytest.importorskip("jugaad_data.nse")
    try:
        df = nse.stock_df(
            symbol="RELIANCE",
            from_date=_dt.date(2024, 11, 18),
            to_date=_dt.date(2024, 11, 22),
            series="EQ",
        )
    except Exception as exc:  # noqa: BLE001 — surface the drift verdict clearly
        pytest.fail(
            "jugaad-data stock_df endpoint broken as of this run "
            f"({type(exc).__name__}: {exc}); historical builder (04-07) must fall "
            "back to yfinance price data (P15)."
        )
    assert df is not None and len(df) > 0, "stock_df returned an empty candle series"


def test_jugaad_bhavcopy_available() -> None:
    """NSE bhavcopy for a known past trading date (the universe/price source
    04-07 sanity-checks against)."""
    nse = pytest.importorskip("jugaad_data.nse")
    fetch = getattr(nse, "bhavcopy_raw", None) or getattr(nse, "full_bhavcopy_raw", None)
    if fetch is None:
        pytest.fail(
            "jugaad-data exposes no bhavcopy_raw/full_bhavcopy_raw in 0.33.1; "
            "historical builder (04-07) must fall back to yfinance / BSE bhavcopy."
        )
    try:
        raw = fetch(_KNOWN_TRADING_DAY)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(
            "jugaad-data bhavcopy endpoint broken as of this run "
            f"({type(exc).__name__}: {exc}); fall back to yfinance / BSE (P15)."
        )
    assert raw, "bhavcopy fetch returned empty content"
