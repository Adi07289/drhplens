"""
pipelines/forecast/diagnostics.py — the GLOBAL walk-forward honesty metrics
(D5-12 / FCAST-04), computed ONCE over the out-of-sample walk-forward rows.

``global_metrics(oos_df)`` aggregates the per-IPO out-of-sample bands the
walk-forward emitted into the three model-wide numbers the forecast page shows on
EVERY IPO (identical across pages, D5-12): empirical coverage, mean absolute error,
and per-year RMSE — plus the mean band width and the scored-row count. These are
the "how this was tested" figures baked into every ``ForecastRecord.metrics`` block
(``agent.forecast_schema.ForecastMetrics``).

Honesty invariants (P17 — calibration theater is the pitfall this guards):
  * **Empirical coverage is the REAL held-out number** — ``mean((actual >= low) &
    (actual <= high))`` over the scored rows. It is NEVER clamped to the 0.80
    target; a coverage of 0.74 or 0.86 is reported as-is (P17). The only rounding
    applied is display precision (4 dp) which can never move a non-0.80 value TO
    0.80.
  * **Abstain rows contribute NOTHING** — an ``abstain=True`` row (no calibratable
    band) is excluded from coverage, MAE, RMSE, width and the count. A no-band row
    is not a 0%-error row; counting it would fabricate calibration quality.
  * **No fabricated year** — ``per_year_rmse`` is keyed only by the listing years
    actually present among the scored rows. A year with no scored IPO is simply
    absent, never a fabricated 0.0.

UNITS: the caller passes rows already in **percentage points** (e.g. a +6.1%
listing-day return is ``6.1``, not ``0.061``). The walk-forward emits the raw
FRACTION return, so ``pipelines.forecast.precompute`` multiplies by 100 at the
model→record boundary BEFORE calling this; the ``oos_rows`` test fixture is likewise
authored in percentage points. Coverage is scale-free; MAE / RMSE / width inherit
the caller's units (hence ``mae_pts`` — points).

``global_metrics`` imports only pandas + stdlib. The calibration / PIT / SHAP
diagnostic PLOT builders (05-10, FCAST-03) live below it: each writes a committed
PNG under ``model_card/`` and imports its heavy plotting / explainability stack
(matplotlib, shap, scipy) **LAZILY inside the function** and forces the headless
``Agg`` backend — so importing THIS module stays offline and light (no display, no
matplotlib/shap at module load, safe in CI). ``global_metrics`` is left exactly as
05-06 shipped it.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# The band columns every scored row must carry to contribute a statistic. A row
# missing any of these has no computable band and is dropped from the aggregate
# (an honest "not scored", never a fabricated zero-error contribution).
_BAND_COLUMNS = ("actual", "low", "high", "median")


def global_metrics(oos_df: pd.DataFrame) -> dict:
    """Aggregate the out-of-sample walk-forward rows into the GLOBAL metrics (D5-12).

    Args:
        oos_df: a walk-forward out-of-sample frame — one row per scored IPO with
            ``actual``, ``low``, ``high``, ``median`` (all in **percentage points**)
            and ``listing_year``, plus an optional ``abstain`` flag column. Abstain
            rows (and any row missing a band value) are excluded from every
            statistic.

    Returns:
        A dict with:
          - ``coverage_empirical`` — ``mean((actual >= low) & (actual <= high))``
            over the scored rows, the REAL held-out number (never clamped to 0.80,
            P17); ``float('nan')`` when there are no scored rows.
          - ``mae_pts`` — mean absolute error of the median vs the realized return,
            in points.
          - ``per_year_rmse`` — ``{str(year): rmse}`` of the median's RMSE grouped
            by listing year; keys are only the years actually present.
          - ``mean_width`` — mean band width ``high - low`` (points).
          - ``n`` — the number of scored (non-abstain, banded) rows.
    """
    scored = oos_df
    if "abstain" in scored.columns:
        scored = scored[~scored["abstain"].astype(bool)]
    scored = scored.dropna(subset=list(_BAND_COLUMNS))

    n = int(len(scored))
    if n == 0:
        # No scored rows — honestly empty, never a fabricated coverage/MAE.
        return {
            "coverage_empirical": float("nan"),
            "mae_pts": float("nan"),
            "per_year_rmse": {},
            "mean_width": float("nan"),
            "n": 0,
        }

    actual = scored["actual"].astype(float)
    low = scored["low"].astype(float)
    high = scored["high"].astype(float)
    median = scored["median"].astype(float)

    covered = (actual >= low) & (actual <= high)
    # RAW empirical coverage — the real held-out number (P17). Rounded only to 4 dp
    # for a diff-reviewable committed record; 4 dp can never move a non-0.80 value
    # to 0.80, so this is display precision, NOT target-clamping.
    coverage_empirical = round(float(covered.mean()), 4)
    mae_pts = round(float((actual - median).abs().mean()), 2)
    mean_width = round(float((high - low).mean()), 2)

    # Per-year RMSE of the median. Rows without a listing_year cannot be attributed
    # to a year and are dropped from THIS statistic only (never bucketed as a
    # fabricated year); coverage/MAE above still counted them.
    squared_error = (actual - median) ** 2
    year_frame = pd.DataFrame(
        {"listing_year": scored["listing_year"].to_numpy(), "se": squared_error.to_numpy()}
    ).dropna(subset=["listing_year"])
    per_year = year_frame.groupby("listing_year")["se"].mean().pow(0.5)
    per_year_rmse = {
        str(int(year)): round(float(rmse), 2) for year, rmse in per_year.items()
    }

    return {
        "coverage_empirical": coverage_empirical,
        "mae_pts": mae_pts,
        "per_year_rmse": per_year_rmse,
        "mean_width": mean_width,
        "n": n,
    }


# ---------------------------------------------------------------------------
# Calibration / PIT / SHAP diagnostic PLOTS (05-10, FCAST-03) — committed PNGs.
#
# The heavy stacks (matplotlib / shap / scipy) are imported LAZILY inside each
# function and the headless Agg backend is forced, so importing this module never
# drags in a display backend (offline / CI-safe). The production interval stays the
# 0.1 / 0.5 / 0.9 band (``pipelines.forecast.model``); the finer grid below is fit
# PURELY for the reliability / PIT diagnostic (RESEARCH Open Q1, A8) — the PIT is
# labeled grid-derived wherever it is shown.
# ---------------------------------------------------------------------------

# The diagnostic quantile grid (0.05, 0.10, …, 0.95) — reliability/PIT only.
QUANTILE_GRID: tuple[float, ...] = tuple(round(0.05 * k, 2) for k in range(1, 20))

# Dark --drhp-* palette echoes (the committed PNGs sit on the dark methodology page).
_ACCENT = "#E0A24E"      # amber — the ONE accent (the empirical curve / bars)
_MUTED = "#9A9BA0"       # neutral muted — the reference diagonal / uniform line
_BORDER = "#33363C"      # subtle border — bar edges / the 80% guide
_INK = "#ECECEA"         # primary text
_SURFACE = "#1E2024"     # card surface


def _scored_band(oos_df: pd.DataFrame) -> pd.DataFrame:
    """Drop abstain rows + any row missing a band value (mirrors global_metrics)."""
    scored = oos_df
    if "abstain" in scored.columns:
        scored = scored[~scored["abstain"].astype(bool)]
    return scored.dropna(subset=list(_BAND_COLUMNS))


def _band_sigma(low: np.ndarray, high: np.ndarray, confidence: float = 0.8) -> np.ndarray:
    """Per-row Gaussian-working-assumption sigma implied by the central band.

    A central ``confidence`` interval spans ``median ± z * sigma`` with
    ``z = Phi^{-1}((1+confidence)/2)``, so ``sigma = (high - low) / (2 z)``. This is
    the ONLY assumption the reliability/PIT diagnostic makes — it turns the committed
    0.1/0.5/0.9 band into the finer grid PURELY for the diagnostic (A8; the
    production interval is unchanged). Zero/negative widths yield NaN (excluded).
    """
    from scipy.stats import norm  # lazy

    z = float(norm.ppf((1.0 + confidence) / 2.0))
    width = np.asarray(high, dtype=float) - np.asarray(low, dtype=float)
    sigma = width / (2.0 * z)
    return np.where(sigma > 0.0, sigma, np.nan)


def empirical_coverage(oos_df: pd.DataFrame) -> float:
    """The REAL held-out 80% empirical coverage of the committed band (P17).

    A thin, honest wrapper over ``global_metrics`` so the calibration annotation and
    the model card share ONE coverage seam — ``mean((actual>=low)&(actual<=high))``
    over the scored rows, NEVER rounded to the 0.80 target (P17 / A8).
    """
    return global_metrics(oos_df)["coverage_empirical"]


def calibration_plot(oos_df: pd.DataFrame, out_path: str | Path) -> Path:
    """Write a reliability diagram (nominal vs empirical coverage) to ``out_path``.

    Across the ``QUANTILE_GRID`` (0.05..0.95, fit purely for the diagnostic) the
    empirical central-interval coverage is plotted against the nominal level with
    the perfect-calibration diagonal, and the plot is ANNOTATED with the REAL 80%
    empirical coverage of the committed band (``empirical_coverage`` — never
    0.80-rounded, P17). Returns the written ``Path``.
    """
    import matplotlib

    matplotlib.use("Agg")  # headless — no display, CI-safe
    import matplotlib.pyplot as plt
    from scipy.stats import norm

    scored = _scored_band(oos_df)
    actual = scored["actual"].to_numpy(dtype=float)
    low = scored["low"].to_numpy(dtype=float)
    high = scored["high"].to_numpy(dtype=float)
    median = scored["median"].to_numpy(dtype=float)
    sigma = _band_sigma(low, high)

    nominal = np.asarray(QUANTILE_GRID, dtype=float)
    empirical = np.empty_like(nominal)
    for i, c in enumerate(nominal):
        z = float(norm.ppf((1.0 + c) / 2.0))
        inside = (actual >= median - z * sigma) & (actual <= median + z * sigma)
        empirical[i] = float(np.nanmean(inside.astype(float)))

    cov80 = empirical_coverage(oos_df)  # the REAL committed-band 80% coverage (P17)

    fig, ax = plt.subplots(figsize=(5.0, 5.0), dpi=120)
    fig.patch.set_facecolor(_SURFACE)
    ax.set_facecolor(_SURFACE)
    ax.plot([0, 1], [0, 1], ls="--", color=_MUTED, lw=1.2, label="perfect calibration")
    ax.plot(nominal, empirical, marker="o", color=_ACCENT, lw=1.6,
            label="empirical (held-out, grid-derived)")
    ax.axvline(0.8, color=_BORDER, lw=1.0)
    if cov80 == cov80:  # not NaN
        ax.annotate(
            f"real 80% band coverage = {cov80:.3f}",
            xy=(0.8, cov80), xytext=(0.06, 0.9), color=_INK, fontsize=9,
            arrowprops=dict(arrowstyle="->", color=_MUTED, lw=0.8),
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("nominal central-interval coverage", color=_INK, fontsize=9)
    ax.set_ylabel("empirical coverage (held-out)", color=_INK, fontsize=9)
    ax.set_title("Reliability diagram — grid-derived (0.05..0.95)", color=_INK, fontsize=10)
    ax.tick_params(colors=_MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(_BORDER)
    ax.legend(fontsize=8, facecolor=_SURFACE, edgecolor=_BORDER, labelcolor=_INK)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return out


def pit_histogram(oos_df: pd.DataFrame, out_path: str | Path) -> Path:
    """Write the PIT / reliability histogram (grid-derived) to ``out_path``.

    The Probability-Integral-Transform ``PIT_i = Phi((actual_i - median_i)/sigma_i)``
    is computed from the band-implied per-row sigma (the grid working assumption,
    A8) and histogrammed over [0, 1]; a FLAT histogram means calibrated. The title
    labels it grid-derived (0.05..0.95). Returns the written ``Path``.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.stats import norm

    scored = _scored_band(oos_df)
    actual = scored["actual"].to_numpy(dtype=float)
    median = scored["median"].to_numpy(dtype=float)
    low = scored["low"].to_numpy(dtype=float)
    high = scored["high"].to_numpy(dtype=float)
    sigma = _band_sigma(low, high)

    pit = norm.cdf((actual - median) / sigma)
    pit = pit[~np.isnan(pit)]

    bins = 10
    fig, ax = plt.subplots(figsize=(5.0, 4.2), dpi=120)
    fig.patch.set_facecolor(_SURFACE)
    ax.set_facecolor(_SURFACE)
    ax.hist(pit, bins=bins, range=(0.0, 1.0), color=_ACCENT, edgecolor=_BORDER)
    if pit.size:
        ax.axhline(pit.size / bins, ls="--", color=_MUTED, lw=1.2,
                   label="uniform (calibrated)")
    ax.set_xlim(0, 1)
    ax.set_xlabel("PIT = Phi((actual − median) / band-implied σ)", color=_INK, fontsize=9)
    ax.set_ylabel("count", color=_INK, fontsize=9)
    ax.set_title("PIT histogram — grid-derived (0.05..0.95); flat = calibrated",
                 color=_INK, fontsize=10)
    ax.tick_params(colors=_MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(_BORDER)
    ax.legend(fontsize=8, facecolor=_SURFACE, edgecolor=_BORDER, labelcolor=_INK)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return out


def shap_summary(
    model,
    X,
    out_path: str | Path,
    *,
    feature_names: list[str] | None = None,
) -> Path:
    """Write a SHAP feature-importance summary to ``out_path`` (D5-07 interpretability).

    Computes mean ``|SHAP value|`` per feature over the lean design matrix ``X`` via
    a ``shap.TreeExplainer``; when SHAP is unavailable (or the estimator is not
    tree-explainable) it FALLS BACK to the model's ``feature_importances_`` (XGBoost
    gain). A horizontal bar chart over the lean ``SELECTED_FEATURES`` is written.
    Returns the written ``Path``.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if hasattr(X, "columns"):
        feat = X.drop(columns=["available_at"], errors="ignore")
        names = feature_names or list(feat.columns)
        Xa = np.asarray(feat, dtype=float)
    else:
        Xa = np.asarray(X, dtype=float)
        if Xa.ndim == 1:
            Xa = Xa.reshape(1, -1)
        names = feature_names or [f"f{i}" for i in range(Xa.shape[1])]

    method = "mean |SHAP value|"
    importances: np.ndarray | None = None
    try:
        import shap  # lazy

        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(Xa)
        importances = np.abs(np.asarray(values, dtype=float)).mean(axis=0)
    except Exception:  # noqa: BLE001 - SHAP unavailable / non-tree estimator -> fallback
        fi = getattr(model, "feature_importances_", None)
        if fi is None and hasattr(model, "get_booster"):  # pragma: no cover - rare path
            booster = model.get_booster()
            raw = booster.get_score(importance_type="gain")
            fi = [raw.get(f"f{i}", 0.0) for i in range(len(names))]
        if fi is None:
            fi = [0.0] * len(names)
        importances = np.asarray(fi, dtype=float)
        method = "XGBoost gain importance (SHAP unavailable)"

    importances = np.asarray(importances, dtype=float).reshape(-1)
    k = min(len(names), importances.size)
    names = list(names[:k])
    importances = importances[:k]
    order = np.argsort(importances)

    fig, ax = plt.subplots(figsize=(5.6, max(3.0, 0.42 * k)), dpi=120)
    fig.patch.set_facecolor(_SURFACE)
    ax.set_facecolor(_SURFACE)
    ax.barh([names[i] for i in order], importances[order], color=_ACCENT,
            edgecolor=_BORDER)
    ax.set_xlabel(method, color=_INK, fontsize=9)
    ax.set_title("Feature importance — lean SELECTED_FEATURES", color=_INK, fontsize=10)
    ax.tick_params(colors=_MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(_BORDER)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return out


__all__ = [
    "global_metrics",
    "QUANTILE_GRID",
    "empirical_coverage",
    "calibration_plot",
    "pit_histogram",
    "shap_summary",
]
