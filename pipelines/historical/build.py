"""
pipelines/historical/build.py — Survivorship-corrected historical IPO panel builder.

Assembles the 2014-present Indian mainboard IPO universe (~800–1000 rows) from
the issuer-side sources in `sources.py`, derives the `status` column, computes
the listing-day return, applies REPLACE-WITH-NaN for missing listing prices
(never drops a row), runs the ~7% median MAAR sanity-check
(`validate.sanity_check_median`), and writes BOTH:

  - `data/historical/ipo_panel.parquet`  (the Phase-5 consumable, FCAST-03)
  - `data/historical/ipo_panel.csv`      (a git-diff-reviewable mirror)
  - `data/historical/README.md`          (column contract + the median result)

Two CLI commands:
  - `build`         — the LIVE full crawl (network). Deferred to the 04-07
                      human/network checkpoint; NOT run in the executor sandbox.
  - `build-sample`  — writes a small, clearly-labelled hand-built SAMPLE panel
                      (a few fictional rows exercising every status + a NaN row)
                      so the artifact path and validator are exercised in CI
                      with no network. This is the artifact committed in Phase 4.

Schema is intentionally minimal (no feature engineering — that is Phase 5).
NO NETWORK AT IMPORT: every fetcher in `sources.py` imports its network client
lazily, and `build_panel` (the only live path) is never called at import.
"""
from __future__ import annotations

import datetime as _dt
import logging
from pathlib import Path

import pandas as pd
import typer
from rich.console import Console

from pipelines.historical import (
    PANEL_COLUMNS,
    STATUS_VALUES,
    assemble_panel,
    coerce_panel,
)
from pipelines.historical import sources as _sources
from pipelines.historical.validate import band_text, sanity_check_median

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer(help="DRHPLens survivorship-corrected historical IPO panel builder.")

DATA_DIR: Path = Path(__file__).parent.parent.parent / "data" / "historical"
PANEL_PARQUET: Path = DATA_DIR / "ipo_panel.parquet"
PANEL_CSV: Path = DATA_DIR / "ipo_panel.csv"
PANEL_README: Path = DATA_DIR / "README.md"

# Mainboard universe window (P3): 2014-present. Withdrawn/delisted IPOs in this
# window MUST be represented — a universe with zero of them is a survivorship
# red flag (see validate.py + 04-RESEARCH.md §Pitfall 3).
UNIVERSE_START = _dt.date(2014, 1, 1)


# ---------------------------------------------------------------------------
# Status derivation (the P3 taxonomy) — honest, never assume a survivor.
# ---------------------------------------------------------------------------


def derive_status(row: dict) -> str:
    """Derive the panel `status` for a raw source row.

    A row explicitly marked pulled/withdrawn stays `withdrawn` even though it
    has no listing price (the whole point of P3). A row with a listing date and
    no negative signal is `listed_alive`. Explicit delisted/merged/name_changed
    signals from the source are honoured via `sources.normalize_status`.
    """
    raw_status = row.get("status") or row.get("status_raw")
    has_listing = row.get("listing_date") is not None
    return _sources.normalize_status(raw_status, listed=has_listing)


# ---------------------------------------------------------------------------
# Live build (network) — DEFERRED to the 04-07 checkpoint. Not run in tests.
# ---------------------------------------------------------------------------


def build_panel(*, write: bool = True) -> pd.DataFrame:  # pragma: no cover - live
    """Build the full survivorship-corrected panel from live issuer-side sources.

    LIVE NETWORK. Deferred to the 04-07 human/network checkpoint — do NOT call
    from the executor sandbox or from any test. Per-source failure isolation
    keeps one flaky source from aborting the batch.
    """
    console.rule("[bold blue]Building historical IPO panel (LIVE)[/bold blue]")

    raw_rows: list[dict] = []
    try:
        raw_rows.extend(_sources.fetch_chittorgarh_index())
    except Exception as exc:  # noqa: BLE001 - per-source isolation (P14)
        console.print(f"[red]chittorgarh index failed: {exc}[/red]")
    try:
        raw_rows.extend(_sources.fetch_sebi_offer_documents())
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]SEBI issuer-side failed: {exc}[/red]")

    rows: list[dict] = []
    for raw in raw_rows:
        if raw.get("issue_date") and raw["issue_date"] < UNIVERSE_START:
            continue
        status = derive_status(raw)
        rows.append(
            {
                "issuer": raw.get("issuer"),
                "issue_date": raw.get("issue_date"),
                "listing_date": raw.get("listing_date"),
                "issue_price": raw.get("issue_price"),
                "listing_day_close": raw.get("listing_day_close"),
                "status": status,
            }
        )

    df = assemble_panel(rows)
    if write:
        write_panel(df)
    return df


# ---------------------------------------------------------------------------
# Artifact writer (parquet + CSV + README with the median sanity result).
# ---------------------------------------------------------------------------


def write_panel(df: pd.DataFrame, *, is_sample: bool = False) -> dict:
    """Write the panel to parquet + CSV and a README carrying the median result.

    Parquet is the Phase-5 consumable. If `pyarrow` is unavailable the parquet
    write becomes a deferred seam (a `.PARQUET_PENDING` marker is written and the
    CSV remains the source of truth) — the runbook notes pyarrow as a dependency.

    Returns a dict summary: {n_rows, median, flag, status_counts, wrote_parquet}.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = coerce_panel(df)

    median, flag = sanity_check_median(df)
    status_counts = df["status"].value_counts(dropna=False).to_dict()

    # CSV mirror always (dtype-lossy but human-diffable).
    df.to_csv(PANEL_CSV, index=False)

    wrote_parquet = False
    try:
        df.to_parquet(PANEL_PARQUET, index=False)
        wrote_parquet = True
    except Exception as exc:  # noqa: BLE001 - pyarrow missing => deferred seam
        logger.warning("parquet write deferred (pyarrow?): %s", exc)
        (DATA_DIR / "ipo_panel.PARQUET_PENDING").write_text(
            "Parquet write is deferred: install pyarrow to materialize "
            "data/historical/ipo_panel.parquet from ipo_panel.csv.\n",
            encoding="utf-8",
        )

    _write_readme(
        median=median,
        flag=flag,
        n_rows=len(df),
        status_counts=status_counts,
        is_sample=is_sample,
        wrote_parquet=wrote_parquet,
    )

    return {
        "n_rows": len(df),
        "median": median,
        "flag": flag,
        "status_counts": status_counts,
        "wrote_parquet": wrote_parquet,
    }


def _write_readme(
    *,
    median: float,
    flag: str | None,
    n_rows: int,
    status_counts: dict,
    is_sample: bool,
    wrote_parquet: bool,
) -> None:
    kind = "HAND-BUILT SAMPLE" if is_sample else "FULL LIVE BUILD"
    median_str = "n/a (no scored rows)" if median != median else f"{median * 100:.2f}%"
    dist = ", ".join(
        f"{k}={v}" for k, v in sorted(status_counts.items(), key=lambda kv: str(kv[0]))
    )
    lines = [
        "# Historical IPO Panel (survivorship-corrected)",
        "",
        f"**Artifact kind:** {kind}",
        f"**Generated:** {_dt.date.today()}",
        f"**Rows:** {n_rows}",
        "",
    ]
    if is_sample:
        lines += [
            "> ⚠️ **THIS IS A SMALL HAND-BUILT SAMPLE, NOT THE FULL PANEL.**",
            "> The rows use *fictional* issuer names (\"Sample Alpha Ltd\", …) and",
            "> illustrative prices — no real IPO's returns are fabricated. It exists",
            "> only to exercise the schema, the artifact path, and the validator in",
            "> CI without network. The full ~800–1000-row panel is produced by the",
            "> deferred live build at the 04-07 checkpoint (see Runbook below).",
            "",
        ]
    lines += [
        "## Column contract",
        "",
        "| Column | Meaning |",
        "|---|---|",
        "| `issuer` | Company name as disclosed |",
        "| `issue_date` | DRHP/issue date |",
        "| `listing_date` | Exchange listing date (NaT if never listed) |",
        "| `issue_price` | Final IPO offer price per share (INR) |",
        "| `listing_day_close` | Listing-day EOD close (INR; NaN if unavailable) |",
        "| `listing_day_return` | (close − issue) / issue (NaN when unknown — the target) |",
        f"| `status` | One of {sorted(STATUS_VALUES)} |",
        "",
        "**Survivorship (P3):** the universe is sourced issuer-side (chittorgarh /",
        "SEBI, which include withdrawn/pulled IPOs). A company with no listing-day",
        "price is kept with `listing_day_return = NaN` (replace-with-NaN) — the",
        "absence is COUNTED, never dropped.",
        "",
        "## Median MAAR sanity-check",
        "",
        f"- **Median listing-day return (scored rows):** {median_str}",
        f"- **Divergence flag:** {'FIRED — ' + flag if flag else 'none (in-band)'}",
        "",
        band_text(),
        "",
        f"- **Status distribution:** {dist}",
        f"- **Parquet written:** {wrote_parquet} (else CSV is the source of truth; "
        "install `pyarrow` — runbook dependency)",
        "",
        "## Runbook — full live build (deferred 04-07 checkpoint)",
        "",
        "Run in an environment with internet egress (chittorgarh/SEBI/NSE):",
        "",
        "```bash",
        ".venv/bin/python -m pipelines.historical.build build",
        "```",
        "",
        "Then confirm: row count ~800–1000, withdrawn/delisted statuses present",
        "(zero in a 2014-present universe is a survivorship red flag), and the",
        "median near the ~7% MAAR band (else the divergence flag above fires and is",
        "surfaced verbatim on /methodology). Commit the resulting parquet + CSV.",
    ]
    PANEL_README.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Offline SAMPLE panel — fictional rows exercising every status + a NaN row.
# ---------------------------------------------------------------------------


def sample_rows() -> list[dict]:
    """A few clearly-fictional rows: every status value + two NaN-return rows.

    Returns are chosen so the sample's median (~7%) sits in-band and the sample
    does not trip its own divergence flag. Issuer names are obviously synthetic
    ("Sample …") — no real IPO's return is fabricated (honesty invariant).
    """
    return [
        {
            "issuer": "Sample Alpha Ltd",
            "issue_date": "2018-03-01",
            "listing_date": "2018-03-12",
            "issue_price": 100.0,
            "listing_day_close": 108.0,  # +8%
            "status": "listed_alive",
        },
        {
            "issuer": "Sample Beta Ltd",
            "issue_date": "2017-07-01",
            "listing_date": "2017-07-13",
            "issue_price": 200.0,
            "listing_day_close": 214.0,  # +7%
            "status": "listed_alive",
        },
        {
            "issuer": "Sample Gamma Ltd",
            "issue_date": "2015-06-01",
            "listing_date": "2015-06-15",
            "issue_price": 150.0,
            "listing_day_close": 156.0,  # +4%
            "status": "delisted",
        },
        {
            "issuer": "Sample Delta Ltd",
            "issue_date": "2016-09-01",
            "listing_date": "2016-09-14",
            "issue_price": 300.0,
            "listing_day_close": 321.0,  # +7%
            "status": "merged",
        },
        {
            "issuer": "Sample Epsilon Ltd",
            "issue_date": "2019-01-10",
            "listing_date": "2019-01-22",
            "issue_price": 80.0,
            "listing_day_close": 86.0,  # +7.5%
            "status": "name_changed",
        },
        {
            # Withdrawn — never listed. Retained as a NaN-return row (P3).
            "issuer": "Sample Zeta Ltd",
            "issue_date": "2020-02-01",
            "listing_date": None,
            "issue_price": 120.0,
            "listing_day_close": None,
            "status": "withdrawn",
        },
        {
            # Listed but listing-day price unavailable — replace-with-NaN, retained.
            "issuer": "Sample Eta Ltd",
            "issue_date": "2021-11-01",
            "listing_date": "2021-11-15",
            "issue_price": 120.0,
            "listing_day_close": None,
            "status": "listed_alive",
        },
    ]


def build_sample_panel(*, write: bool = True) -> pd.DataFrame:
    """Assemble (and optionally write) the offline SAMPLE panel."""
    df = assemble_panel(sample_rows())
    if write:
        summary = write_panel(df, is_sample=True)
        console.print(
            f"  rows={summary['n_rows']} "
            f"statuses={sorted(df['status'].unique())} "
            f"median={summary['median'] * 100:.2f}% "
            f"flag={'FIRED' if summary['flag'] else 'none'}"
        )
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command(name="build")
def build_cli() -> None:  # pragma: no cover - live network
    """LIVE full build (~800–1000 IPOs). Deferred 04-07 checkpoint — needs egress."""
    summary = None
    df = build_panel(write=True)
    median, flag = sanity_check_median(df)
    console.print(
        f"[bold green]Wrote {len(df)} rows[/bold green] "
        f"statuses={sorted(df['status'].dropna().unique())} "
        f"median={median * 100:.2f}% flag={'FIRED' if flag else 'none'}"
    )
    _ = summary


@app.command(name="build-sample")
def build_sample_cli() -> None:
    """Write the small committed offline SAMPLE (no network)."""
    console.rule("[bold blue]Writing historical IPO panel SAMPLE (offline)[/bold blue]")
    build_sample_panel(write=True)
    console.print(f"  Written to {PANEL_PARQUET} + {PANEL_CSV} + {PANEL_README}")


if __name__ == "__main__":
    app()
