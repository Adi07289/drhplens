"""
tests/unit/test_panel_sanity_summary.py — the /methodology-ready survivorship
sanity summary (04-07 / SC-5).

`panel_sanity_summary` wraps `sanity_check_median` + `band_text` into a render-ready
dict the committed `data/historical/panel_sanity.json` is built from. The honest
contract: it reports the REAL median + verdict — within the `[-5%, +20%]` band means
`flag is None` (no fabricated divergence); a median past the 20% survivor-inflation
threshold fires the plain-text flag.
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipelines.historical.validate import panel_sanity_summary


def test_within_band_reports_no_flag():
    df = pd.DataFrame({"listing_day_return": [0.05, 0.08, 0.10, 0.12, float("nan")]})
    s = panel_sanity_summary(df)
    assert s["within_band"] is True
    assert s["flag"] is None
    assert s["n_scored"] == 4  # the NaN row is excluded from the statistic (not dropped)
    assert s["median_pct"] == pytest.approx(9.0)  # median of [0.05,0.08,0.10,0.12] = 0.09
    assert s["baseline_pct"] == pytest.approx(7.19)
    assert "MAAR" in s["methodology"]


def test_survivor_inflation_fires_flag():
    # median 0.29 > the 20% survivor-inflation threshold
    df = pd.DataFrame({"listing_day_return": [0.25, 0.28, 0.30, 0.40]})
    s = panel_sanity_summary(df)
    assert s["within_band"] is False
    assert s["flag"] is not None
    assert "survivorship" in s["flag"].lower()


def test_committed_panel_passes_survivorship_sanity():
    """The REAL committed panel: median above the 7.19% point estimate but WITHIN the
    band (no survivor inflation) — the honest SC-5 result surfaced on /methodology."""
    from tests.unit.test_historical_panel import _SAMPLE_PARQUET, coerce_panel

    if not _SAMPLE_PARQUET.exists():
        pytest.skip("committed panel not built")
    df = coerce_panel(pd.read_parquet(_SAMPLE_PARQUET))
    s = panel_sanity_summary(df)
    assert s["within_band"] is True
    assert s["flag"] is None
    assert 7.19 < s["median_pct"] < 20.0  # above the point estimate, inside the band
