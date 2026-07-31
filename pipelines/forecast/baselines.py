"""
pipelines/forecast/baselines.py — the four locked baselines, the inline
Diebold–Mariano significance test, and the P9 release gate (the phase's honesty
gate, FCAST-05 / P9 / D5-01).

Every one of the four ROADMAP-locked baselines is scored under the IDENTICAL
walk-forward as-of-T0 protocol as the model (``pool = {listing_date < T0_i}``, T0 =
issue-open, D5-01) — the model is never given an easier evaluation than the
baselines. An inline ~15-line Diebold–Mariano test (Harvey small-sample
correction; scipy.stats.t) then tests the model's MAE-loss differential against
each baseline, and the release gate composes those verdicts with the R²>0.5
leakage alarm (``pipelines.forecast.walkforward.r2_leakage_alarm``, 05-05) into an
explicit, honest PASS/FAIL.

The four baselines (RESEARCH §"Four baselines, scored as-of-T0")
------------------------------------------------------------------
Computed ONLY from the as-of-T0 pool (IPOs that listed before the target's T0):
  * ``predict_zero``   — a constant 0.0% listing-day return.
  * ``global_median``  — the median listing-day return of the whole pool.
  * ``trailing_12``    — the median of the 12 most-recent prior listings.
  * ``sector_mean``    — the mean listing-day return of the pool's rows in the
    target's (D5-10 'Other'-pooled) sector.

Diebold–Mariano (inline; NO third-party DM package dependency)
--------------------------------------------------------------
``dm_test(e_model, e_base)`` forms the MAE-loss differential ``d = |e_model| -
|e_base|`` and returns ``(dm_stat, p_value)`` with the Harvey, Leybourne & Newbold
(1997) small-sample correction and a two-sided Student-t p (df = n-1). A negative
``dm_stat`` with ``p < 0.05`` means the MODEL's loss is significantly LOWER than
the baseline's (the model wins); no significance is a statistical TIE. The
low-download [ASSUMED]-provenance third-party DM PyPI package is deliberately
AVOIDED (the inline test is an attack-surface reduction, T-05-09-SC).

``wilcoxon_robustness`` reports a paired signed-rank p as the A7 robustness check
(RESEARCH Open Q2): DM assumes an approximately-normal loss differential; the
non-parametric Wilcoxon is a distribution-free cross-check.

The P9 release gate (honesty, D5-01)
------------------------------------
``release_gate(oos_df, panel)`` returns a plain-data verdict. It FAILS when:
  * the R²>0.5 leakage alarm fires (a T0-violating feature likely slipped in, P4),
    OR
  * ANY baseline SIGNIFICANTLY beats the model (DM p<0.05 in the baseline's favor).
It PASSES otherwise — and when the model does NOT significantly outperform a
baseline (the honest low-R² pre-apply case, D5-01) it STILL passes but appends an
explicit "does not significantly outperform" note. A pre-apply, no-demand model is
EXPECTED to be humble; NEVER p-hack features/folds/the test to cross the gate — if
the model genuinely loses on a fixture, the gate FAILING is the correct, honest
result. The verdict is plain-data (no plotting) so the 05-10 model card embeds the
DM table + verdict verbatim.

ISOLATION / no fragile dependency
---------------------------------
This module imports ONLY numpy / pandas / scipy (+ the import-light
``r2_leakage_alarm`` from the sibling walk-forward module) — it is MODEL-FREE (no
gradient-boosting / conformal / explainability library) and references NO display /
GMP / UI signal (the predictor <-> GMP isolation invariant, T-05-09-ISO). It does no
network I/O.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from scipy.stats import wilcoxon

# ---------------------------------------------------------------------------
# Locked constants
# ---------------------------------------------------------------------------
# The four ROADMAP-locked baseline names, in report order.
BASELINE_NAMES: tuple[str, ...] = (
    "predict_zero",
    "global_median",
    "trailing_12",
    "sector_mean",
)

TRAILING_N: int = 12  # the "trailing-12-IPO-median" window (RESEARCH §Four baselines)
SECTOR_MIN_N: int = 30  # small-N sector pooling threshold -> 'Other' (D5-10)
DM_ALPHA: float = 0.05  # the P9 significance threshold


# ---------------------------------------------------------------------------
# Four baselines, scored as-of-T0 (P9)
# ---------------------------------------------------------------------------
def baselines_asof(pool: pd.DataFrame, sector: str | None) -> dict[str, float]:
    """The four baseline predictions computed ONLY from the as-of-T0 pool.

    Args:
        pool: the IPOs that listed strictly before the target's T0 (the SAME
            as-of-T0 pool the model trains on, P9). Must carry
            ``listing_day_return`` and ``listing_date``; a ``sector`` column
            (already D5-10 'Other'-pooled, if present) drives ``sector_mean``.
        sector: the target IPO's (pooled) sector label; ``sector_mean`` averages
            the pool rows whose ``sector`` equals it. ``NaN`` when the pool has no
            ``sector`` column or no matching rows.

    Returns:
        ``{"predict_zero", "global_median", "trailing_12", "sector_mean"}`` -> float.
        Each is ``NaN`` (never fabricated) when the pool cannot support it (e.g. an
        empty pool, or a sector with no prior listings).
    """
    y = pd.to_numeric(pool.get("listing_day_return"), errors="coerce").dropna()

    trailing = (
        pool.dropna(subset=["listing_day_return"])
        .sort_values("listing_date")["listing_day_return"]
        .tail(TRAILING_N)
    )

    if "sector" in pool.columns and sector is not None:
        sect_vals = pd.to_numeric(
            pool.loc[pool["sector"] == sector, "listing_day_return"], errors="coerce"
        ).dropna()
    else:
        sect_vals = pd.Series([], dtype="float64")

    return {
        "predict_zero": 0.0,
        "global_median": float(y.median()) if len(y) else float("nan"),
        "trailing_12": float(trailing.median()) if len(trailing) else float("nan"),
        "sector_mean": float(sect_vals.mean()) if len(sect_vals) else float("nan"),
    }


def _pool_sector_labels(sectors: pd.Series, *, min_n: int) -> pd.Series:
    """Pool sectors with fewer than ``min_n`` IPOs (and any NaN) into ``'Other'``.

    A local, dependency-light mirror of ``pipelines.features.build.pool_sectors``
    (D5-10) — kept inline so baselines.py imports only numpy/pandas/scipy (no
    feature-build import). Pooling makes a 4-IPO sector's ``sector_mean`` share the
    pooled 'Other' bucket instead of being a noise-prone single-value slice (P7).
    """
    counts = sectors.value_counts(dropna=True)
    keep = {label for label, count in counts.items() if count >= min_n}
    return sectors.map(lambda v: "Other" if pd.isna(v) or v not in keep else v)


def score_baselines(
    panel: pd.DataFrame,
    oos_df: pd.DataFrame,
    *,
    min_n: int = SECTOR_MIN_N,
) -> pd.DataFrame:
    """Score the four baselines against the model's OUT-OF-SAMPLE rows (as-of-T0).

    For every COVERED (non-abstain) walk-forward row, rebuild the SAME as-of-T0
    pool the model used (``panel`` rows with ``listing_date < t0``, using the row's
    recorded ``t0`` provenance), compute the four ``baselines_asof`` predictions,
    and align each baseline's absolute error to the model's — so the release gate
    can DM-test loss differentials on identically-evaluated rows (P9).

    Sector labels are D5-10 'Other'-pooled globally before scoring; a panel with no
    ``sector`` column is treated as a single 'Other' bucket (``sector_mean`` then
    equals the pool mean).

    Args:
        panel: the historical panel (needs ``issuer``, ``listing_date``,
            ``listing_day_return``; an optional ``sector`` column drives pooling).
        oos_df: a walk-forward frame (``pipelines.forecast.walkforward`` OOS_COLUMNS)
            carrying ``issuer``, ``actual``, ``median``, ``t0``, ``abstain``.
        min_n: the D5-10 sector-pooling threshold.

    Returns:
        One row per covered OOS IPO with ``issuer``, ``actual``, ``model_pred``,
        ``model_abs_err`` and, per baseline, ``{name}_pred`` + ``{name}_abs_err``
        (units follow the input — the raw walk-forward frame is fraction; DM is
        scale-invariant).
    """
    work = panel.copy()
    if "sector" in work.columns:
        work["sector"] = _pool_sector_labels(work["sector"], min_n=min_n)
    else:
        work["sector"] = "Other"

    if "abstain" in oos_df.columns:
        covered = oos_df[~oos_df["abstain"].astype(bool)]
    else:
        covered = oos_df

    sector_by_issuer = (
        work.dropna(subset=["issuer"]).groupby("issuer")["sector"].first().to_dict()
    )

    rows: list[dict[str, Any]] = []
    for _, r in covered.iterrows():
        t0 = r["t0"]
        actual = float(r["actual"])
        model_pred = float(r["median"])
        issuer = r.get("issuer")

        pool = work[(work["listing_date"] < t0) & work["listing_day_return"].notna()]
        sector = sector_by_issuer.get(issuer, "Other")
        preds = baselines_asof(pool, sector)

        row: dict[str, Any] = {
            "issuer": issuer,
            "actual": actual,
            "model_pred": model_pred,
            "model_abs_err": abs(actual - model_pred),
        }
        for name, pred in preds.items():
            row[f"{name}_pred"] = pred
            row[f"{name}_abs_err"] = (
                abs(actual - pred) if pred == pred else float("nan")  # NaN-safe
            )
        rows.append(row)

    columns = ["issuer", "actual", "model_pred", "model_abs_err"]
    for name in BASELINE_NAMES:
        columns += [f"{name}_pred", f"{name}_abs_err"]
    return pd.DataFrame(rows, columns=columns)


# ---------------------------------------------------------------------------
# Diebold–Mariano (inline; Harvey small-sample correction) — NO dependency
# ---------------------------------------------------------------------------
def dm_test(e_model: Any, e_base: Any, h: int = 1) -> tuple[float, float]:
    """The Diebold–Mariano test on the MAE-loss differential (Harvey-corrected).

    Forms ``d = |e_model| - |e_base|`` (MAE loss), estimates the long-run variance
    of ``d`` (for ``h=1`` this is just ``gamma0 / n``; higher ``h`` adds the
    ``2*sum gamma_k`` autocovariance terms), applies the Harvey, Leybourne & Newbold
    (1997) small-sample correction, and compares to a two-sided Student-t with
    ``n-1`` degrees of freedom.

    Args:
        e_model: the model's per-IPO forecast errors (``actual - model_pred``).
        e_base: the baseline's per-IPO forecast errors (``actual - baseline_pred``).
        h: the forecast horizon (1 for a one-step listing-day forecast).

    Returns:
        ``(dm_stat, p_value)``. ``dm_stat < 0`` with ``p_value < 0.05`` means the
        MODEL's loss is significantly LOWER than the baseline's (the model wins); a
        larger p is a statistical TIE. ``(NaN, NaN)`` when fewer than two paired
        observations exist; ``(0.0, 1.0)`` on a degenerate zero-variance tie.
    """
    e_model = np.asarray(e_model, dtype=float)
    e_base = np.asarray(e_base, dtype=float)
    d = np.abs(e_model) - np.abs(e_base)  # MAE-loss differential
    n = d.size
    if n < 2:
        return float("nan"), float("nan")

    dbar = float(d.mean())
    dev = d - dbar
    acov = float(np.mean(dev * dev))  # gamma_0
    for k in range(1, h):
        acov += 2.0 * float(np.mean(dev[k:] * dev[:-k]))  # + 2*gamma_k (h>1)
    var_dbar = acov / n
    if var_dbar <= 0.0:
        return 0.0, 1.0  # no variance in the loss differential -> a tie

    dm = dbar / math.sqrt(var_dbar)
    correction = math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)  # Harvey 1997
    dm_adj = dm * correction
    p = 2.0 * (1.0 - float(student_t.cdf(abs(dm_adj), df=n - 1)))
    return float(dm_adj), float(p)


def wilcoxon_robustness(e_model: Any, e_base: Any) -> float:
    """Paired Wilcoxon signed-rank p on the absolute errors (A7 robustness check).

    A distribution-free cross-check for the DM test (RESEARCH Open Q2): DM assumes
    an approximately-normal loss differential, so a non-parametric confirmation adds
    honesty. Returns ``NaN`` when the differences are all zero / too few to rank.
    """
    a = np.abs(np.asarray(e_model, dtype=float))
    b = np.abs(np.asarray(e_base, dtype=float))
    if a.size < 1 or np.all(a - b == 0.0):
        return float("nan")
    try:
        _, p = wilcoxon(a, b)
    except ValueError:
        return float("nan")
    return float(p)


# ---------------------------------------------------------------------------
# The P9 release gate (four-baseline DM + R²>0.5 leakage alarm)
# ---------------------------------------------------------------------------
def release_gate(
    oos_df: pd.DataFrame,
    panel: pd.DataFrame,
    *,
    alpha: float = DM_ALPHA,
    min_n: int = SECTOR_MIN_N,
) -> dict[str, Any]:
    """Compose the P9 release verdict: four-baseline DM + the R²>0.5 leakage alarm.

    Scores the four baselines as-of-T0, DM-tests the model's absolute errors
    against each, runs ``r2_leakage_alarm`` on the OOS median, and returns a
    plain-data verdict the 05-10 model card embeds verbatim.

    The gate FAILS (``passed=False``) when the R²>0.5 leakage alarm fires (a
    T0-violating feature likely slipped in, P4/P9) OR when ANY baseline
    SIGNIFICANTLY beats the model (baseline loss significantly lower at ``p<alpha``).
    Otherwise it PASSES — and when the model does NOT significantly outperform a
    baseline (the honest low-R² pre-apply case, D5-01) it appends an explicit "does
    not significantly outperform" note rather than p-hacking to cross the gate.

    Args:
        oos_df: the walk-forward OOS frame (``actual``/``median``/``t0``/``abstain``).
        panel: the historical panel the baselines are scored from (same as-of-T0).
        alpha: the DM significance threshold (0.05).
        min_n: the D5-10 sector-pooling threshold.

    Returns:
        ``{"passed": bool, "r2": float, "r2_alarm": str | None,
           "per_baseline": {name: {"dm_stat", "p_value", "wilcoxon_p",
                                    "model_beats_sig", "baseline_beats_model_sig",
                                    "n"}},
           "n_scored": int, "notes": [str, ...]}``.
    """
    from pipelines.forecast.walkforward import r2_leakage_alarm  # import-light sibling

    scored = score_baselines(panel, oos_df, min_n=min_n)
    r2, r2_alarm = r2_leakage_alarm(oos_df)

    e_model_all = scored["actual"] - scored["model_pred"]

    per_baseline: dict[str, dict[str, Any]] = {}
    any_baseline_beats = False
    for name in BASELINE_NAMES:
        e_base_all = scored["actual"] - scored[f"{name}_pred"]
        mask = e_model_all.notna() & e_base_all.notna()
        em = e_model_all[mask].to_numpy()
        eb = e_base_all[mask].to_numpy()

        if em.size < 2:
            dm_stat, p_value = float("nan"), float("nan")
        else:
            dm_stat, p_value = dm_test(em, eb)
        wilcox_p = wilcoxon_robustness(em, eb) if em.size >= 1 else float("nan")

        sig = dm_stat == dm_stat and p_value == p_value and p_value < alpha  # not NaN
        model_beats_sig = bool(sig and dm_stat < 0)
        baseline_beats_model_sig = bool(sig and dm_stat > 0)
        if baseline_beats_model_sig:
            any_baseline_beats = True

        per_baseline[name] = {
            "dm_stat": dm_stat,
            "p_value": p_value,
            "wilcoxon_p": wilcox_p,
            "model_beats_sig": model_beats_sig,
            "baseline_beats_model_sig": baseline_beats_model_sig,
            "n": int(em.size),
        }

    passed = (r2_alarm is None) and (not any_baseline_beats)

    notes: list[str] = []
    if r2_alarm is not None:
        notes.append(
            f"RELEASE GATE FAILED (leakage): {r2_alarm}"
        )
    if any_baseline_beats:
        beaten_by = [
            n for n, d in per_baseline.items() if d["baseline_beats_model_sig"]
        ]
        notes.append(
            "RELEASE GATE FAILED (baseline beats model): the naive baseline(s) "
            f"{beaten_by} significantly beat the model (Diebold–Mariano p<{alpha} in "
            "the baseline's favor). The model adds nothing over a naive rule on this "
            "evaluation — do NOT ship it and do NOT p-hack features to force a pass."
        )

    not_beaten = [n for n, d in per_baseline.items() if not d["model_beats_sig"]]
    if not_beaten:
        notes.append(
            "The model does not significantly outperform the following baseline(s) at "
            f"p<{alpha}: {not_beaten}. For a pre-apply, no-demand forecast this humble "
            "result is EXPECTED (D5-01) — a low R² is a feature, not a bug. The model "
            "card states this plainly; no features/folds/tests were tuned to cross the "
            "gate."
        )

    return {
        "passed": passed,
        "r2": r2,
        "r2_alarm": r2_alarm,
        "per_baseline": per_baseline,
        "n_scored": int(len(scored)),
        "notes": notes,
    }


__all__ = [
    "BASELINE_NAMES",
    "TRAILING_N",
    "SECTOR_MIN_N",
    "DM_ALPHA",
    "baselines_asof",
    "score_baselines",
    "dm_test",
    "wilcoxon_robustness",
    "release_gate",
]
