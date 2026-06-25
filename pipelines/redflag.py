"""
pipelines/redflag.py — Red-flag pre-compute pipeline (03-03-PLAN.md).

An EXACT mirror of pipelines/snapshot.py: each of the 7 canonical red-flag
fields is computed by running the EXISTING compiled agent (agent.graph.GRAPH)
once per canned query in pipelines.redflag_queries.REDFLAG_QUERIES. NO new LLM
path, NO "red-flag mode" in the graph — a red-flag field IS a serialized
GroundedAnswer (with a deterministic confidence tier, D3-01) OR an honest
RefusalResponse ("Not disclosed in DRHP", D3-03), so Wave 4's UI reuses the
Phase 1 citation chip renderer for free.

Three honesty invariants beyond snapshot.py (EXTRACT-01/02):
  - A field whose answer is generated but whose NUMBER fails cite_check grounding
    (state["grounded_answer"] present yet state["all_claims_grounded"] False) is
    stored as a BLOCKED RefusalResponse carrying the L3-9 blocked-copy
    explanation — never an unsourced number in the cache (T-03-03).
  - A not-disclosed field (no grounded answer) is stored as a RefusalResponse
    with NO confidence tier (D3-03).
  - The ofs_vs_fresh field REUSES the snapshot's already-computed ofs_fresh
    (pipelines.snapshot.load_snapshot) rather than re-extracting it.

Path safety (T-03-01): precompute_redflags / load_redflag gate <drhp_id> through
the Phase 2 is_known_drhp_id allow-list (data/catalogue_loader.py) BEFORE forming
any data/redflag/<id>.json path — a non-allow-listed id raises, no path is built.

CODE-NOW-DEFER (03-03-PLAN.md objective): fully unit-tested by monkeypatching
agent.graph.GRAPH.invoke — no live Gemini/Groq call and no live Qdrant query
happen under `pytest tests/unit`. The real 7x8 pre-compute run against live infra
is deferred to the data ingest runbook.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console

from agent.redflag_schema import RedFlagField, RedFlagRecord
from compliance.scrubber import scrub
from data.catalogue_loader import is_known_drhp_id
from pipelines.confidence import classify_confidence
from pipelines.redflag_queries import REDFLAG_QUERIES

app = typer.Typer(help="DRHPLens red-flag pre-compute pipeline.")
console = Console()

REDFLAG_DIR: Path = Path(__file__).parent.parent / "data" / "redflag"

# L3-9 blocked-number copy (UI-SPEC Copywriting Contract; the constant itself
# lives in ui/copy.py in Plan 06, this is the verbatim string the cache stores so
# the renderer never has to fabricate it). A field whose number could not be
# grounded to a cited DRHP page is stored as a refusal carrying this explanation.
_NUMERIC_GATE_BLOCKED_COPY = (
    "Could not ground this number to a cited DRHP page, so it is not shown."
)

# Per-field default refusal reason when GRAPH.invoke produces neither a
# grounded_answer nor a refusal (defensive fallback — should not happen given the
# graph's routing, but the cache must never be left without an honest value).
_DEFAULT_REFUSAL_REASON = "low_retrieval_score"


# ---------------------------------------------------------------------------
# load_redflag
# ---------------------------------------------------------------------------


def load_redflag(drhp_id: str) -> RedFlagRecord:
    """Read data/redflag/<drhp_id>.json into a RedFlagRecord.

    Args:
        drhp_id: e.g. "swiggy_2024_11". Must be a known catalogue id (T-03-01).

    Returns:
        The validated RedFlagRecord.

    Raises:
        ValueError: if drhp_id is not in the catalogue allow-list.
        FileNotFoundError: if the red-flag cache file does not exist.
    """
    path = _redflag_path(drhp_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No red-flag cache found for drhp_id={drhp_id!r} at {path}"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return RedFlagRecord.from_dict(raw)


def _redflag_path(drhp_id: str) -> Path:
    """Form the cache path, gating drhp_id through the allow-list (T-03-01).

    Raises:
        ValueError: if drhp_id is not a known catalogue entry — the path is
        never formed for an untrusted id (path-traversal mitigation).
    """
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to form a cache path "
            f"(catalogue allow-list, T-03-01)."
        )
    return REDFLAG_DIR / f"{drhp_id}.json"


def _make_refusal_response(reason: str, explanation: str):
    """Build a RefusalResponse for the honest "not disclosed"/"blocked" path."""
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
# precompute_redflags — the 7x-per-IPO canned-query agent invocation loop
# ---------------------------------------------------------------------------


def precompute_redflags(drhp_id: str, *, write: bool = True) -> RedFlagRecord:
    """Run the existing agent 7x per drhp_id with the canned REDFLAG_QUERIES.

    For each field in REDFLAG_QUERIES:
      - ofs_vs_fresh: reuse the snapshot's cached ofs_fresh (do not re-extract);
        fall through to the canned-query path only if no snapshot exists.
      - Otherwise call agent.graph.GRAPH.invoke({"question": query,
        "drhp_id": drhp_id, "regenerate_attempts": 0}) and classify the result:
        * grounded answer that passed cite_check (all_claims_grounded True) and
          the scrubber -> store a GroundedAnswer with a confidence tier (D3-01).
        * grounded answer whose number FAILED cite_check (all_claims_grounded
          False) -> store a BLOCKED RefusalResponse (L3-9), never an unsourced
          number (T-03-03).
        * no grounded answer (refusal) -> store the honest not-disclosed
          RefusalResponse with NO confidence (D3-03).

    Args:
        drhp_id: e.g. "swiggy_2024_11". Must be allow-listed (T-03-01).
        write: if True (default), write to data/redflag/<drhp_id>.json. Tests
            typically pass write=False.

    Returns:
        The computed RedFlagRecord.

    Raises:
        ValueError: if drhp_id is not a known catalogue entry (raised BEFORE any
        graph call or path formation — path-traversal mitigation T-03-01).
    """
    # T-03-01: gate the id up front, before any graph call or path is formed.
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to pre-compute red-flags "
            f"for a non-allow-listed id (T-03-01)."
        )

    from agent.graph import GRAPH

    fields: dict = {}
    for field_key, query in REDFLAG_QUERIES.items():
        # Field #2: reuse the snapshot's already-computed ofs_fresh rather than
        # re-running the graph (RESEARCH Pattern 1). Falls through to the canned
        # query only when no snapshot cache exists for this IPO.
        if field_key == "ofs_vs_fresh":
            reused = _ofs_vs_fresh_from_snapshot(drhp_id)
            if reused is not None:
                fields[field_key] = reused
                continue

        state = GRAPH.invoke(
            {"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0}
        )
        grounded_answer = state.get("grounded_answer")
        refusal = state.get("refusal")
        all_grounded = state.get("all_claims_grounded")

        if grounded_answer is not None and all_grounded:
            if _scrub_passes(grounded_answer):
                tier, score = classify_confidence(grounded_answer)
                fields[field_key] = RedFlagField(
                    value=grounded_answer,
                    confidence_tier=tier,
                    confidence_score=score,
                )
            else:
                # Defense in depth (T-03-06): never commit unscrubbed prose, even
                # though the graph's own scrub node should have caught it. Store
                # an honest refusal instead of dropping the field silently.
                fields[field_key] = RedFlagField(
                    value=_make_refusal_response(
                        "banned_token",
                        "A compliance check flagged this answer's wording before "
                        "it could be cached; this field is being treated as not "
                        "available rather than risk publishing non-compliant copy.",
                    )
                )
        elif grounded_answer is not None:
            # An answer was generated but its number failed cite_check grounding
            # (all_claims_grounded False). Block it — store the L3-9 blocked-copy
            # refusal, never an unsourced number (T-03-03).
            fields[field_key] = RedFlagField(
                value=_make_refusal_response(
                    "unsupported_claim",
                    _NUMERIC_GATE_BLOCKED_COPY,
                )
            )
        elif refusal is not None:
            # Honest "not disclosed" path — no confidence on absence (D3-03).
            fields[field_key] = RedFlagField(value=refusal)
        else:
            # Defensive fallback — should not happen given the graph's routing,
            # but the cache must never be left without an honest value.
            fields[field_key] = RedFlagField(
                value=_make_refusal_response(
                    _DEFAULT_REFUSAL_REASON,
                    "This DRHP does not appear to disclose this field.",
                )
            )

    # ranked_risks: derive from the grounded risk-bearing fields via Task 2's
    # in-corpus IDF ranker (offline, stdlib + rapidfuzz).
    ranked_risks = _rank_risks_for_record(fields, drhp_id)

    record = RedFlagRecord(
        drhp_id=drhp_id,
        computed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        fields=fields,
        ranked_risks=ranked_risks,
    )

    if write:
        path = _redflag_path(drhp_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.to_json(), encoding="utf-8")

    return record


def _ofs_vs_fresh_from_snapshot(drhp_id: str) -> RedFlagField | None:
    """Build the ofs_vs_fresh RedFlagField from the snapshot's cached ofs_fresh.

    Reuse, do not re-extract (RESEARCH Pattern 1). Returns None if no snapshot
    cache exists OR the snapshot did not determine an OFS split — the caller then
    falls through to the canned-query path.
    """
    from pipelines.snapshot import load_snapshot

    try:
        snap = load_snapshot(drhp_id)
    except FileNotFoundError:
        return None

    ofs_fresh = snap.ofs_fresh
    if not ofs_fresh:
        return None

    # Surface the cached split via the snapshot's use_of_proceeds GroundedAnswer,
    # which carries the claim_id citations behind the split. This is a REUSE of an
    # already-vetted cached artifact (the snapshot pipeline ran its own scrubber +
    # cite-check at its precompute time) — we deliberately do NOT re-scrub or
    # re-extract here, that is the whole point of reuse (RESEARCH Pattern 1). If
    # the snapshot did not produce a grounded use_of_proceeds, fall through.
    from agent.schemas import GroundedAnswer

    uop = snap.fields.get("use_of_proceeds")
    if isinstance(uop, GroundedAnswer):
        tier, score = classify_confidence(uop)
        return RedFlagField(
            value=uop, confidence_tier=tier, confidence_score=score
        )
    return None


def _rank_risks_for_record(fields: dict, drhp_id: str) -> list:
    """Rank this IPO's risk claims via the in-corpus IDF ranker (Task 2).

    Pulls the claim texts from any grounded risk-bearing field, scores them
    against the catalogue corpus, and returns the ordered RankedRisk list. Done
    defensively (per-IPO isolation): a ranking failure must not sink the whole
    record — an empty list is an honest "no ranked risks" rather than a crash.
    """
    from agent.schemas import GroundedAnswer

    risk_claims: list[tuple[str, str]] = []
    for field in fields.values():
        value = field.value
        if isinstance(value, GroundedAnswer):
            for claim in value.claims:
                risk_claims.append((claim.claim_id, claim.text))

    if not risk_claims:
        return []

    try:
        from pipelines.risk_idf import rank_risks

        return rank_risks(risk_claims)
    except Exception:  # noqa: BLE001 — ranking is best-effort, never fatal
        return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command(name="precompute-one")
def precompute_one(
    drhp_id: str = typer.Argument(
        ..., help="The drhp_id to pre-compute, e.g. swiggy_2024_11"
    ),
) -> None:
    """Pre-compute the 7-field red-flag record for one IPO."""
    console.rule(f"[bold blue]Pre-computing red-flags for {drhp_id}[/bold blue]")
    record = precompute_redflags(drhp_id)
    console.print(
        f"  fields={list(record.fields.keys())} "
        f"ranked_risks={len(record.ranked_risks)}"
    )
    console.print(f"  Written to data/redflag/{drhp_id}.json")


@app.command(name="precompute-all")
def precompute_all() -> None:
    """Loop over data/catalogue.json and pre-compute every IPO's red-flag record.

    Per-IPO failure isolation (mirrors pipelines.snapshot.precompute_all's P14
    posture) — one IPO's exception is logged and skipped; it does not abort the
    batch.
    """
    from data.catalogue_loader import load_catalogue

    catalogue = load_catalogue()
    console.rule(
        f"[bold blue]Pre-computing red-flags for {len(catalogue)} IPOs[/bold blue]"
    )

    results: list[tuple[str, str]] = []
    for ipo in catalogue:
        console.print(f"\n[bold]{ipo.drhp_id}[/bold] ({ipo.issuer})")
        try:
            record = precompute_redflags(ipo.drhp_id)
            console.print(
                f"  fields={list(record.fields.keys())} "
                f"ranked_risks={len(record.ranked_risks)}"
            )
            results.append((ipo.drhp_id, "ok"))
        except Exception as exc:  # noqa: BLE001 — per-IPO failure isolation
            console.print(f"  [red]FAILED: {exc}[/red]")
            results.append((ipo.drhp_id, "failed"))

    console.print("\n[bold]Summary[/bold]")
    for drhp_id, status in results:
        console.print(f"  {drhp_id}: {status}")


if __name__ == "__main__":
    app()
