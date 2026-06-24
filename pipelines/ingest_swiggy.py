"""
pipelines/ingest_swiggy.py — Thin Swiggy-bound shim over pipelines/ingest.py.

Wave 2 generalized the pipeline into pipelines/ingest.py::ingest_drhp(drhp_id,
pdf_path, ...). This module is kept ONLY so that:
  - Phase 1 tests (tests/unit/test_chunker.py, tests/unit/test_parser.py,
    tests/integration/test_qdrant_ingest.py) that import names directly from
    pipelines.ingest_swiggy keep working unchanged.
  - The original `python -m pipelines.ingest_swiggy all` CLI entry point still
    runs the Swiggy ingest end-to-end, now delegating to the generalized
    pipeline under the hood.

All actual logic lives in pipelines/ingest.py. Do NOT add new logic here.
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

# Re-export everything Phase 1 tests import directly from this module.
from pipelines.ingest import (  # noqa: F401
    CHUNK_ABSOLUTE_MIN,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    DEFAULT_FRONT_MATTER_PAGES,
    IngestReport,
    Section,
    _count_tokens,
    _infer_printed_label,
    _split_into_sentences,
    chunk_docling_json,
    chunk_sections as _chunk_sections_generalized,
    embed_chunks,
    extract_sections_from_docling as _extract_sections_from_docling_generalized,
    ingest_drhp,
    load_or_parse_drhp,
    parse_drhp,
    parse_quality_gate,
)

app = typer.Typer(help="DRHPLens offline DRHP ingestion pipeline (Swiggy shim).")
console = Console()

# ---------------------------------------------------------------------------
# Swiggy-specific constants (Phase 1 values, preserved for back-compat)
# ---------------------------------------------------------------------------

DRHP_ID = "swiggy_2024_11"
PDF_PATH = Path(__file__).parent.parent / "data" / "swiggy_drhp" / "swiggy_prospectus_2024_11.pdf"
JSON_CACHE_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "swiggy_drhp"
    / "swiggy_prospectus_2024_11.docling.json"
)

# Swiggy-tuned historical default (kept for back-compat with anything reading
# this constant directly; pipelines/ingest.py treats this as a parameter now).
ROMAN_NUMERAL_THRESHOLD_PAGE = DEFAULT_FRONT_MATTER_PAGES


# ---------------------------------------------------------------------------
# Back-compat wrappers — same call signature Phase 1 tests/code expect,
# defaulting to the Swiggy constants instead of requiring drhp_id explicitly.
# ---------------------------------------------------------------------------


def extract_sections_from_docling(doc_dict: dict) -> list[Section]:
    """Swiggy-bound wrapper: defaults front_matter_pages to the Swiggy constant."""
    return _extract_sections_from_docling_generalized(
        doc_dict, front_matter_pages=ROMAN_NUMERAL_THRESHOLD_PAGE
    )


def chunk_sections(
    sections: list[Section],
    drhp_id: str = DRHP_ID,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list:
    """Swiggy-bound wrapper: defaults drhp_id to the Swiggy constant (Phase 1 back-compat)."""
    return _chunk_sections_generalized(
        sections, drhp_id=drhp_id, max_tokens=max_tokens, overlap_tokens=overlap_tokens
    )


# ---------------------------------------------------------------------------
# CLI Commands — bound to the Swiggy constants, delegating to ingest_drhp
# ---------------------------------------------------------------------------


@app.command()
def parse(
    pdf_path: Path = typer.Option(PDF_PATH, "--pdf", help="Path to the DRHP PDF"),
    force: bool = typer.Option(False, "--force", help="Re-parse even if cache exists"),
) -> None:
    """Parse the DRHP PDF with Docling -> write JSON cache."""
    if JSON_CACHE_PATH.exists() and not force:
        console.print(f"Cache already exists: {JSON_CACHE_PATH}")
        console.print("Use --force to re-parse.")
        return
    doc = parse_drhp(pdf_path, JSON_CACHE_PATH)
    sections = extract_sections_from_docling(doc)
    console.print(f"  Extracted [bold]{len(sections)}[/bold] sections")


@app.command()
def chunk(
    max_tokens: int = typer.Option(CHUNK_MAX_TOKENS, "--max-tokens"),
    overlap: int = typer.Option(CHUNK_OVERLAP_TOKENS, "--overlap"),
) -> None:
    """Chunk the cached Docling JSON and print stats."""
    import json

    if not JSON_CACHE_PATH.exists():
        console.print(f"[red]Cache not found:[/red] {JSON_CACHE_PATH}")
        console.print("Run `parse` first.")
        raise typer.Exit(1)

    with open(JSON_CACHE_PATH) as f:
        doc = json.load(f)

    sections = extract_sections_from_docling(doc)
    chunks = chunk_sections(sections, max_tokens=max_tokens, overlap_tokens=overlap)
    total_tokens = sum(_count_tokens(c.chunk_text) for c in chunks)
    console.print(f"  [bold]{len(chunks)}[/bold] chunks | {total_tokens:,} total tokens")

    if chunks:
        sizes = [_count_tokens(c.chunk_text) for c in chunks]
        console.print(
            f"  Token range: min={min(sizes)} max={max(sizes)} "
            f"avg={sum(sizes)//len(sizes)}"
        )


@app.command()
def embed(
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Embed chunks and print progress (does not upsert)."""
    import json

    if not JSON_CACHE_PATH.exists():
        console.print(f"[red]Cache not found:[/red] {JSON_CACHE_PATH}")
        raise typer.Exit(1)

    with open(JSON_CACHE_PATH) as f:
        doc = json.load(f)

    sections = extract_sections_from_docling(doc)
    chunks = chunk_sections(sections)
    embed_chunks(chunks)


@app.command()
def upsert(
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip upsert; print stats only"),
) -> None:
    """Upsert chunks to Qdrant (loads cached JSON + re-embeds)."""
    report = ingest_drhp(
        drhp_id=DRHP_ID,
        pdf_path=PDF_PATH,
        json_cache_path=JSON_CACHE_PATH,
        front_matter_pages=ROMAN_NUMERAL_THRESHOLD_PAGE,
        dry_run=dry_run,
    )
    if dry_run:
        console.print(f"  chunks={report.chunk_count} (dry-run; no upsert performed)")
    else:
        console.print(f"  [bold green]Upserted {report.chunk_count} chunks to Qdrant[/bold green]")


@app.command()
def all(
    pdf_path: Path = typer.Option(PDF_PATH, "--pdf"),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Skip the Qdrant upsert; print chunk count + sample chunks only",
    ),
    max_tokens: int = typer.Option(CHUNK_MAX_TOKENS, "--max-tokens"),
    overlap: int = typer.Option(CHUNK_OVERLAP_TOKENS, "--overlap"),
) -> None:
    """Run the full pipeline: parse -> chunk -> embed -> upsert (Swiggy-bound).

    Delegates to pipelines.ingest.ingest_drhp under the hood.
    """
    console.rule("[bold blue]DRHPLens DRHP Ingestion Pipeline (Swiggy)[/bold blue]")
    report = ingest_drhp(
        drhp_id=DRHP_ID,
        pdf_path=pdf_path,
        json_cache_path=JSON_CACHE_PATH,
        front_matter_pages=ROMAN_NUMERAL_THRESHOLD_PAGE,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        dry_run=dry_run,
    )
    console.print(
        f"  chunks={report.chunk_count} page_coverage={report.page_coverage} "
        f"quality={report.extraction_quality} dry_run={report.dry_run}"
    )
    console.rule("[bold blue]Pipeline complete[/bold blue]")


if __name__ == "__main__":
    app()
