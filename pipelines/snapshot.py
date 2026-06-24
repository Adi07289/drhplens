"""
pipelines/snapshot.py — Snapshot pre-compute pipeline (02-04-PLAN.md).

Per 02-RESEARCH.md §Pattern 3 / D2-04: each of the 6 snapshot fields is
computed by running the EXISTING compiled agent (agent.graph.GRAPH) once per
canned query in pipelines.snapshot_queries.SNAPSHOT_QUERIES. NO new LLM path,
NO "snapshot mode" in the graph — a snapshot field IS a serialized
GroundedAnswer (or RefusalResponse when the DRHP is silent), so Wave 4's UI
reuses the Phase 1 citation chip renderer for free.

CODE-NOW-DEFER (02-04-PLAN.md objective): this module is fully unit-tested by
monkeypatching agent.graph.GRAPH.invoke — no live Gemini/Groq call and no live
Qdrant query happen when running `pytest tests/unit`. The real 6x8 pre-compute
run against live infra is deferred to the data/INGEST_ALL_LATER.md runbook.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

from agent.snapshot_schema import SnapshotRecord
from compliance.scrubber import scrub
from pipelines.snapshot_queries import SNAPSHOT_QUERIES

app = typer.Typer(help="DRHPLens snapshot pre-compute pipeline.")
console = Console()

SNAPSHOTS_DIR: Path = Path(__file__).parent.parent / "data" / "snapshots"

# Per-field default refusal reason when GRAPH.invoke produces neither a
# grounded_answer nor a refusal (defensive fallback — should not happen in
# practice since refuse_with_reformulation always populates state["refusal"]
# on every non-emit path, but the snapshot cache must never be left without
# an honest value for a field).
_DEFAULT_REFUSAL_REASON = "unsupported_claim"


# ---------------------------------------------------------------------------
# load_snapshot
# ---------------------------------------------------------------------------


def load_snapshot(drhp_id: str) -> SnapshotRecord:
    """Read data/snapshots/<drhp_id>.json into a SnapshotRecord.

    Args:
        drhp_id: e.g. "swiggy_2024_11"

    Returns:
        The validated SnapshotRecord.

    Raises:
        FileNotFoundError: if the snapshot cache file does not exist.
    """
    path = SNAPSHOTS_DIR / f"{drhp_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No snapshot cache found for drhp_id={drhp_id!r} at {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return SnapshotRecord.from_dict(raw)


def _snapshot_path(drhp_id: str) -> Path:
    return SNAPSHOTS_DIR / f"{drhp_id}.json"


def _make_refusal_response(reason: str, explanation: str):
    """Build a RefusalResponse for the honest "not disclosed" path."""
    from agent.schemas import RefusalResponse

    return RefusalResponse(
        reason=reason,  # type: ignore[arg-type]
        explanation=explanation,
        reformulation_suggestions=[],
    )


def _scrub_passes(grounded_answer) -> bool:
    """Run the banned-token scrubber over a GroundedAnswer's answer_prose."""
    result = scrub(grounded_answer.answer_prose)
    return result.passed


# ---------------------------------------------------------------------------
# precompute — the 6x-per-IPO canned-query agent invocation loop
# ---------------------------------------------------------------------------


def precompute(drhp_id: str, *, write: bool = True) -> SnapshotRecord:
    """Run the existing agent 6x per drhp_id with the canned SNAPSHOT_QUERIES.

    For each field in SNAPSHOT_QUERIES:
      - Call agent.graph.GRAPH.invoke({"question": query, "drhp_id": drhp_id,
        "regenerate_attempts": 0}).
      - If state["grounded_answer"] is set, scrub its answer_prose. If the
        scrub passes, store the GroundedAnswer. If the scrub fails (a banned
        token somehow survived the graph's own scrub node — defense in depth,
        T-02-03), store a RefusalResponse(reason="banned_token") instead of
        ever committing unscrubbed prose.
      - Otherwise (state["refusal"] set, or neither populated), store a
        RefusalResponse — the honest "not disclosed" path (critical for
        SNAP-07 pledging).

    Computes ofs_fresh from the use_of_proceeds field once all 6 fields are
    resolved (Task 2 / SNAP-06).

    Args:
        drhp_id: e.g. "hyundai_2024_10"
        write: if True (default), write the record to
            data/snapshots/<drhp_id>.json. Tests typically pass write=False.

    Returns:
        The computed SnapshotRecord.
    """
    from agent.graph import GRAPH

    fields: dict = {}
    for field_key, query in SNAPSHOT_QUERIES.items():
        state = GRAPH.invoke(
            {"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0}
        )
        grounded_answer = state.get("grounded_answer")
        refusal = state.get("refusal")

        if grounded_answer is not None:
            if _scrub_passes(grounded_answer):
                fields[field_key] = grounded_answer
            else:
                # Defense in depth (T-02-03): never commit unscrubbed prose,
                # even though the graph's own scrub node should have already
                # caught this. Store an honest refusal instead of dropping
                # the field silently.
                fields[field_key] = _make_refusal_response(
                    "banned_token",
                    "A compliance check flagged this answer's wording before it "
                    "could be cached; this field is being treated as not "
                    "available rather than risk publishing non-compliant copy.",
                )
        elif refusal is not None:
            fields[field_key] = refusal
        else:
            # Defensive fallback — should not happen given the graph's routing,
            # but the snapshot cache must never be left without an honest value.
            fields[field_key] = _make_refusal_response(
                _DEFAULT_REFUSAL_REASON,
                "This DRHP does not appear to disclose this field.",
            )

    ofs_fresh = compute_ofs_fresh(fields.get("use_of_proceeds"))

    record = SnapshotRecord(
        drhp_id=drhp_id,
        computed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        fields=fields,
        ofs_fresh=ofs_fresh,
    )

    if write:
        path = _snapshot_path(drhp_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.to_json(), encoding="utf-8")

    return record


# ---------------------------------------------------------------------------
# compute_ofs_fresh — SNAP-06 neutral OFS-vs-fresh split
# ---------------------------------------------------------------------------


def compute_ofs_fresh(field) -> dict | None:
    """Derive the OFS-vs-fresh % split from the use_of_proceeds field.

    Per D2-06 / UI-SPEC §Split-Bar Contract, the returned dict carries ONLY
    `ofs_pct` + `fresh_pct` (+ an optional `source_claim_id`) — NEVER a
    "good"/"bad"/"warning"/color/verdict field. SNAP-06 neutrality is a hard
    invariant: the product describes the proportion, it never judges it.

    Args:
        field: the use_of_proceeds GroundedAnswer, a RefusalResponse (DRHP
            silent on the split), or None.

    Returns:
        {"ofs_pct": float, "fresh_pct": float, "source_claim_id": str | None}
        summing to 100 (rounded to 1 decimal), or None if the field is a
        RefusalResponse / None / the split could not be determined from the
        claims (honest "not disclosed" — the UI renders the not-disclosed
        note instead of a bar).
    """
    from agent.schemas import GroundedAnswer

    if field is None or not isinstance(field, GroundedAnswer):
        return None

    import re

    ofs_pct: float | None = None
    fresh_pct: float | None = None
    source_claim_id: str | None = None

    # Look for an explicit percentage pair across the answer prose + claim text.
    text_blobs: list[tuple[str | None, str]] = [(None, field.answer_prose)]
    text_blobs.extend((claim.claim_id, claim.text) for claim in field.claims)
    text_blobs.extend((claim.claim_id, claim.verbatim_span) for claim in field.claims)

    ofs_pattern = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%[^.]*?\bOFS\b|\bOFS\b[^.]*?(\d{1,3}(?:\.\d+)?)\s*%", re.IGNORECASE)
    fresh_pattern = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%[^.]*?\bfresh\b|\bfresh\b[^.]*?(\d{1,3}(?:\.\d+)?)\s*%", re.IGNORECASE)

    for claim_id, blob in text_blobs:
        if ofs_pct is None:
            m = ofs_pattern.search(blob)
            if m:
                ofs_pct = float(m.group(1) or m.group(2))
                source_claim_id = source_claim_id or claim_id
        if fresh_pct is None:
            m = fresh_pattern.search(blob)
            if m:
                fresh_pct = float(m.group(1) or m.group(2))
                source_claim_id = source_claim_id or claim_id

    # Honest single-sided disclosures (D2-06 / RESEARCH §Section Conventions):
    # "100% OFS" or "entirely an offer for sale" -> fresh is 0, and vice versa.
    if ofs_pct is None and fresh_pct is not None:
        ofs_pct = round(100.0 - fresh_pct, 1)
    elif fresh_pct is None and ofs_pct is not None:
        fresh_pct = round(100.0 - ofs_pct, 1)

    if ofs_pct is None and fresh_pct is None:
        # Could not determine the split from disclosed text -> not disclosed.
        return None

    # Normalize rounding so the pair always sums to exactly 100.
    ofs_pct = round(ofs_pct, 1)
    fresh_pct = round(100.0 - ofs_pct, 1)

    return {
        "ofs_pct": ofs_pct,
        "fresh_pct": fresh_pct,
        "source_claim_id": source_claim_id,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command()
def precompute_one(
    drhp_id: str = typer.Argument(..., help="The drhp_id to pre-compute, e.g. swiggy_2024_11"),
) -> None:
    """Pre-compute the 6-field snapshot for one IPO: python -m pipelines.snapshot precompute-one <drhp_id>."""
    console.rule(f"[bold blue]Pre-computing snapshot for {drhp_id}[/bold blue]")
    record = precompute(drhp_id)
    console.print(f"  fields={list(record.fields.keys())} ofs_fresh={record.ofs_fresh}")
    console.print(f"  Written to data/snapshots/{drhp_id}.json")


@app.command(name="precompute-all")
def precompute_all() -> None:
    """Loop over data/catalogue.json and pre-compute every IPO's snapshot.

    Per-IPO failure isolation (mirrors pipelines.ingest.ingest_all's P14
    posture) — one IPO's exception is logged and skipped; it does not abort
    the batch.
    """
    from data.catalogue_loader import load_catalogue

    catalogue = load_catalogue()
    console.rule(f"[bold blue]Pre-computing snapshots for {len(catalogue)} IPOs[/bold blue]")

    results: list[tuple[str, str]] = []
    for ipo in catalogue:
        console.print(f"\n[bold]{ipo.drhp_id}[/bold] ({ipo.issuer})")
        try:
            record = precompute(ipo.drhp_id)
            console.print(f"  fields={list(record.fields.keys())} ofs_fresh={record.ofs_fresh}")
            results.append((ipo.drhp_id, "ok"))
        except Exception as exc:  # noqa: BLE001 — per-IPO failure isolation
            console.print(f"  [red]FAILED: {exc}[/red]")
            results.append((ipo.drhp_id, "failed"))

    console.print("\n[bold]Summary[/bold]")
    for drhp_id, status in results:
        console.print(f"  {drhp_id}: {status}")


if __name__ == "__main__":
    app()
