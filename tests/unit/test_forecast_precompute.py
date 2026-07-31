"""
Unit test — the forecast pre-compute CLI writes one ``data/forecasts/<id>.json``
per catalogue IPO (its OWN out-of-sample band + the SHARED global metrics + as-of/OOS
provenance), offline-testably, AND tracks the global metrics to a local MLflow run
(FCAST-01 / FCAST-04 / D5-11 / D5-12).

Fully offline: ``walk_forward`` is monkeypatched to a small crafted out-of-sample
frame (in the walk-forward's native FRACTION units) — NO training, NO network. The
pre-compute multiplies by 100 at the model→record boundary, so a crafted band of
``low=-0.042/median=0.061/high=0.217`` becomes the ``-4.2 / 6.1 / 21.7`` percentage
points that match the hand-seeded ``data/forecasts/swiggy_2024_11.json`` shape.

Pins: each catalogue record carries its own band + the identical global metrics
(D5-12); an abstained IPO fabricates no interval; the writer is allow-list gated
before path formation (T-05-06-PATH); a single corrupt IPO is isolated without
aborting the batch (P14); and with tracking on, an ``mlflow.start_run()`` logs
coverage/MAE to a local file-backend ``mlruns/`` (a tmp dir — no server).
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipelines.forecast import precompute


def _crafted_oos() -> pd.DataFrame:
    """A small out-of-sample frame in FRACTION units (as walk_forward emits).

    Three non-catalogue scored rows drive the GLOBAL metrics; three catalogue rows
    exercise covered / abstain / corrupt. Scored (banded, non-abstain) coverage is
    3 of 4 -> 0.75; scored years {2016, 2017, 2018, 2024} -> window "2016-2024".
    """
    return pd.DataFrame(
        [
            # --- non-catalogue scored rows (global metrics only) ---
            {"drhp_id": "synth_2016", "issuer": "A Ltd", "actual": 0.10, "low": -0.05,
             "high": 0.20, "median": 0.06, "listing_year": 2016, "abstain": False,
             "abstain_reason": None},
            {"drhp_id": "synth_2017", "issuer": "B Ltd", "actual": 0.30, "low": 0.00,
             "high": 0.25, "median": 0.12, "listing_year": 2017, "abstain": False,
             "abstain_reason": None},  # NOT covered (0.30 > 0.25)
            {"drhp_id": "synth_2018", "issuer": "C Ltd", "actual": -0.05, "low": -0.10,
             "high": 0.00, "median": -0.03, "listing_year": 2018, "abstain": False,
             "abstain_reason": None},
            # --- catalogue: covered ---
            {"drhp_id": "swiggy_2024_11", "issuer": "Swiggy Limited", "actual": 0.10,
             "low": -0.042, "high": 0.217, "median": 0.061, "listing_year": 2024,
             "abstain": False, "abstain_reason": None},
            # --- catalogue: abstain (no band) ---
            {"drhp_id": "hyundai_2024_10", "issuer": "Hyundai", "actual": 0.05,
             "low": float("nan"), "high": float("nan"), "median": float("nan"),
             "listing_year": 2024, "abstain": True,
             "abstain_reason": "insufficient_history"},
            # --- catalogue: CORRUPT (covered flag but NaN band) -> isolated ---
            {"drhp_id": "ola_electric_2024_08", "issuer": "Ola", "actual": 0.07,
             "low": float("nan"), "high": float("nan"), "median": float("nan"),
             "listing_year": 2024, "abstain": False, "abstain_reason": None},
        ]
    )


@pytest.fixture
def patched_walk_forward(monkeypatch):
    """Monkeypatch precompute.walk_forward to the crafted OOS frame (no model)."""
    monkeypatch.setattr(precompute, "walk_forward", lambda *a, **k: _crafted_oos())


# ---------------------------------------------------------------------------
# (a) each catalogue record carries its own band + the SHARED global metrics
# ---------------------------------------------------------------------------


def test_records_carry_own_band_and_shared_global_metrics(
    patched_walk_forward, forecast_synthetic_panel
) -> None:
    results = precompute.precompute_forecasts(
        panel=forecast_synthetic_panel, write=False, track=False
    )

    # covered swiggy + abstain hyundai produced; corrupt ola isolated; the 5 other
    # catalogue IPOs have no out-of-sample row -> skipped.
    assert set(results) == {"swiggy_2024_11", "hyundai_2024_10"}

    swiggy = results["swiggy_2024_11"]
    assert swiggy.is_abstain is False
    assert swiggy.interval is not None
    # the walk-forward fraction band -> percentage points (x100), matching the seed
    assert swiggy.interval.low_pct == -4.2
    assert swiggy.interval.high_pct == 21.7
    assert swiggy.interval.median_pct == 6.1
    assert swiggy.interval.width_pts == 25.9
    # provenance
    assert swiggy.out_of_sample is True
    assert swiggy.walk_forward is True
    assert swiggy.model_version == "cqr-xgb-2026.07-v1"
    assert swiggy.sector == "Food delivery"  # from the catalogue
    assert swiggy.as_of_listing_date == "2024-11"  # catalogue listing date

    # GLOBAL metrics — the REAL held-out coverage (3 of 4 scored covered = 0.75)
    assert swiggy.metrics.coverage_empirical == 0.75
    assert swiggy.metrics.n == 4
    assert swiggy.metrics.backtest_window == "2016-2024"
    assert set(swiggy.metrics.per_year_rmse) == {"2016", "2017", "2018", "2024"}

    # D5-12: the metrics block is IDENTICAL across every IPO page
    hyundai = results["hyundai_2024_10"]
    assert hyundai.metrics == swiggy.metrics


# ---------------------------------------------------------------------------
# (b) an abstained IPO fabricates no interval
# ---------------------------------------------------------------------------


def test_abstained_ipo_has_no_fabricated_interval(
    patched_walk_forward, forecast_synthetic_panel
) -> None:
    results = precompute.precompute_forecasts(
        panel=forecast_synthetic_panel, write=False, track=False
    )
    hyundai = results["hyundai_2024_10"]

    assert hyundai.is_abstain is True
    assert hyundai.interval is None  # no fabricated band
    assert hyundai.abstain_reason == "insufficient_history"
    # still carries the shared global metrics (honest "how it was tested")
    assert hyundai.metrics.n == 4
    assert hyundai.metrics.coverage_empirical == 0.75


# ---------------------------------------------------------------------------
# (c) the writer gates drhp_id via the allow-list BEFORE forming any path
# ---------------------------------------------------------------------------


def test_writer_gates_unknown_drhp_id_before_path_formation() -> None:
    """The record write path (_forecast_path) rejects a non-allow-listed / traversal
    id BEFORE forming any data/forecasts path (T-05-06-PATH)."""
    with pytest.raises(ValueError):
        precompute._forecast_path("../../etc/passwd")
    with pytest.raises(ValueError):
        precompute._forecast_path("not_a_real_id")
    # a known id forms a path under the forecasts dir
    path = precompute._forecast_path("swiggy_2024_11")
    assert path.name == "swiggy_2024_11.json"


def test_precompute_one_cli_rejects_unknown_drhp_id() -> None:
    with pytest.raises(ValueError):
        precompute.precompute_one("../../etc/passwd")


# ---------------------------------------------------------------------------
# (d) per-IPO failure isolation — one corrupt IPO never aborts the batch (P14)
# ---------------------------------------------------------------------------


def test_per_ipo_failure_is_isolated(
    patched_walk_forward, forecast_synthetic_panel
) -> None:
    """The corrupt ola row (covered flag + NaN band) is logged + skipped; the covered
    and abstain records are still produced (P14)."""
    results = precompute.precompute_forecasts(
        panel=forecast_synthetic_panel, write=False, track=False
    )

    assert "ola_electric_2024_08" not in results  # the corrupt IPO was isolated
    assert "swiggy_2024_11" in results  # the batch did not abort
    assert "hyundai_2024_10" in results


# ---------------------------------------------------------------------------
# (e) write round-trip through the 05-03 codec + reader
# ---------------------------------------------------------------------------


def test_written_record_round_trips_via_load_forecast(
    patched_walk_forward, forecast_synthetic_panel, tmp_path, monkeypatch
) -> None:
    """write=True writes a record that load_forecast reconstructs byte-for-byte —
    the record keeps the render-compatible ForecastRecord JSON shape."""
    import pipelines.forecast as forecast_pkg

    monkeypatch.setattr(forecast_pkg, "FORECASTS_DIR", tmp_path, raising=True)

    precompute.precompute_forecasts(
        panel=forecast_synthetic_panel,
        write=True,
        track=False,
        only={"swiggy_2024_11"},
    )

    written = tmp_path / "swiggy_2024_11.json"
    assert written.exists()

    loaded = forecast_pkg.load_forecast("swiggy_2024_11")
    assert loaded.drhp_id == "swiggy_2024_11"
    assert loaded.interval is not None
    assert loaded.interval.low_pct == -4.2
    assert loaded.interval.high_pct == 21.7
    assert loaded.metrics.coverage_empirical == 0.75
    assert loaded.metrics.n == 4


# ---------------------------------------------------------------------------
# (f) MLflow tracking to a local file backend (tmp dir — no server)
# ---------------------------------------------------------------------------


def test_track_true_logs_global_metrics_to_local_mlflow(
    patched_walk_forward, forecast_synthetic_panel, tmp_path
) -> None:
    """With track=True against a tmp file:// tracking URI, precompute opens an
    mlflow run and logs coverage/MAE to the local file backend (no network, no
    server) — an mlruns/ run dir is created with the readable metrics."""
    import mlflow

    mlruns = tmp_path / "mlruns"
    original_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(mlruns.as_uri())
    try:
        precompute.precompute_forecasts(
            panel=forecast_synthetic_panel,
            write=False,
            track=True,
            only={"swiggy_2024_11"},
        )

        # a local mlruns run dir was created (file backend, no server)
        assert mlruns.exists()

        runs = mlflow.search_runs()
        assert not runs.empty
        assert "metrics.coverage_empirical" in runs.columns
        assert float(runs.iloc[0]["metrics.coverage_empirical"]) == 0.75
        assert "metrics.mae_pts" in runs.columns
        # a key CQR param was logged
        assert "params.confidence_level" in runs.columns
    finally:
        mlflow.set_tracking_uri(original_uri)
