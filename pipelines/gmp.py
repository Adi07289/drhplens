"""
pipelines/gmp.py — the read-only grey-market-premium pre-compute pipeline.

Mirrors pipelines/redflag.py's allow-list path-gate + Typer CLI, but WITHOUT the
agent graph: GMP is not extracted from the DRHP. It is scraped from 2-3 public
aggregator sites (pipelines/gmp_sources.py) purely as read-only, cache-only
DISPLAY data with caveats — never a demand indicator (Pitfall 5).

Each aggregator is fetched with PER-SOURCE failure isolation: one aggregator
failing is logged and skipped, never aborts the record and never fabricates a
value for it. The reachable aggregators' quotes are kept SEPARATE in the
GmpRecord so their disagreement (the honesty signal, D4-01) is preserved.

Absent GMP (`quotes == []`) is a FIRST-CLASS state and the COMMON case — 7 of 8
catalogue IPOs are already listed, so no live grey-market premium is being
reported. It is committed as an honest empty record, NOT a zero and NOT an error.
Single-source GMP (`len == 1`) is likewise first-class (no cross-source check).

Path safety (T-04-04-PATH): precompute_gmp / load_gmp gate <drhp_id> through the
Phase 2 is_known_drhp_id allow-list (data/catalogue_loader.py) BEFORE forming any
data/gmp/<id>.json path — a non-allow-listed id raises, no path is built.

CODE-NOW-DEFER (04-04-PLAN.md objective): fully unit-tested by monkeypatching the
aggregator fetchers — NO live network happens under `pytest tests/unit`. The real
live scrape (open-IPO window) is a deferred human runbook step. Two hand-seeded
fixtures (data/gmp/swiggy_2024_11.json absent, data/gmp/hyundai_2024_10.json a
synthetic 3-source spread) unblock the renderer (04-06) offline.

ISOLATION (GMP-02, D4-03): this module imports NOTHING from any modelling library
or downstream prediction/historical pipeline. Pinned by
tests/unit/test_gmp_isolation.py (an inspect.getsource substring audit).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

from agent.gmp_schema import GmpRecord
from data.catalogue_loader import is_known_drhp_id
from pipelines import gmp_sources

app = typer.Typer(help="DRHPLens grey-market-premium pre-compute pipeline.")
console = Console()

GMP_DIR: Path = Path(__file__).parent.parent / "data" / "gmp"


# ---------------------------------------------------------------------------
# load_gmp
# ---------------------------------------------------------------------------


def load_gmp(drhp_id: str) -> GmpRecord:
    """Read data/gmp/<drhp_id>.json into a GmpRecord.

    Args:
        drhp_id: e.g. "hyundai_2024_10". Must be a known catalogue id (T-04-04-PATH).

    Returns:
        The validated GmpRecord (an absent-GMP record has quotes == []).

    Raises:
        ValueError: if drhp_id is not in the catalogue allow-list.
        FileNotFoundError: if the GMP cache file does not exist.
    """
    path = _gmp_path(drhp_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No GMP cache found for drhp_id={drhp_id!r} at {path}"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return GmpRecord.from_dict(raw)


def _gmp_path(drhp_id: str) -> Path:
    """Form the cache path, gating drhp_id through the allow-list (T-04-04-PATH).

    Raises:
        ValueError: if drhp_id is not a known catalogue entry — the path is never
        formed for an untrusted id (path-traversal mitigation, verbatim from
        pipelines/redflag.py).
    """
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to form a cache path "
            f"(catalogue allow-list, T-04-04-PATH)."
        )
    return GMP_DIR / f"{drhp_id}.json"


def _issuer_name(drhp_id: str) -> str | None:
    """Look up the IPO issuer's display name from the catalogue (the scrape key)."""
    from data.catalogue_loader import load_catalogue

    for ipo in load_catalogue():
        if ipo.drhp_id == drhp_id:
            return ipo.issuer
    return None


# ---------------------------------------------------------------------------
# precompute_gmp — the per-aggregator scrape loop with per-source isolation
# ---------------------------------------------------------------------------


def precompute_gmp(drhp_id: str, *, write: bool = True) -> GmpRecord:
    """Scrape each public aggregator for one IPO's GMP and assemble a GmpRecord.

    For each aggregator in gmp_sources.source_fetchers():
      - a returned GmpQuote is appended (its value kept separate, D4-01).
      - None (no live quote — the common already-listed case) or a raised
        exception is isolated: it is skipped, never aborts the record, and never
        fabricates a value for that aggregator (P14 / Pitfall 5).

    A record with no reachable aggregator quote is the honest absent-GMP state
    (`quotes == []`), committed as-is — never a zero.

    Args:
        drhp_id: e.g. "hyundai_2024_10". Must be allow-listed (T-04-04-PATH).
        write: if True (default), write to data/gmp/<drhp_id>.json. Tests pass
            write=False.

    Returns:
        The computed GmpRecord.

    Raises:
        ValueError: if drhp_id is not a known catalogue entry (raised BEFORE any
        scrape or path formation — path-traversal mitigation T-04-04-PATH).
    """
    # T-04-04-PATH: gate the id up front, before any scrape or path is formed.
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to pre-compute GMP "
            f"for a non-allow-listed id (T-04-04-PATH)."
        )

    name = _issuer_name(drhp_id) or drhp_id

    quotes = []
    for label, fetcher in gmp_sources.source_fetchers():
        try:
            quote = fetcher(name)
        except Exception as exc:  # noqa: BLE001 — per-source failure isolation (P14)
            console.print(f"  [yellow]{label} unavailable: {exc}[/yellow]")
            quote = None
        if quote is not None:
            quotes.append(quote)

    now = datetime.now(timezone.utc)
    # Headline as-of: the latest quote's date where quotes exist, else the compute
    # date (an absent record still carries an honest as-of for the sub-line).
    as_of = max((q.as_of for q in quotes), default=now.strftime("%Y-%m-%d"))

    record = GmpRecord(
        drhp_id=drhp_id,
        computed_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        as_of=as_of,
        quotes=quotes,
    )

    if write:
        path = _gmp_path(drhp_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.to_json(), encoding="utf-8")

    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command(name="precompute-one")
def precompute_one(
    drhp_id: str = typer.Argument(
        ..., help="The drhp_id to pre-compute, e.g. hyundai_2024_10"
    ),
) -> None:
    """Pre-compute the GMP record for one IPO."""
    console.rule(f"[bold blue]Pre-computing GMP for {drhp_id}[/bold blue]")
    record = precompute_gmp(drhp_id)
    spread = record.spread()
    console.print(
        f"  quotes={len(record.quotes)} "
        f"spread={'—' if spread is None else f'{spread.low}-{spread.high} (n={spread.n})'}"
    )
    console.print(f"  Written to data/gmp/{drhp_id}.json")


@app.command(name="precompute-all")
def precompute_all() -> None:
    """Loop over data/catalogue.json and pre-compute every IPO's GMP record.

    Per-IPO failure isolation (mirrors pipelines.redflag.precompute_all's P14
    posture) — one IPO's exception is logged and skipped; it does not abort the
    batch. Most catalogue IPOs are already listed → an honest absent-GMP record.
    """
    from data.catalogue_loader import load_catalogue

    catalogue = load_catalogue()
    console.rule(
        f"[bold blue]Pre-computing GMP for {len(catalogue)} IPOs[/bold blue]"
    )

    results: list[tuple[str, str]] = []
    for ipo in catalogue:
        console.print(f"\n[bold]{ipo.drhp_id}[/bold] ({ipo.issuer})")
        try:
            record = precompute_gmp(ipo.drhp_id)
            console.print(f"  quotes={len(record.quotes)}")
            results.append((ipo.drhp_id, "ok"))
        except Exception as exc:  # noqa: BLE001 — per-IPO failure isolation (P14)
            console.print(f"  [red]FAILED: {exc}[/red]")
            results.append((ipo.drhp_id, "failed"))

    console.print("\n[bold]Summary[/bold]")
    for drhp_id, status in results:
        console.print(f"  {drhp_id}: {status}")


if __name__ == "__main__":
    app()
