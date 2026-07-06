"""
pipelines/historical/ — Survivorship-corrected historical Indian mainboard IPO panel.

This package builds the backend data foundation for Phase 5's listing-return
forecaster (FCAST-03). It is NOT user-visible in Phase 4 (except the one
`/methodology` divergence flag surfaced by `validate.py`).

The DS-critical control is P3 (survivorship bias): the universe is sourced
issuer-side (SEBI / chittorgarh's historical IPO index, which lists withdrawn
and pulled IPOs) rather than from survivor-only exchange "currently-listed"
feeds. Every IPO carries an explicit `status` column, and any company whose
listing-day price is unavailable is kept with `listing_day_return = NaN`
(replace-with-NaN) — the absence is COUNTED, never dropped.

This module (`__init__`) owns the **row-schema / column contract**:
  - `PANEL_COLUMNS`   — the ordered, minimal, Phase-5-extensible column set.
  - `PANEL_DTYPES`    — dtypes chosen so NaN survives (float returns; string status).
  - `STATUS_VALUES`   — the survivorship status taxonomy (the P3 control surface).
  - `compute_listing_day_return()` — the honest return formula (NaN when unknown).
  - `assemble_panel()` — build a typed frame from raw rows, deriving the return
                         and applying replace-with-NaN (NEVER dropping a row).

`build.py` (the universe assembler + artifact writer + CLI) and `validate.py`
(the ~7% median MAAR sanity-check) both import this contract. Keep the schema
minimal — feature engineering is Phase 5.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Status taxonomy (the P3 survivorship control surface)
# ---------------------------------------------------------------------------
# An honest 2014-present mainboard universe MUST be able to represent every one
# of these — a universe with zero `withdrawn`/`delisted` rows is a survivorship
# red flag (see validate.py + 04-RESEARCH.md §Pitfall 3).
STATUS_VALUES: frozenset[str] = frozenset(
    {
        "withdrawn",      # IPO was filed/announced but pulled before listing
        "listed_alive",   # listed and still trading
        "delisted",       # listed then delisted (voluntary/compulsory)
        "merged",         # ceased to exist as a standalone listed entity
        "name_changed",   # same entity, renamed post-listing
    }
)

# ---------------------------------------------------------------------------
# Column contract (minimal, Phase-5-extensible — NO feature engineering here)
# ---------------------------------------------------------------------------
PANEL_COLUMNS: tuple[str, ...] = (
    "issuer",             # company name exactly as disclosed (str)
    "issue_date",         # DRHP/issue date (datetime64, nullable)
    "listing_date",       # exchange listing date (datetime64, nullable — NaT if never listed)
    "issue_price",        # final IPO offer price per share, INR (float, nullable)
    "listing_day_close",  # listing-day EOD close, INR (float, nullable — NaN if unavailable)
    "listing_day_return", # (close - issue) / issue (float, NaN when unknown — the target)
    "status",             # one of STATUS_VALUES (str/categorical)
)

# dtypes chosen so NaN/NaT survive a round-trip through parquet+CSV.
PANEL_DTYPES: dict[str, str] = {
    "issuer": "string",
    "issue_date": "datetime64[ns]",
    "listing_date": "datetime64[ns]",
    "issue_price": "float64",
    "listing_day_close": "float64",
    "listing_day_return": "float64",
    "status": "string",
}


# ---------------------------------------------------------------------------
# Listing-day return — the honest formula (NaN when unknown, never 0)
# ---------------------------------------------------------------------------


def compute_listing_day_return(
    issue_price: float | None,
    listing_day_close: float | None,
) -> float:
    """Return the listing-day simple return, or NaN when it cannot be computed.

    (listing_day_close - issue_price) / issue_price.

    Returns ``float('nan')`` — NOT 0.0 — whenever either price is missing/NaN or
    the issue price is non-positive. A missing return is an HONEST absence to be
    RETAINED as a NaN row (replace-with-NaN survivorship), never a fabricated
    zero and never a reason to drop the IPO.
    """
    ip = _to_float_or_nan(issue_price)
    lc = _to_float_or_nan(listing_day_close)
    if math.isnan(ip) or math.isnan(lc) or ip <= 0:
        return float("nan")
    return (lc - ip) / ip


def _to_float_or_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return f


# ---------------------------------------------------------------------------
# Panel assembly — typed frame + replace-with-NaN (NEVER drop a row)
# ---------------------------------------------------------------------------


def assemble_panel(rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Assemble raw per-IPO row dicts into the typed, survivorship-corrected panel.

    For each row:
      - `status` is validated against STATUS_VALUES (an unknown status RAISES —
        malformed rows must be caught upstream and isolated, never silently
        coerced into a survivor; T-04-07-VALID).
      - `listing_day_return` is taken as given if a caller supplied a non-NaN
        value, otherwise DERIVED from issue_price + listing_day_close.
      - a row whose listing-day price is unavailable keeps
        `listing_day_return = NaN` and is RETAINED — the returned frame has
        exactly as many rows as the input (replace-with-NaN, never drop).

    Args:
        rows: iterable of mappings carrying at least `issuer` and `status`.

    Returns:
        A DataFrame with exactly PANEL_COLUMNS (in order) and PANEL_DTYPES.

    Raises:
        ValueError: if a row carries a `status` not in STATUS_VALUES.
    """
    records: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        status = row.get("status")
        if status not in STATUS_VALUES:
            raise ValueError(
                f"Row {i} (issuer={row.get('issuer')!r}) has invalid "
                f"status={status!r}; must be one of {sorted(STATUS_VALUES)}."
            )

        issue_price = _to_float_or_nan(row.get("issue_price"))
        listing_close = _to_float_or_nan(row.get("listing_day_close"))

        # Honor a caller-supplied return only when it is a real (non-NaN) number;
        # otherwise derive it. Missing => NaN (retained), never dropped.
        supplied_return = _to_float_or_nan(row.get("listing_day_return"))
        listing_return = (
            supplied_return
            if not math.isnan(supplied_return)
            else compute_listing_day_return(issue_price, listing_close)
        )

        records.append(
            {
                "issuer": row.get("issuer"),
                "issue_date": row.get("issue_date"),
                "listing_date": row.get("listing_date"),
                "issue_price": issue_price,
                "listing_day_close": listing_close,
                "listing_day_return": listing_return,
                "status": status,
            }
        )

    df = pd.DataFrame.from_records(records, columns=list(PANEL_COLUMNS))
    return coerce_panel(df)


def coerce_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a panel DataFrame to PANEL_COLUMNS order + PANEL_DTYPES.

    Idempotent; used by both `assemble_panel` and on-load after reading a
    committed parquet/CSV so NaN/NaT survive the round-trip.
    """
    missing = set(PANEL_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Panel is missing required column(s): {sorted(missing)}")

    df = df.loc[:, list(PANEL_COLUMNS)].copy()
    for col, dtype in PANEL_DTYPES.items():
        if dtype == "datetime64[ns]":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            df[col] = df[col].astype(dtype)
    return df


__all__ = [
    "STATUS_VALUES",
    "PANEL_COLUMNS",
    "PANEL_DTYPES",
    "compute_listing_day_return",
    "assemble_panel",
    "coerce_panel",
]
