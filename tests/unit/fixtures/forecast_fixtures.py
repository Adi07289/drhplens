"""
tests/unit/fixtures/forecast_fixtures.py — shared offline builders for the Phase 5
listing-day-forecaster tests.

Every builder here is PURE and OFFLINE: it does no network I/O and trains no live
model. Given a fixed ``seed`` each returns a deterministic object, so the Wave 2-6
modeling tests (conformalized quantile regression, walk-forward CV, calibration
metrics, the four baselines) can assemble a tiny reproducible panel + feature
matrix + out-of-sample rows to exercise their logic without the real ~200-300-row
historical panel (which is a separate, later, live build).

Three builders:

- ``synthetic_panel(n=80, seed=0)`` — a survivorship-representable panel matching the
  ``pipelines.historical`` column contract (PANEL_COLUMNS / PANEL_DTYPES), ordered by
  listing_date, with a realistic heteroscedastic listing-day-return spread
  (~-20%..+60%) and every ``status`` in STATUS_VALUES present — including >=1
  ``withdrawn`` (never listed -> NaT listing_date, NaN return) and >=1 ``delisted``
  row so the P3 survivorship control surface is exercised (a universe with zero
  withdrawn/delisted rows is the survivorship red flag validate.py guards against).

- ``synthetic_features(panel, seed=1)`` — an X matrix of a few issue-structure
  columns (issue_size_cr, price_band_width_pct, ofs_fraction, promoter_dilution_pct,
  lot_size) aligned to the panel, each row stamped with an ``available_at`` timestamp
  set to that IPO's ``issue_date``. Issue-structure features are disclosed in the
  DRHP by the issue date, so ``available_at <= issue_date`` holds for every row — the
  no-leakage invariant (FCAST-02: features must carry available_at, walk-forward only).

- ``oos_rows(seed=2)`` — a small per-IPO out-of-sample frame
  (actual, low, high, median, listing_year) for the metrics / baselines tests. low <
  median < high always; ``actual`` lands inside the band for most rows but outside for
  some, so empirical coverage is a realistic value strictly below 1.0.

These are deliberately synthetic and self-consistent; they are NOT the real panel and
carry no real IPO data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pipelines.historical import PANEL_COLUMNS, STATUS_VALUES, assemble_panel


def _special_status_indices(n: int) -> dict[int, str]:
    """Assign a deterministic, disjoint set of non-``listed_alive`` statuses.

    Guarantees (for the default n=80, and any n >= 6) at least one ``withdrawn``
    and one ``delisted`` row, plus a ``merged`` and a ``name_changed`` row when n
    is large enough — so every member of STATUS_VALUES is representable (P3).
    """
    assigned: dict[int, str] = {}

    def _claim(idx: int, status: str) -> None:
        if 0 <= idx < n and idx not in assigned:
            assigned[idx] = status

    # withdrawn (never listed) — at least one, a second when the panel is large
    _claim(3, "withdrawn")
    _claim(n // 2, "withdrawn")
    # delisted (listed then delisted) — at least one, a second when large
    _claim(7, "delisted")
    _claim(n - 5, "delisted")
    # the remaining survivorship states, best-effort
    _claim(n // 3, "merged")
    _claim(n - 2, "name_changed")
    return assigned


def synthetic_panel(n: int = 80, seed: int = 0) -> pd.DataFrame:
    """Build a deterministic synthetic historical IPO panel (offline, no network).

    Returns a DataFrame with exactly ``PANEL_COLUMNS`` (issuer, issue_date,
    listing_date, issue_price, listing_day_close, listing_day_return, status),
    ``PANEL_DTYPES`` coerced, ordered by listing_date. ``withdrawn`` rows are never
    listed (NaT listing_date, NaN close -> NaN return, retained not dropped).
    """
    if n < 6:
        raise ValueError("synthetic_panel needs n >= 6 to represent the status taxonomy")

    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2016-01-01")
    # sorted day offsets across ~9 years -> listing_year varies for walk-forward CV
    offsets = np.sort(rng.integers(0, 365 * 9, size=n))
    special = _special_status_indices(n)

    rows: list[dict] = []
    for i in range(n):
        issue_price = float(round(rng.uniform(90.0, 1400.0), 1))
        # heteroscedastic return: per-IPO volatility varies 8%..30%, mean +6%
        vol = 0.08 + 0.22 * float(rng.random())
        ret = float(rng.normal(0.06, vol))
        ret = max(-0.20, min(0.60, ret))  # clip to the realistic -20%..+60% band

        listing_date = start + pd.Timedelta(days=int(offsets[i]))
        # issue opens 6-13 days before listing
        issue_date = listing_date - pd.Timedelta(days=int(6 + rng.integers(0, 8)))
        status = special.get(i, "listed_alive")

        if status == "withdrawn":
            # pulled before listing: no listing-day price -> NaN return, retained
            listing_date_val: object = pd.NaT
            listing_close: float = float("nan")
        else:
            listing_date_val = listing_date
            listing_close = round(issue_price * (1.0 + ret), 1)

        rows.append(
            {
                "issuer": f"SynthCo {i:03d} Ltd",
                "issue_date": issue_date,
                "listing_date": listing_date_val,
                "issue_price": issue_price,
                "listing_day_close": listing_close,
                "status": status,
            }
        )

    # assemble_panel validates status against STATUS_VALUES, derives the honest
    # listing_day_return (NaN when unknown), and coerces to PANEL_DTYPES.
    panel = assemble_panel(rows)
    panel = panel.sort_values("listing_date", na_position="last").reset_index(drop=True)
    return panel


def synthetic_features(panel: pd.DataFrame, seed: int = 1) -> pd.DataFrame:
    """Build a deterministic issue-structure feature matrix aligned to ``panel``.

    Columns: issue_size_cr, price_band_width_pct, ofs_fraction,
    promoter_dilution_pct, lot_size — all disclosed in the DRHP by the issue date —
    plus an ``available_at`` stamp set to each row's ``issue_date`` so the no-leakage
    invariant ``available_at <= issue_date`` holds for every row (FCAST-02).
    """
    rng = np.random.default_rng(seed)
    m = len(panel)
    if m == 0:
        raise ValueError("synthetic_features needs a non-empty panel")

    x = pd.DataFrame(
        {
            "issue_size_cr": np.round(rng.uniform(120.0, 9000.0, m), 1),
            "price_band_width_pct": np.round(rng.uniform(2.0, 12.0, m), 2),
            "ofs_fraction": np.round(rng.uniform(0.0, 1.0, m), 3),
            "promoter_dilution_pct": np.round(rng.uniform(2.0, 35.0, m), 2),
            "lot_size": rng.choice(
                [10, 12, 14, 15, 16, 18, 20, 22, 25, 30, 40], size=m
            ).astype("int64"),
        },
        index=panel.index,
    )
    # Issue-structure features are known at the DRHP/issue date -> available_at ==
    # issue_date (<= issue_date, no look-ahead leakage).
    x["available_at"] = pd.to_datetime(panel["issue_date"].to_numpy())
    return x


def oos_rows(seed: int = 2, n: int = 24) -> pd.DataFrame:
    """Build a small deterministic per-IPO out-of-sample frame for metrics/baselines.

    Columns: actual, low, high, median, listing_year. Invariants: low < median < high
    on every row; ``actual`` falls inside [low, high] for most rows but outside for
    some, so empirical coverage computed from these rows is a realistic value below
    1.0 (never a fabricated exact 0.80).
    """
    rng = np.random.default_rng(seed)
    years = list(range(2016, 2025))
    rows: list[dict] = []
    for k in range(n):
        year = years[k % len(years)]
        median = float(round(rng.normal(6.0, 8.0), 1))
        low = round(median - float(rng.uniform(8.0, 16.0)), 1)
        high = round(median + float(rng.uniform(10.0, 20.0)), 1)
        actual = float(round(median + rng.normal(0.0, 11.0), 1))
        rows.append(
            {
                "actual": actual,
                "low": low,
                "high": high,
                "median": median,
                "listing_year": year,
            }
        )
    return pd.DataFrame(rows, columns=["actual", "low", "high", "median", "listing_year"])


__all__ = [
    "PANEL_COLUMNS",
    "STATUS_VALUES",
    "synthetic_panel",
    "synthetic_features",
    "oos_rows",
]
