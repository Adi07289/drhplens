"""
Integration smoke — yfinance 1.5.1 `.NS`/`.BO` Ticker.info key coverage (04-01).

Validates the yfinance rung of the D4-05 peer-multiples source ladder (PEER-02):
that `yfinance.Ticker("RELIANCE.NS").info` is a non-empty dict and the four keys
the peer pipeline (04-03 `pipelines/peer_sources.py`) reads are present-as-number
or explicitly-absent — never a silent wrong type.

Observed `.info` keys the peer pipeline relies on (confirm/update from the live run):
    trailingPE          -> P/E
    priceToBook         -> P/B
    enterpriseToEbitda  -> EV/EBITDA
    returnOnEquity      -> ROE

Live network + package required, so it is SKIPPED unless `NSE_LIVE_SMOKE=1`. It runs
in the nightly `nightly-nse.yml` workflow and in the 04-01 Task 3 live spike; the
default `pytest tests/unit` run never collects it and a plain `pytest -q` skips it.
"""
from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("NSE_LIVE_SMOKE") != "1",
        reason="live NSE/Yahoo smoke — set NSE_LIVE_SMOKE=1 to run (nightly CI / 04-01 spike)",
    ),
]

PEER_MULTIPLE_KEYS = ("trailingPE", "priceToBook", "enterpriseToEbitda", "returnOnEquity")


def test_yfinance_reliance_info_has_peer_multiple_keys() -> None:
    yf = pytest.importorskip("yfinance")
    assert yf.__version__ == "1.5.1", f"expected yfinance 1.5.1, got {yf.__version__}"

    info = yf.Ticker("RELIANCE.NS").info
    assert isinstance(info, dict) and info, "RELIANCE.NS .info returned empty/non-dict"

    for key in PEER_MULTIPLE_KEYS:
        if key in info and info[key] is not None:
            # Present -> must be numeric (never a silent wrong type, P15).
            assert isinstance(info[key], (int, float)), (
                f"{key} present but non-numeric ({type(info[key]).__name__}): {info[key]!r}"
            )
        # Absent is acceptable and expected for some peers — the peer pipeline
        # renders an honest '—' for a missing multiple (D4-05).
