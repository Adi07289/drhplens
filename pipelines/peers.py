"""
pipelines/peers.py — Peer-comparator pre-compute pipeline (04-03-PLAN.md).

A mirror of pipelines/redflag.py. The DRHP's own disclosed peer SET (PEER-01) is
extracted by running the EXISTING compiled agent (agent.graph.GRAPH) once with the
canned pipelines.peer_queries.PEER_SET_QUERY — NO new LLM path, NO "peer mode" in
the graph, so the peer SET carries claim_id citations and its DRHP page for free
(reused by the Phase 1 citation-chip renderer). The graph's RefusalResponse return
IS the D4-06 honest empty-state (no listed-peer comparison disclosed) — stored as
the peer_set value, never a fabricated set.

The peer MULTIPLES (PEER-02, D4-05) are fetched per named peer through the
source-priority ladder in pipelines.peer_sources.resolve_multiples at PRECOMPUTE
TIME ONLY (D3-17 / P16 — never in load_peers or a page function). Each cell records
WHICH source supplied the value and its as-of dimension; a value missing from every
source is an honest "—".

Path safety (T-04-03-PATH): precompute_peers / load_peers gate <drhp_id> through
the Phase 2 is_known_drhp_id allow-list (data/catalogue_loader.py) BEFORE forming
any data/peers/<id>.json path — a non-allow-listed id raises, no path is built.

CODE-NOW-DEFER (04-03-PLAN.md objective): fully unit-tested by monkeypatching
agent.graph.GRAPH.invoke AND the peer_sources fetchers — no live Gemini/Qdrant and
no live screener.in/yfinance/NSE HTTP happen under `pytest tests/unit`. The real
live peer precompute (8×-per-IPO SET extraction + market-multiple scrape) is
deferred to the data ingest runbook. A hand-seeded data/peers/swiggy_2024_11.json
unblocks the renderer (04-05) offline.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

from agent.peer_schema import PeerCompany, PeerRecord
from data.catalogue_loader import is_known_drhp_id
from pipelines.peer_queries import PEER_SET_QUERY

app = typer.Typer(help="DRHPLens peer-comparator pre-compute pipeline.")
console = Console()

PEERS_DIR: Path = Path(__file__).parent.parent / "data" / "peers"

# Default refusal reason when GRAPH.invoke produces neither a grounded_answer nor a
# refusal (defensive fallback — the cache must never be left without an honest
# value; D4-06 honest empty-state).
_DEFAULT_REFUSAL_REASON = "low_retrieval_score"
_DEFAULT_REFUSAL_EXPLANATION = "This DRHP disclosed no listed-peer comparison."


# ---------------------------------------------------------------------------
# load_peers
# ---------------------------------------------------------------------------


def load_peers(drhp_id: str) -> PeerRecord:
    """Read data/peers/<drhp_id>.json into a PeerRecord.

    Args:
        drhp_id: e.g. "swiggy_2024_11". Must be a known catalogue id (T-04-03-PATH).

    Returns:
        The validated PeerRecord.

    Raises:
        ValueError: if drhp_id is not in the catalogue allow-list.
        FileNotFoundError: if the peer cache file does not exist.
    """
    path = _peers_path(drhp_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No peer cache found for drhp_id={drhp_id!r} at {path}"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return PeerRecord.from_dict(raw)


def _peers_path(drhp_id: str) -> Path:
    """Form the cache path, gating drhp_id through the allow-list (T-04-03-PATH).

    Raises:
        ValueError: if drhp_id is not a known catalogue entry — the path is never
        formed for an untrusted id (path-traversal mitigation, verbatim from
        pipelines/redflag.py).
    """
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to form a cache path "
            f"(catalogue allow-list, T-04-03-PATH)."
        )
    return PEERS_DIR / f"{drhp_id}.json"


def _make_refusal_response(reason: str, explanation: str):
    """Build a RefusalResponse for the D4-06 honest empty-state."""
    from agent.schemas import RefusalResponse

    return RefusalResponse(
        reason=reason,  # type: ignore[arg-type]
        explanation=explanation,
        reformulation_suggestions=[],
    )


# ---------------------------------------------------------------------------
# precompute_peers — the canned peer-SET agent invocation + per-cell ladder
# ---------------------------------------------------------------------------


def precompute_peers(drhp_id: str, *, write: bool = True) -> PeerRecord:
    """Extract the DRHP peer SET via the existing agent, then fetch per-cell multiples.

    1. PEER-01: run agent.graph.GRAPH.invoke({"question": PEER_SET_QUERY, ...}) ONCE.
       - a grounded answer that passed cite_check (all_claims_grounded True) → store
         the cited GroundedAnswer as the peer_set value, then loop its named peers
         through the source-priority ladder (PEER-02).
       - a RefusalResponse (no peer section) → store it as the peer_set value and
         fabricate NO peer companies (D4-06 honest empty-state).
    2. PEER-02: for each named peer AND the IPO's own row, call
       peer_sources.resolve_multiples at precompute time only.

    Args:
        drhp_id: e.g. "swiggy_2024_11". Must be allow-listed (T-04-03-PATH).
        write: if True (default), write to data/peers/<drhp_id>.json. Tests pass
            write=False.

    Returns:
        The computed PeerRecord.

    Raises:
        ValueError: if drhp_id is not a known catalogue entry (raised BEFORE any
        graph call or path formation — path-traversal mitigation T-04-03-PATH).
    """
    # T-04-03-PATH: gate the id up front, before any graph call or path is formed.
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to pre-compute peers "
            f"for a non-allow-listed id (T-04-03-PATH)."
        )

    from agent.graph import GRAPH

    state = GRAPH.invoke(
        {"question": PEER_SET_QUERY, "drhp_id": drhp_id, "regenerate_attempts": 0}
    )
    grounded_answer = state.get("grounded_answer")
    refusal = state.get("refusal")
    all_grounded = state.get("all_claims_grounded")

    if grounded_answer is not None and all_grounded:
        peer_set = grounded_answer
        companies = _build_companies(drhp_id, grounded_answer)
    elif refusal is not None:
        # D4-06 honest empty-state — store the refusal, fabricate no peers.
        peer_set = refusal
        companies = []
    else:
        # Defensive fallback — the cache must never lack an honest value.
        peer_set = _make_refusal_response(
            _DEFAULT_REFUSAL_REASON, _DEFAULT_REFUSAL_EXPLANATION
        )
        companies = []

    now = datetime.now(timezone.utc)
    record = PeerRecord(
        drhp_id=drhp_id,
        computed_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        as_of=now.strftime("%Y-%m-%d"),
        peer_set=peer_set,
        companies=companies,
    )

    if write:
        path = _peers_path(drhp_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.to_json(), encoding="utf-8")

    return record


def _build_companies(drhp_id: str, grounded_answer) -> list[PeerCompany]:
    """Assemble the peer rows: the IPO's own row first, then the DRHP-named peers.

    Each company's current-market multiples are resolved through the
    source-priority ladder (PEER-02) at precompute time. The IPO's own row is
    flagged is_ipo; its as-of-DRHP-date cells (source "d", as_of "drhp_date") are
    populated by the deferred DRHP-table extraction (see the seed fixture for the
    demonstrated BOTH-dimensions shape) — the live ladder supplies current-market.
    """
    from pipelines import peer_sources

    companies: list[PeerCompany] = []

    issuer = _issuer_name(drhp_id)
    if issuer:
        companies.append(
            PeerCompany(
                name=issuer,
                is_ipo=True,
                metrics=peer_sources.resolve_multiples(issuer),
            )
        )

    seen: set[str] = {issuer} if issuer else set()
    for name in _extract_peer_names(grounded_answer):
        if name in seen:
            continue
        seen.add(name)
        companies.append(
            PeerCompany(
                name=name,
                is_ipo=False,
                metrics=peer_sources.resolve_multiples(name),
            )
        )

    return companies


def _extract_peer_names(grounded_answer) -> list[str]:
    """Pull the disclosed peer names from the grounded answer's claims.

    Each cited claim names one disclosed listed peer (its claim.text is the peer
    name, exactly as disclosed — D4-04). Deduped, order-preserving. The live
    name-cleaning nuances are a deferred runbook detail; empty/blank texts are
    skipped so no blank row is ever fabricated.
    """
    names: list[str] = []
    for claim in getattr(grounded_answer, "claims", []):
        text = (claim.text or "").strip()
        if text and text not in names:
            names.append(text)
    return names


def _issuer_name(drhp_id: str) -> str | None:
    """Look up the IPO issuer's display name from the catalogue (for its own row)."""
    from data.catalogue_loader import load_catalogue

    for ipo in load_catalogue():
        if ipo.drhp_id == drhp_id:
            return ipo.issuer
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command(name="precompute-one")
def precompute_one(
    drhp_id: str = typer.Argument(
        ..., help="The drhp_id to pre-compute, e.g. swiggy_2024_11"
    ),
) -> None:
    """Pre-compute the peer record for one IPO."""
    console.rule(f"[bold blue]Pre-computing peers for {drhp_id}[/bold blue]")
    record = precompute_peers(drhp_id)
    console.print(
        f"  peer_set={type(record.peer_set).__name__} "
        f"companies={len(record.companies)}"
    )
    console.print(f"  Written to data/peers/{drhp_id}.json")


@app.command(name="precompute-all")
def precompute_all() -> None:
    """Loop over data/catalogue.json and pre-compute every IPO's peer record.

    Per-IPO failure isolation (mirrors pipelines.redflag.precompute_all's P14
    posture) — one IPO's exception is logged and skipped; it does not abort the
    batch.
    """
    from data.catalogue_loader import load_catalogue

    catalogue = load_catalogue()
    console.rule(
        f"[bold blue]Pre-computing peers for {len(catalogue)} IPOs[/bold blue]"
    )

    results: list[tuple[str, str]] = []
    for ipo in catalogue:
        console.print(f"\n[bold]{ipo.drhp_id}[/bold] ({ipo.issuer})")
        try:
            record = precompute_peers(ipo.drhp_id)
            console.print(
                f"  peer_set={type(record.peer_set).__name__} "
                f"companies={len(record.companies)}"
            )
            results.append((ipo.drhp_id, "ok"))
        except Exception as exc:  # noqa: BLE001 — per-IPO failure isolation (P14)
            console.print(f"  [red]FAILED: {exc}[/red]")
            results.append((ipo.drhp_id, "failed"))

    console.print("\n[bold]Summary[/bold]")
    for drhp_id, status in results:
        console.print(f"  {drhp_id}: {status}")


if __name__ == "__main__":
    app()
