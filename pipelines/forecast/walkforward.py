"""
pipelines/forecast/walkforward.py — the expanding-window, as-of-T0 walk-forward
loop (D5-11 / FCAST-03), the honesty keystone of the forecaster.

One pass over the universe ordered by ``listing_date``. For each IPO ``i`` the
train + calibration POOL is STRICTLY the IPOs that listed before ``i``'s T0
(issue-open day, D5-01):

    pool = { rows : listing_date < ipo.issue_date }

so no future IPO can ever enter ``i``'s training or calibration set — the loop is
provably lookahead-free (that is exactly what tests/unit/test_walkforward_no_lookahead.py
asserts, per fold, using the provenance columns this loop records). The single
out-of-sample band it emits for ``i`` IS the number the UI later renders for that
covered IPO: **displayed band = backtested band** (D5-11) — one code path, no second
"display" prediction.

The split (valid conformal coverage)
------------------------------------
Conformalized-quantile regression needs a calibration set DISJOINT from the
quantile-training set AND entirely before T0_i. So the pre-T0 pool is split by
LISTING DATE into an older *proper-train* slice and a newer *calibration* slice:

    cut = pool.listing_date.quantile(1 - cal_frac)
    proper-train = pool[listing_date <= cut]     # older
    calibration  = pool[listing_date >  cut]     # newer, still < T0_i

Both stay strictly before T0_i; they are disjoint by construction. We never
KFold/shuffle (CLAUDE.md "What NOT to Use": shuffled CV leaks future IPOs).

Abstention (D5-09, honesty)
---------------------------
An IPO with fewer than ``min_train`` prior listings (or one whose pre-T0 pool
cannot be split into a non-empty proper-train slice and a calibration slice of at
least ``MIN_CAL`` rows) gets an ABSTAIN row (``abstain=True,
abstain_reason="insufficient_history"``) and NO band — never a fabricated interval.

R²>0.5 leakage alarm (P4)
-------------------------
``r2_leakage_alarm`` computes the walk-forward out-of-sample R² of the MEDIAN vs
the realized return and returns a plain-text alarm when it exceeds 0.5 — an
automated gate for the model card, mirroring
``pipelines.historical.validate.sanity_check_median``'s ``(value, flag_or_None)``
posture. A pre-apply, no-demand model should be humble; a high R² almost always
means a T0-violating feature slipped in.

NO NETWORK / NO MODEL AT IMPORT
-------------------------------
The heavy modelling stack (xgboost / mapie) is reached only transitively through
``pipelines.forecast.model``'s LAZY (in-function) imports; sklearn's ``r2_score``
is likewise imported lazily inside ``r2_leakage_alarm``. Importing THIS module
pulls in only stdlib + numpy + pandas + the import-light model wrappers — it stays
offline.

ISOLATION (FCAST-02, Direction 2): this module references NOTHING from the display
signal — the model never sees it. Pinned by tests/unit/test_forecast_isolation.py.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from pipelines.forecast.model import (
    CONFIDENCE_LEVEL,
    fit_cqr,
    make_quantile_models,
    predict_band,
)

# ---------------------------------------------------------------------------
# Walk-forward defaults (D5-09 tuning territory — wired empirically in 05-09)
# ---------------------------------------------------------------------------
MIN_TRAIN_DEFAULT: int = 60  # abstain until this many prior listings exist
CAL_FRAC_DEFAULT: float = 0.25  # newest 25% of the pre-T0 pool is the calibration set
R2_LEAKAGE_THRESHOLD: float = 0.5  # OOS R² above this fires the P4 leakage alarm

# Minimum calibration-slice size for a valid split-CQR interval. MAPIE must
# estimate the TAIL conformity quantile (each tail = (1-confidence_level)/2), which
# requires n_cal >= 1/tail = ceil(2 / (1-confidence_level)) samples — 10 for the
# 80% interval. A pool whose newest slice is thinner than this cannot calibrate an
# honest band, so the IPO abstains (D5-09) rather than crash or fabricate.
MIN_CAL: int = math.ceil(2.0 / (1.0 - CONFIDENCE_LEVEL))

# The out-of-sample frame's columns. The first block is the record/metrics input
# the plan calls for (drhp_id/issuer, actual, low, high, median, listing_year,
# abstain); the second block is per-fold PROVENANCE that makes the no-lookahead
# property auditable (the exact pool/train/calibration boundaries this loop used).
OOS_COLUMNS: tuple[str, ...] = (
    "drhp_id",
    "issuer",
    "actual",
    "low",
    "high",
    "median",
    "listing_year",
    "abstain",
    "abstain_reason",
    # provenance (no-lookahead proof surface):
    "t0",
    "pool_max_listing_date",
    "train_max_listing_date",
    "cal_min_listing_date",
    "n_train",
    "n_cal",
)

_REQUIRED_PANEL_COLUMNS = ("issuer", "issue_date", "listing_date", "listing_day_return")


def _abstain_row(
    *,
    drhp_id: str | None,
    issuer: str,
    actual: float,
    listing_year: int | None,
    t0,
    reason: str,
) -> dict:
    """A no-band abstain row (D5-09): honest absence, never a fabricated interval."""
    return {
        "drhp_id": drhp_id,
        "issuer": issuer,
        "actual": actual,
        "low": float("nan"),
        "high": float("nan"),
        "median": float("nan"),
        "listing_year": listing_year,
        "abstain": True,
        "abstain_reason": reason,
        "t0": t0,
        "pool_max_listing_date": pd.NaT,
        "train_max_listing_date": pd.NaT,
        "cal_min_listing_date": pd.NaT,
        "n_train": 0,
        "n_cal": 0,
    }


def walk_forward(
    panel: pd.DataFrame,
    X: pd.DataFrame,
    *,
    min_train: int = MIN_TRAIN_DEFAULT,
    cal_frac: float = CAL_FRAC_DEFAULT,
    params: dict | None = None,
) -> pd.DataFrame:
    """Run the expanding-window as-of-T0 walk-forward, one OOS band per IPO.

    Args:
        panel: an assembled historical panel (``pipelines.historical`` contract) —
            must carry ``issuer``, ``issue_date`` (T0), ``listing_date`` and
            ``listing_day_return`` (the target); an optional ``drhp_id`` column is
            carried through when present.
        X: the leakage-gated feature matrix aligned to ``panel`` by index (e.g. the
            output of ``pipelines.features.build.build_features`` — or a fixture).
            An ``available_at`` stamp column, if present, is dropped before fitting.
        min_train: abstain until at least this many prior listings exist (D5-09).
        cal_frac: newest fraction of the pre-T0 pool used as the calibration slice.
        params: optional XGBoost overrides forwarded to ``make_quantile_models``.

    Returns:
        A DataFrame with ``OOS_COLUMNS``: one row per scorable IPO (known target +
        known dates), ordered by ``listing_date``. Covered rows carry the
        out-of-sample ``(low, high, median)`` band; abstain rows carry no band and
        an ``abstain_reason``. Provenance columns record the exact pool / train /
        calibration boundaries used (the no-lookahead audit surface).

    Raises:
        ValueError: if ``panel`` is missing a required column.
    """
    missing = set(_REQUIRED_PANEL_COLUMNS) - set(panel.columns)
    if missing:
        raise ValueError(
            f"walk_forward panel is missing required column(s): {sorted(missing)}"
        )

    # Drop the availability stamp (kept only for the leakage gate) — the model
    # sees numeric features only.
    feat = X.drop(columns=["available_at"], errors="ignore")
    has_drhp = "drhp_id" in panel.columns

    # Scorable universe: a KNOWN target and known issue/listing dates. Withdrawn
    # IPOs (NaN return, NaT listing_date) are correctly neither trained on nor
    # scored — but they are retained upstream (survivorship), never dropped there.
    usable = panel[
        panel["listing_day_return"].notna()
        & panel["listing_date"].notna()
        & panel["issue_date"].notna()
    ].sort_values("listing_date")

    rows_out: list[dict] = []
    for idx, ipo in usable.iterrows():
        t0 = ipo["issue_date"]  # T0 = issue-open (D5-01)
        issuer = ipo["issuer"]
        actual = float(ipo["listing_day_return"])
        listing_year = int(pd.Timestamp(ipo["listing_date"]).year)
        drhp_id = ipo["drhp_id"] if has_drhp else None

        # STRICT no-lookahead pool: IPOs that LISTED before this IPO's T0.
        pool = usable[usable["listing_date"] < t0]

        if len(pool) < min_train:
            rows_out.append(
                _abstain_row(
                    drhp_id=drhp_id,
                    issuer=issuer,
                    actual=actual,
                    listing_year=listing_year,
                    t0=t0,
                    reason="insufficient_history",
                )
            )
            continue

        # Split the pre-T0 pool by listing date: older proper-train, newer calib.
        cut = pool["listing_date"].quantile(1.0 - cal_frac)
        tr = pool[pool["listing_date"] <= cut]
        cal = pool[pool["listing_date"] > cut]

        # A valid conformal split needs a non-empty proper-train slice and a
        # calibration slice large enough to estimate the tail conformity quantile
        # (>= MIN_CAL; the <=cut / >cut partition already guarantees disjointness).
        # Too-thin calibration is not enough usable history yet — abstain rather
        # than fabricate a band (D5-09).
        if len(tr) == 0 or len(cal) < MIN_CAL:
            rows_out.append(
                _abstain_row(
                    drhp_id=drhp_id,
                    issuer=issuer,
                    actual=actual,
                    listing_year=listing_year,
                    t0=t0,
                    reason="insufficient_history",
                )
            )
            continue

        models = make_quantile_models(
            feat.loc[tr.index], tr["listing_day_return"], params
        )
        cqr = fit_cqr(models, feat.loc[cal.index], cal["listing_day_return"])
        median, low, high = predict_band(cqr, feat.loc[[idx]])

        rows_out.append(
            {
                "drhp_id": drhp_id,
                "issuer": issuer,
                "actual": actual,
                "low": float(low[0]),
                "high": float(high[0]),
                "median": float(median[0]),
                "listing_year": listing_year,
                "abstain": False,
                "abstain_reason": None,
                "t0": t0,
                "pool_max_listing_date": pool["listing_date"].max(),
                "train_max_listing_date": tr["listing_date"].max(),
                "cal_min_listing_date": cal["listing_date"].min(),
                "n_train": int(len(tr)),
                "n_cal": int(len(cal)),
            }
        )

    return pd.DataFrame(rows_out, columns=list(OOS_COLUMNS))


def r2_leakage_alarm(
    oos_df: pd.DataFrame,
    threshold: float = R2_LEAKAGE_THRESHOLD,
) -> tuple[float, str | None]:
    """Fire a P4 leakage alarm when the walk-forward OOS median R² exceeds threshold.

    Computes R² of the realized return vs the predicted MEDIAN over the covered
    (non-abstain) out-of-sample rows. Returns ``(r2, flag_or_None)`` — a plain-text
    alarm string when ``r2 > threshold``, else ``None`` — mirroring
    ``pipelines.historical.validate.sanity_check_median``'s posture. A pre-apply,
    no-demand forecast is expected to be humble; a high R² almost always means a
    T0-violating feature leaked into training (P4 / FCAST-02).

    Args:
        oos_df: a walk-forward frame (``OOS_COLUMNS``) or any frame with
            ``actual`` + ``median`` (+ optional ``abstain``) columns.
        threshold: the leakage R² ceiling (0.5, per the ROADMAP P4 guard).

    Returns:
        ``(r2, flag)`` where ``flag`` is the alarm string if ``r2 > threshold``
        else ``None``. ``r2`` is ``NaN`` (and ``flag`` ``None``) when fewer than
        two covered rows exist.
    """
    from sklearn.metrics import r2_score  # lazy: keeps module import offline

    scored = oos_df
    if "abstain" in scored.columns:
        scored = scored[~scored["abstain"].astype(bool)]
    scored = scored.dropna(subset=["actual", "median"])

    n = int(len(scored))
    if n < 2:
        return float("nan"), None

    r2 = float(r2_score(scored["actual"].to_numpy(), scored["median"].to_numpy()))
    if r2 > threshold:
        flag = (
            f"LEAKAGE ALARM: walk-forward out-of-sample R²={r2:.3f} exceeds "
            f"{threshold:.2f} (n={n}). A pre-apply, no-demand forecast should be "
            f"humble — a high R² almost always means a T0-violating feature slipped "
            f"into training. Audit the available_at gate before shipping (P4/FCAST-02)."
        )
        return r2, flag
    return r2, None


__all__ = [
    "MIN_TRAIN_DEFAULT",
    "CAL_FRAC_DEFAULT",
    "R2_LEAKAGE_THRESHOLD",
    "MIN_CAL",
    "OOS_COLUMNS",
    "walk_forward",
    "r2_leakage_alarm",
]
