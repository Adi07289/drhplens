"""
scripts/backfill_mlflow_run.py — retrospective MLflow run for the 05-11 live walk-forward.

The 05-11 live walk-forward (2026-07-25) was an ad-hoc supervised run: it persisted the
real held-out frame + gate verdict (``data/forecasts/_gate/{oos_real.parquet,release_gate.json}``)
and the real model card (``model_card/card_data.json``), but did NOT commit an ``mlruns/``
tracking run (the 05-11 acceptance criterion for DS-rigor visibility). This script closes
that gap **honestly**: it logs ONLY the real metrics already committed in those artifacts to a
local-file-backend MLflow run — it does NOT re-run the walk-forward and fabricates nothing.

Every value logged is read from a committed source of truth:
  - model_card/card_data.json      — coverage, MAE, per-year RMSE, R2, windows, features, seed
  - data/forecasts/_gate/release_gate.json — the P9 verdict + per-baseline Diebold-Mariano stats

The run is tagged ``backfill=true`` and ``gate_passed=false`` so it can never be mistaken for a
fresh passing run. Deterministic + re-runnable (uses the fixed run_name, so re-running updates
the same logical experiment rather than fabricating history).

Usage:  PYTHONPATH=. .venv/bin/python -m scripts.backfill_mlflow_run
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# The repo's DS-rigor design (CLAUDE.md deploy plan) commits a local file-backend
# ``mlruns/`` run. mlflow >=3 puts the file store in "maintenance mode" and raises
# unless this opt-out is set — do it before importing mlflow so the file backend works.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import mlflow

_REPO = Path(__file__).resolve().parents[1]
_CARD = _REPO / "model_card" / "card_data.json"
_GATE = _REPO / "data" / "forecasts" / "_gate" / "release_gate.json"
_MLRUNS = _REPO / "mlruns"


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main() -> None:
    if not _CARD.is_file() or not _GATE.is_file():
        raise SystemExit("committed card_data.json / release_gate.json missing — run 05-11 first.")

    card = json.loads(_CARD.read_text(encoding="utf-8"))
    gate = json.loads(_GATE.read_text(encoding="utf-8"))

    mlflow.set_tracking_uri(f"file:{_MLRUNS}")
    mlflow.set_experiment("drhplens-listing-forecaster")

    with mlflow.start_run(run_name="05-11-live-walkforward-backfill"):
        # --- params (all from card_data.json) ---
        params = {
            "model_version": card.get("model_version"),
            "seed": card.get("seed"),
            "training_window": card.get("training_window"),
            "backtest_window": card.get("backtest_window"),
            "n_scored": card.get("n_scored"),
            "n_selected_features": len(card.get("selected_features") or []),
            "selected_features": ",".join(card.get("selected_features") or []),
        }
        mlflow.log_params({k: v for k, v in params.items() if v is not None})

        # --- headline metrics (real held-out numbers) ---
        for key in ("coverage", "mae_pts", "r2"):
            val = _num(card.get(key))
            if val is not None:
                mlflow.log_metric(key, val)

        # --- per-year RMSE ---
        for year, rmse in (card.get("per_year_rmse") or {}).items():
            v = _num(rmse)
            if v is not None:
                mlflow.log_metric(f"rmse_{year}", v)

        # --- per-baseline Diebold-Mariano verdicts (from the gate) ---
        for name, d in (gate.get("per_baseline") or {}).items():
            if not isinstance(d, dict):
                continue
            if _num(d.get("dm_stat")) is not None:
                mlflow.log_metric(f"dm_{name}_stat", _num(d["dm_stat"]))
            if _num(d.get("p_value")) is not None:
                mlflow.log_metric(f"dm_{name}_pvalue", _num(d["p_value"]))
            mlflow.log_metric(
                f"baseline_beats_model_{name}",
                1.0 if d.get("baseline_beats_model_sig") else 0.0,
            )

        # --- honest tags: this is a retrospective backfill of a FAILING gate ---
        mlflow.set_tags({
            "backfill": "true",
            "source_run_date": "2026-07-25",
            "gate_passed": str(gate.get("passed")).lower(),
            "r2_alarm": str(gate.get("r2_alarm")),
            "honest_note": "one-feature live model; baselines beat it (D5-01); NOT p-hacked to pass",
        })

        # attach the committed evidence as artifacts (pointers, not new numbers)
        mlflow.log_artifact(str(_GATE), artifact_path="gate")
        mlflow.log_artifact(str(_CARD), artifact_path="card")

    passed = gate.get("passed")
    print(f"logged retrospective MLflow run to {_MLRUNS} — "
          f"gate_passed={passed}, coverage={card.get('coverage')}, r2={card.get('r2')}")


if __name__ == "__main__":
    main()
