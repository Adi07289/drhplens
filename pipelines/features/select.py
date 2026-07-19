"""
pipelines/features/select.py — lean walk-forward feature selection (D5-07) + the
training-support helper (the ``out_of_support`` input for D5-09 abstention, 05-09).

Two jobs:

1. **Curate the wide candidate pool to a LEAN production set (D5-07).**
   ``select_features(panel, X)`` runs an expanding-window, as-of-T0 walk-forward
   (the same no-lookahead pooling as ``pipelines.forecast.walkforward``), collects
   per-fold XGBoost GAIN importances for every candidate feature, and ranks by
   BOTH mean importance AND cross-fold stability — returning a lean set (~8–15,
   capped at ``max_k``) plus an importance/stability table (the model-card input).
   The selection is itself walk-forward: each fold's importance is fit ONLY on
   pre-T0 data, so there is no full-sample importance leak (P4). The production run
   trains on the lean ``SELECTED_FEATURES`` constant, NOT the kitchen sink
   (P7/overfit control on ~200–300 rows).

2. **Flag out-of-support feature vectors (D5-09 input).**
   ``training_support(X_train)`` computes per-feature ``[q01, q99]`` bounds;
   ``is_out_of_support(x_row, support)`` returns ``True`` when any (non-missing)
   feature falls outside its training-support bound — the extrapolation half of the
   D5-09 abstention trigger the walk-forward wires in at 05-09.

NO NETWORK / NO MODEL AT IMPORT
-------------------------------
``xgboost`` is reached only through ``pipelines.forecast.model``'s LAZY (in-function)
imports; importing THIS module pulls in only stdlib + numpy + pandas + the
import-light model/walk-forward wrappers — it stays offline (pinned by
tests/unit/test_feature_selection.py's subprocess lazy-import proof).

CODE-NOW-DEFER: ``SELECTED_FEATURES`` is the committed lean set curated by this
selector; the REAL walk-forward selection over the live ~200–300-row panel is run
at 05-09/05-11 and updates the constant (mirrors the phase's precompute posture).
"""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from pipelines.features import FEATURE_COLUMNS
from pipelines.forecast.model import make_quantile_models
from pipelines.forecast.walkforward import (
    CAL_FRAC_DEFAULT,
    MIN_TRAIN_DEFAULT,
)

# ---------------------------------------------------------------------------
# The committed LEAN production feature set (D5-07) — curated via select_features'
# walk-forward importance/stability ranking. ~8–15, interpretable, spans all four
# families. The real walk-forward selection over the live panel regenerates this at
# 05-09/05-11 (CODE-NOW-DEFER); it is importable so the production run trains on the
# lean set, not the full candidate pool.
# ---------------------------------------------------------------------------
SELECTED_FEATURES: tuple[str, ...] = (
    # (a) issue structure
    "issue_size_cr",
    "price_band_width_pct",
    "ofs_fraction",
    "promoter_dilution_pct",
    # (b) market regime
    "nifty_mom_3m",
    "india_vix",
    "trailing_listing_gain",
    # (c) DRHP-derived
    "red_flag_count",
    "rpt_intensity",
    # (d) anchor demand
    "anchor_book_cr",
)

# Contract guard: the lean set must be a subset of the declared candidate pool.
assert set(SELECTED_FEATURES) <= set(FEATURE_COLUMNS), (
    "SELECTED_FEATURES must be a subset of FEATURE_COLUMNS (the candidate pool)."
)

# Support quantiles for the D5-09 out-of-support (extrapolation) check.
SUPPORT_LOW_Q: float = 0.01
SUPPORT_HIGH_Q: float = 0.99

# Default cap + fold budget for the lean walk-forward selection.
MAX_SELECTED_DEFAULT: int = 15  # D5-07 lean cap (~8–15 target)
_MAX_FOLDS_DEFAULT: int = 6     # walk-forward importance folds (cross-fold stability)

_REQUIRED_PANEL_COLUMNS = ("issue_date", "listing_date", "listing_day_return")


def _numeric_features(X: pd.DataFrame) -> pd.DataFrame:
    """Drop the non-feature ``available_at`` stamp; keep the numeric design matrix."""
    return X.drop(columns=["available_at"], errors="ignore")


def _fold_gain_importances(
    panel: pd.DataFrame,
    feat: pd.DataFrame,
    *,
    min_train: int,
    max_folds: int,
    params: dict | None,
) -> pd.DataFrame:
    """Collect per-fold XGBoost GAIN importances under the as-of-T0 walk-forward.

    Picks up to ``max_folds`` expanding-window anchor points; at each, the training
    pool is STRICTLY the IPOs that listed before that anchor's T0 (no lookahead),
    fits the median quantile model, and records each candidate feature's gain
    importance (0 when the feature never splits). Returns a ``feature x fold`` frame.
    """
    columns = list(feat.columns)
    usable = panel[
        panel["listing_day_return"].notna()
        & panel["listing_date"].notna()
        & panel["issue_date"].notna()
    ].sort_values("listing_date")

    n = len(usable)
    fold_series: list[pd.Series] = []
    if n <= min_train:
        return pd.DataFrame(index=columns)

    # Evenly spaced expanding-window anchors in [min_train, n-1].
    anchor_positions = np.unique(
        np.linspace(min_train, n - 1, num=min(max_folds, n - min_train), dtype=int)
    )

    for fold_i, pos in enumerate(anchor_positions):
        t0 = usable.iloc[int(pos)]["issue_date"]
        pool = usable[usable["listing_date"] < t0]
        if len(pool) < min_train:
            continue
        y = pool["listing_day_return"]
        models = make_quantile_models(feat.loc[pool.index], y, params)
        # median model (index 2 — [lower, upper, median]) gain importances.
        booster = models[2].get_booster()
        raw = booster.get_score(importance_type="gain")  # {"f{i}": gain}
        gains = {
            columns[int(key[1:])]: float(val)
            for key, val in raw.items()
            if key.startswith("f") and int(key[1:]) < len(columns)
        }
        fold_series.append(
            pd.Series(
                {col: gains.get(col, 0.0) for col in columns}, name=f"fold_{fold_i}"
            )
        )

    if not fold_series:
        return pd.DataFrame(index=columns)
    return pd.concat(fold_series, axis=1)


def select_features(
    panel: pd.DataFrame,
    X: pd.DataFrame,
    *,
    max_k: int = MAX_SELECTED_DEFAULT,
    min_train: int = MIN_TRAIN_DEFAULT,
    cal_frac: float = CAL_FRAC_DEFAULT,  # noqa: ARG001 - accepted for a uniform seam
    max_folds: int = _MAX_FOLDS_DEFAULT,
    params: dict | None = None,
) -> tuple[list[str], pd.DataFrame]:
    """Curate the wide candidate pool to a lean walk-forward-selected set (D5-07).

    Runs the as-of-T0 walk-forward, collects per-fold XGBoost gain importances,
    ranks candidates by BOTH mean importance AND cross-fold stability, and returns
    the lean set (capped at ``max_k``, ~8–15 target) plus the full importance/
    stability table (one row per candidate — the model-card input).

    Args:
        panel: an assembled historical panel (needs ``issue_date`` /
            ``listing_date`` / ``listing_day_return``).
        X: the leakage-gated feature matrix aligned to ``panel`` by index (the
            candidate pool; an ``available_at`` stamp column is ignored).
        max_k: the lean-set cap (D5-07).
        min_train / cal_frac: walk-forward window controls (mirroring
            ``pipelines.forecast.walkforward``).
        max_folds: number of expanding-window folds for the stability estimate.
        params: optional XGBoost overrides forwarded to the fold fits.

    Returns:
        ``(selected, table)``:
          - ``selected`` — the lean, importance/stability-ranked feature names
            (``<= max_k``); only features with positive mean importance are kept.
          - ``table`` — a DataFrame indexed by EVERY candidate feature with
            ``mean_importance`` / ``importance_std`` / ``mean_rank`` / ``rank_std`` /
            ``stability`` / ``score`` / ``selected``, ordered by ``score`` desc.

    Raises:
        ValueError: if ``panel`` is missing a required column.
    """
    missing = set(_REQUIRED_PANEL_COLUMNS) - set(panel.columns)
    if missing:
        raise ValueError(
            f"select_features panel is missing required column(s): {sorted(missing)}"
        )

    feat = _numeric_features(X)
    imp = _fold_gain_importances(
        panel, feat, min_train=min_train, max_folds=max_folds, params=params
    )

    columns = list(feat.columns)
    if imp.empty or imp.shape[1] == 0:
        # No fold could fit (too little history) — no importance signal; empty lean set.
        table = pd.DataFrame(
            {
                "mean_importance": [0.0] * len(columns),
                "importance_std": [0.0] * len(columns),
                "mean_rank": [float("nan")] * len(columns),
                "rank_std": [float("nan")] * len(columns),
                "stability": [0.0] * len(columns),
                "score": [0.0] * len(columns),
                "selected": [False] * len(columns),
            },
            index=columns,
        )
        return [], table

    mean_importance = imp.mean(axis=1)
    importance_std = imp.std(axis=1).fillna(0.0)

    # Per-fold rank (1 = most important); cross-fold rank stability.
    ranks = imp.rank(axis=0, ascending=False, method="average")
    mean_rank = ranks.mean(axis=1)
    rank_std = ranks.std(axis=1).fillna(0.0)
    stability = 1.0 / (1.0 + rank_std)  # in (0, 1]; higher = steadier across folds

    # Combined score: normalized mean importance weighted by cross-fold stability.
    max_imp = float(mean_importance.max())
    norm_importance = mean_importance / max_imp if max_imp > 0 else mean_importance * 0.0
    score = norm_importance * stability

    table = pd.DataFrame(
        {
            "mean_importance": mean_importance,
            "importance_std": importance_std,
            "mean_rank": mean_rank,
            "rank_std": rank_std,
            "stability": stability,
            "score": score,
        }
    ).sort_values("score", ascending=False)

    # Lean set: positive-importance features, capped at max_k (D5-07 ~8–15 target).
    ranked = table[table["mean_importance"] > 0.0]
    selected = list(ranked.index[:max_k])
    table["selected"] = table.index.isin(selected)

    return selected, table


def training_support(X_train: pd.DataFrame) -> dict[str, tuple[float, float]]:
    """Compute per-feature ``[q01, q99]`` training-support bounds (D5-09 input).

    Args:
        X_train: the training design matrix (an ``available_at`` stamp is ignored).

    Returns:
        ``{feature: (q01, q99)}`` for every feature with at least one non-NaN
        training value. Features that are entirely NaN in training are omitted
        (no support to reason about → never flagged as out-of-support).
    """
    feat = _numeric_features(X_train)
    support: dict[str, tuple[float, float]] = {}
    for col in feat.columns:
        series = pd.to_numeric(feat[col], errors="coerce").dropna()
        if series.empty:
            continue
        lo = float(series.quantile(SUPPORT_LOW_Q))
        hi = float(series.quantile(SUPPORT_HIGH_Q))
        support[col] = (lo, hi)
    return support


def is_out_of_support(
    x_row: Mapping[str, Any] | pd.Series,
    support: Mapping[str, tuple[float, float]],
) -> bool:
    """Return True if any (non-missing) feature falls outside its training support.

    The extrapolation half of the D5-09 abstention trigger (the walk-forward at
    05-09 abstains when a covered IPO is ``is_out_of_support``). A missing (NaN /
    absent) feature is NOT out-of-support — there is nothing to extrapolate from;
    only a present value outside its ``[q01, q99]`` bound flags extrapolation.

    Args:
        x_row: one feature vector (mapping or Series: feature -> value).
        support: the ``training_support`` bounds.

    Returns:
        ``True`` iff at least one present feature value is below its ``q01`` or
        above its ``q99`` training-support bound.
    """
    for feature, (lo, hi) in support.items():
        if isinstance(x_row, pd.Series):
            if feature not in x_row.index:
                continue
            value = x_row[feature]
        else:
            if feature not in x_row:
                continue
            value = x_row[feature]
        if value is None:
            continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if np.isnan(v):
            continue
        if v < lo or v > hi:
            return True
    return False


__all__ = [
    "SELECTED_FEATURES",
    "SUPPORT_LOW_Q",
    "SUPPORT_HIGH_Q",
    "MAX_SELECTED_DEFAULT",
    "select_features",
    "training_support",
    "is_out_of_support",
]
