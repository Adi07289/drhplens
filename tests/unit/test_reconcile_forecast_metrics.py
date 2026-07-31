"""
tests/unit/test_reconcile_forecast_metrics.py — reconcile committed forecast
records' GLOBAL metrics to the live backtest (05-11 quick task).

The forecaster FAILED its P9 gate, so the per-IPO records keep their honest
illustrative SEED band + abstain posture (D5-01). But the GLOBAL metrics block is
D5-12 "identical across every page" and describes the model's REAL tested behavior,
so it must be the live walk-forward numbers. `live_metrics` builds that block from
the committed live OOS frame; `reconcile_record_metrics` swaps ONLY that block into
a record, preserving the band / abstain / model_version / everything-else verbatim.
"""
from __future__ import annotations

from pipelines.forecast import load_forecast
from pipelines.forecast.diagnostics import global_metrics
from pipelines.forecast.reconcile import live_metrics, reconcile_record_metrics
from tests.unit.fixtures.forecast_fixtures import oos_rows


def test_live_metrics_matches_global_metrics_and_year_span():
    oos = oos_rows()
    gm = global_metrics(oos)
    lm = live_metrics(oos)

    assert lm.coverage_empirical == gm["coverage_empirical"]
    assert lm.mae_pts == gm["mae_pts"]
    assert lm.n == gm["n"]
    assert lm.per_year_rmse == {str(k): v for k, v in gm["per_year_rmse"].items()}
    # backtest_window is the scored-year SPAN (min-max of the years actually
    # attributed) — never a fabricated range.
    years = sorted(int(y) for y in gm["per_year_rmse"])
    assert lm.backtest_window == f"{years[0]}-{years[-1]}"


def test_reconcile_replaces_only_metrics_preserving_band_and_abstain():
    rec = load_forecast("swiggy_2024_11")
    before_interval = rec.interval
    before_version = rec.model_version
    before_abstain = rec.abstain
    before_sector = rec.sector

    new_metrics = live_metrics(oos_rows())
    out = reconcile_record_metrics(rec, new_metrics)

    assert out.metrics == new_metrics            # the global metrics block is replaced
    assert out.interval == before_interval       # per-IPO band preserved (seed illustrative)
    assert out.abstain == before_abstain         # abstain posture preserved
    assert out.model_version == before_version   # not touched (out of scope)
    assert out.sector == before_sector
