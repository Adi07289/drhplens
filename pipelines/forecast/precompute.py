"""
pipelines/forecast/precompute.py — the offline forecast pre-compute CLI: run the
as-of-T0 walk-forward ONCE, aggregate the GLOBAL honesty metrics ONCE, and
materialise one ``data/forecasts/<drhp_id>.json`` per catalogue IPO (FCAST-01 /
FCAST-04 / D5-11 / D5-12).

Mirrors ``pipelines/gmp.py`` and ``pipelines/snapshot.py``: an allow-list-gated
write path + a Typer CLI with per-IPO failure isolation (P14). The difference is
the single shared computation — the walk-forward and the global metrics are
computed once over the whole panel, then EVERY catalogue record carries:

  * its OWN out-of-sample band (D5-11: displayed band = backtested band), or a
    first-class ABSTAIN when the walk-forward declined a band — never a fabricated
    interval;
  * the IDENTICAL global metrics block (coverage / MAE / per-year RMSE, D5-12),
    the same numbers on every IPO page;
  * the as-of listing-date provenance + a pinned ``model_version``.

UNITS boundary: the walk-forward emits the raw FRACTION listing-day return (e.g.
``0.061`` for +6.1%), while the record + UI speak percentage POINTS (``6.1``). This
module multiplies the band + realized return by 100 (``RETURN_TO_PCT``) at the
model→record boundary before computing metrics or writing intervals, so the
committed records match the hand-seeded ``data/forecasts/swiggy_2024_11.json`` scale
and the 05-07 render keeps working.

Experiment tracking (the CLAUDE.md / RESEARCH lock): the single walk-forward +
global-metrics computation is wrapped in an ``mlflow.start_run()`` on the LOCAL
FILE backend (default ``mlruns/``; a tmp dir in tests). It logs the global
coverage/MAE/per-year-RMSE + the key CQR/XGBoost params. mlflow is imported LAZILY
inside the function and NO remote tracking URI is set — local file store only, no
server, no credentials, no network egress (T-05-06-MLF). Kept minimal: this is
DS-rigor visibility, not a tracking-server build.

CODE-NOW-DEFER: this module is fully unit-tested OFFLINE by monkeypatching
``walk_forward`` (no training, no network) with MLflow pointed at a tmp dir. The
REAL committed records + the committed ``mlruns/`` run are regenerated from the live
survivorship panel at the 05-11 checkpoint; the hand-seeded 05-01 records stay in
place until then.

ISOLATION (FCAST-02, Direction 2): the pre-compute consumes only the model / feature
/ metrics pipeline + the catalogue allow-list. It imports NOTHING from the GMP or
any display module — the predictor never sees the display signal.
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timezone

import pandas as pd
import typer
from rich.console import Console

from agent.forecast_schema import ForecastInterval, ForecastMetrics, ForecastRecord
from data.catalogue_loader import CatalogueIPO, is_known_drhp_id, load_catalogue
from pipelines.features.build import build_features
from pipelines.forecast import _forecast_path  # allow-list-gated write path (T-05-06-PATH)
from pipelines.forecast.diagnostics import global_metrics
from pipelines.forecast.model import CONFIDENCE_LEVEL, PARAMS, QUANTILE_ALPHAS
from pipelines.forecast.walkforward import (
    CAL_FRAC_DEFAULT,
    MIN_TRAIN_DEFAULT,
    walk_forward,
)

app = typer.Typer(help="DRHPLens listing-day-forecast pre-compute pipeline.")
console = Console()

# Pinned model + feature-set version (provenance for D5-11 reproducibility).
MODEL_VERSION: str = "cqr-xgb-2026.07-v1"

# The walk-forward speaks fraction listing-day return; the record + UI speak points.
RETURN_TO_PCT: float = 100.0

# The band columns converted from fraction to percentage points.
_PCT_COLUMNS = ("actual", "low", "high", "median")


# ---------------------------------------------------------------------------
# Panel loading (CODE-NOW-DEFER — the real survivorship panel is the 05-11 step)
# ---------------------------------------------------------------------------


def _load_panel() -> pd.DataFrame:
    """Assemble the real survivorship panel — DEFERRED to the 05-11 live build.

    The production panel comes from the Phase 4 historical build, which is blocked
    on source rot (see STATE.md 04-07) and regenerated at the 05-11 checkpoint.
    Until then, callers (and the offline tests) MUST pass ``panel=`` explicitly;
    invoking the CLI without a built panel raises this honest, actionable error
    rather than fabricating data.
    """
    raise RuntimeError(
        "precompute_forecasts needs a survivorship panel. The real panel build is "
        "the deferred 05-11 checkpoint (Phase 4 04-07 source rot); pass panel=... "
        "explicitly, or run the 05-11 live build first."
    )


# ---------------------------------------------------------------------------
# Model -> record conversion helpers
# ---------------------------------------------------------------------------


def _to_percent_frame(oos: pd.DataFrame) -> pd.DataFrame:
    """Convert the walk-forward band + realized return from fraction to points.

    The walk-forward emits ``listing_day_return`` in FRACTION units; the record and
    UI are in percentage POINTS. Multiplying by 100 here is the single units
    boundary (``RETURN_TO_PCT``). Abstain rows keep their NaN band (NaN * 100 = NaN).
    """
    df = oos.copy()
    for col in _PCT_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") * RETURN_TO_PCT
    return df


def _backtest_window(per_year_rmse: dict[str, float]) -> str:
    """Derive the ISO-year backtest span from the scored years (D5-12 provenance).

    Uses the years actually present in the global ``per_year_rmse`` so the window is
    always consistent with ``n`` and the coverage figure — no fabricated span.
    """
    years = sorted(int(y) for y in per_year_rmse)
    if not years:
        return "n/a"
    if years[0] == years[-1]:
        return f"{years[0]}"
    return f"{years[0]}-{years[-1]}"


def _build_record(
    oos_row: pd.Series,
    ipo: CatalogueIPO,
    metrics: dict,
    window: str,
    *,
    computed_at: str,
) -> ForecastRecord:
    """Assemble one IPO's ForecastRecord: its own band + the shared global metrics.

    A covered row becomes a ``ForecastInterval`` (percentage points); an abstain row
    becomes ``interval=None`` with an honest reason — never a fabricated band. A row
    flagged covered but carrying a NaN band is CORRUPT and RAISES (isolated by the
    per-IPO loop) rather than fabricating a NaN interval.
    """
    abstain = bool(oos_row["abstain"])
    if abstain:
        interval: ForecastInterval | None = None
        abstain_reason = oos_row.get("abstain_reason") or "insufficient_history"
    else:
        low = float(oos_row["low"])
        high = float(oos_row["high"])
        median = float(oos_row["median"])
        if math.isnan(low) or math.isnan(high) or math.isnan(median):
            raise ValueError(
                f"Covered out-of-sample row for {ipo.drhp_id!r} carries a NaN band "
                f"(low={low}, high={high}, median={median}); refusing to fabricate an "
                f"interval — this row is corrupt (D5-09 honesty)."
            )
        interval = ForecastInterval(
            low_pct=round(low, 2),
            high_pct=round(high, 2),
            median_pct=round(median, 2),
            width_pts=round(high - low, 2),
        )
        abstain_reason = None

    metrics_block = ForecastMetrics(
        coverage_empirical=metrics["coverage_empirical"],
        mae_pts=metrics["mae_pts"],
        backtest_window=window,
        n=metrics["n"],
        per_year_rmse=metrics["per_year_rmse"],
    )

    return ForecastRecord(
        drhp_id=ipo.drhp_id,
        computed_at=computed_at,
        model_version=MODEL_VERSION,
        as_of_listing_date=ipo.listing_date,  # D5-11 provenance (catalogue listing date)
        out_of_sample=True,
        walk_forward=True,
        abstain=abstain,
        abstain_reason=abstain_reason,
        interval=interval,
        sector=ipo.sector,
        metrics=metrics_block,
    )


def _write_record(record: ForecastRecord) -> None:
    """Write a record to ``data/forecasts/<id>.json`` via the allow-list-gated path.

    ``_forecast_path`` gates ``drhp_id`` through ``is_known_drhp_id`` BEFORE forming
    any path (T-05-06-PATH); an un-allow-listed id raises and no path is built.
    """
    path = _forecast_path(record.drhp_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.to_json(), encoding="utf-8")


# ---------------------------------------------------------------------------
# MLflow tracking (local file backend only — T-05-06-MLF)
# ---------------------------------------------------------------------------


def _log_run(mlflow, metrics: dict, *, min_train: int, cal_frac: float, params: dict | None) -> None:
    """Log the key CQR/XGBoost params + the global metrics to the active MLflow run.

    Local file backend only; no remote URI, no server. Kept minimal (DS-rigor
    visibility). Non-finite metrics are skipped rather than logged as NaN.
    """
    effective = {**PARAMS, **(params or {})}
    mlflow.log_params(
        {
            "model_version": MODEL_VERSION,
            "confidence_level": CONFIDENCE_LEVEL,
            "quantile_alpha_lower": QUANTILE_ALPHAS[0],
            "quantile_alpha_upper": QUANTILE_ALPHAS[1],
            "quantile_alpha_median": QUANTILE_ALPHAS[2],
            "min_train": min_train,
            "cal_frac": cal_frac,
            "n_estimators": effective.get("n_estimators"),
            "max_depth": effective.get("max_depth"),
        }
    )

    numeric = {
        "coverage_empirical": metrics["coverage_empirical"],
        "mae_pts": metrics["mae_pts"],
        "mean_width": metrics["mean_width"],
        "n": float(metrics["n"]),
    }
    for year, rmse in metrics["per_year_rmse"].items():
        numeric[f"rmse_{year}"] = rmse
    # Skip NaN/inf so an empty backtest never writes a fabricated metric.
    loggable = {
        k: v
        for k, v in numeric.items()
        if v is not None and isinstance(v, (int, float)) and math.isfinite(v)
    }
    if loggable:
        mlflow.log_metrics(loggable)


def _run_and_score(
    panel: pd.DataFrame,
    X: pd.DataFrame,
    *,
    min_train: int,
    cal_frac: float,
    params: dict | None,
) -> tuple[pd.DataFrame, dict]:
    """Run the walk-forward once and compute the global metrics once (points scale)."""
    oos = walk_forward(panel, X, min_train=min_train, cal_frac=cal_frac, params=params)
    oos_pct = _to_percent_frame(oos)
    metrics = global_metrics(oos_pct)
    return oos_pct, metrics


# ---------------------------------------------------------------------------
# precompute_forecasts — the single-walk-forward, per-catalogue-IPO writer
# ---------------------------------------------------------------------------


def precompute_forecasts(
    *,
    panel: pd.DataFrame | None = None,
    write: bool = True,
    track: bool = True,
    only: set[str] | None = None,
    min_train: int = MIN_TRAIN_DEFAULT,
    cal_frac: float = CAL_FRAC_DEFAULT,
    params: dict | None = None,
) -> dict[str, ForecastRecord]:
    """Compute the walk-forward + global metrics once, write one record per IPO.

    Runs ``build_features(panel)`` -> ``walk_forward(...)`` ONCE to get the
    out-of-sample bands, computes ``global_metrics`` ONCE (identical on every page,
    D5-12), then for each catalogue IPO builds a ``ForecastRecord`` carrying its own
    band (or a first-class abstain) plus the shared metrics block. Per-IPO failures
    are isolated (logged + skipped, P14) — one IPO never aborts the batch.

    Args:
        panel: an assembled survivorship panel. When None, ``_load_panel`` is called
            (DEFERRED to the 05-11 live build — raises until a panel is passed).
        write: if True, write each record to ``data/forecasts/<id>.json`` (gated).
        track: if True, wrap the single walk-forward + metrics computation in an
            ``mlflow.start_run()`` on the local file backend and log the global
            metrics + key CQR params.
        only: optional set of drhp_ids to restrict which records are built/written
            (the global walk-forward + metrics still run over the whole panel).
        min_train / cal_frac / params: walk-forward + XGBoost overrides.

    Returns:
        ``{drhp_id: ForecastRecord}`` for every catalogue IPO that produced a record
        (an IPO with no out-of-sample row, or one whose record-build failed, is
        skipped and absent from the map).
    """
    panel = panel if panel is not None else _load_panel()
    X, _ = build_features(panel)

    if track:
        # MLflow 3.x put the local file store into maintenance mode and gates it
        # behind MLFLOW_ALLOW_FILE_STORE. The CLAUDE.md / RESEARCH lock mandates the
        # local file backend (mlruns/, no server, no DB), so opt in via MLflow's own
        # env var (respecting an explicit user override). This keeps the locked,
        # server-less architecture working on MLflow 3.14 (T-05-06-MLF).
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        import mlflow  # lazy — local file backend only, no server (T-05-06-MLF)

        with mlflow.start_run(run_name="forecast-walk-forward"):
            oos_pct, metrics = _run_and_score(
                panel, X, min_train=min_train, cal_frac=cal_frac, params=params
            )
            _log_run(mlflow, metrics, min_train=min_train, cal_frac=cal_frac, params=params)
    else:
        oos_pct, metrics = _run_and_score(
            panel, X, min_train=min_train, cal_frac=cal_frac, params=params
        )

    window = _backtest_window(metrics["per_year_rmse"])
    computed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Index the out-of-sample rows by drhp_id (only rows that carry one).
    lookup: dict[str, pd.Series] = {}
    if "drhp_id" in oos_pct.columns:
        for _, row in oos_pct.iterrows():
            rid = row["drhp_id"]
            if isinstance(rid, str) and rid:
                lookup[rid] = row

    results: dict[str, ForecastRecord] = {}
    for ipo in load_catalogue():
        drhp_id = ipo.drhp_id
        if only is not None and drhp_id not in only:
            continue
        try:
            # Belt-and-suspenders allow-list gate (the catalogue is trusted, but the
            # write path is gated regardless — T-05-06-PATH).
            if not is_known_drhp_id(drhp_id):  # pragma: no cover - catalogue is allow-listed
                raise ValueError(f"Unknown drhp_id={drhp_id!r}; refusing to write a record.")
            oos_row = lookup.get(drhp_id)
            if oos_row is None:
                console.print(
                    f"  [yellow]{drhp_id}: no out-of-sample row — skipped[/yellow]"
                )
                continue
            record = _build_record(oos_row, ipo, metrics, window, computed_at=computed_at)
            if write:
                _write_record(record)
            results[drhp_id] = record
        except Exception as exc:  # noqa: BLE001 — per-IPO failure isolation (P14)
            console.print(f"  [red]{drhp_id}: FAILED — {exc}[/red]")
            continue

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command(name="precompute-one")
def precompute_one(
    drhp_id: str = typer.Argument(
        ..., help="The drhp_id to pre-compute, e.g. swiggy_2024_11"
    ),
) -> None:
    """Pre-compute the forecast record for one catalogue IPO.

    CODE-NOW-DEFER: runs against the real panel (the deferred 05-11 build). The
    global walk-forward + metrics run over the whole panel; only this IPO's record
    is written.
    """
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to pre-compute a forecast for a "
            f"non-allow-listed id (T-05-06-PATH)."
        )
    console.rule(f"[bold blue]Pre-computing forecast for {drhp_id}[/bold blue]")
    results = precompute_forecasts(only={drhp_id})
    record = results.get(drhp_id)
    if record is None:
        console.print(f"  [yellow]No record produced for {drhp_id}[/yellow]")
        return
    if record.is_abstain:
        console.print(f"  abstain: {record.abstain_reason} (no band)")
    else:
        assert record.interval is not None
        console.print(
            f"  band={record.interval.low_pct}..{record.interval.high_pct} "
            f"(median {record.interval.median_pct}, width {record.interval.width_pts})"
        )
    console.print(
        f"  coverage={record.metrics.coverage_empirical} mae={record.metrics.mae_pts} "
        f"n={record.metrics.n} window={record.metrics.backtest_window}"
    )
    console.print(f"  Written to data/forecasts/{drhp_id}.json")


@app.command(name="precompute-all")
def precompute_all() -> None:
    """Loop over the catalogue and pre-compute every IPO's forecast record.

    CODE-NOW-DEFER: runs against the real panel (the deferred 05-11 build). Per-IPO
    failure isolation (P14) — one IPO's exception is logged and skipped, never
    aborting the batch.
    """
    catalogue = load_catalogue()
    console.rule(
        f"[bold blue]Pre-computing forecasts for {len(catalogue)} IPOs[/bold blue]"
    )
    results = precompute_forecasts()
    console.print("\n[bold]Summary[/bold]")
    for ipo in catalogue:
        record = results.get(ipo.drhp_id)
        if record is None:
            console.print(f"  {ipo.drhp_id}: skipped")
        elif record.is_abstain:
            console.print(f"  {ipo.drhp_id}: abstain ({record.abstain_reason})")
        else:
            console.print(f"  {ipo.drhp_id}: covered")


if __name__ == "__main__":
    app()
