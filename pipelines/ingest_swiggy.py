"""
pipelines/ingest_swiggy.py — Offline DRHP ingestion pipeline (Typer CLI).

Storage-bus invariant (SKELETON §A):
- This pipeline ONLY writes to Qdrant. The runtime agent ONLY reads.
- They never share Python state and never invoke each other.

Pipeline steps:
  1. parse   — Docling 2.95 PDF → structured JSON (sections, tables, page anchors)
  2. chunk   — Section-aware chunker (512-1024 tokens, 100-200 overlap)
  3. embed   — bge-m3 batch encode (CPU; batch_size=4)
  4. upsert  — Qdrant upsert (collection: drhp_chunks)

Usage:
    python -m pipelines.ingest_swiggy parse   # parse only → writes JSON cache
    python -m pipelines.ingest_swiggy chunk   # chunk from cached JSON
    python -m pipelines.ingest_swiggy embed   # embed only (prints progress)
    python -m pipelines.ingest_swiggy upsert  # upsert to Qdrant
    python -m pipelines.ingest_swiggy all     # full pipeline end-to-end
    python -m pipelines.ingest_swiggy all --dry-run  # skip upsert, print stats

PITFALL mitigations:
  PITFALL 1: This pipeline NEVER runs in the app process; it's offline build-time.
  PITFALL 4: Both page_start (PDF index, 0-based) AND printed_page_label stored.
  PITFALL 5: span_offsets=(0, len(chunk_text)) stored; Wave 3 narrows per-claim.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import tiktoken
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from storage.vector import ChunkPayload

app = typer.Typer(help="DRHPLens offline DRHP ingestion pipeline.")
console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DRHP_ID = "swiggy_2024_11"
PDF_PATH = Path(__file__).parent.parent / "data" / "swiggy_drhp" / "swiggy_prospectus_2024_11.pdf"
JSON_CACHE_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "swiggy_drhp"
    / "swiggy_prospectus_2024_11.docling.json"
)

CHUNK_MAX_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 100
CHUNK_ABSOLUTE_MIN = 50   # Discard chunks shorter than this (table headers etc.)

# Approximation: PDF front-matter pages with Roman numerals are typically
# the first ~20 pages for a standard Indian DRHP.
ROMAN_NUMERAL_THRESHOLD_PAGE = 20

TOKENIZER = tiktoken.encoding_for_model("gpt-4o")


# ---------------------------------------------------------------------------
# Section dataclass
# ---------------------------------------------------------------------------


class Section:
    """Represents a single section extracted from a DRHP document."""

    def __init__(
        self,
        name: str,
        level: int,
        page_indices: list[int],
        printed_page_labels: list[str],
        text: str,
    ) -> None:
        self.name = name
        self.level = level
        self.page_indices = page_indices  # 0-based PDF page indices
        self.printed_page_labels = printed_page_labels
        self.text = text

    def __repr__(self) -> str:
        return (
            f"Section({self.name!r}, level={self.level}, "
            f"pages={self.page_indices}, text_len={len(self.text)})"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_printed_label(page_idx: int, docling_page_meta: dict | None) -> str:
    """Infer the printed page label from Docling metadata or page index.

    PITFALL 4 mitigation: Indian DRHPs have Roman-numeral front matter (i, ii, iii...)
    before switching to Arabic pagination. We store BOTH the PDF index (0-based)
    AND the visible printed label.

    Args:
        page_idx: 0-based PDF page index
        docling_page_meta: Docling page metadata dict (may contain label)
    """
    # Try to get from Docling metadata first
    if docling_page_meta:
        # Docling may expose the page label under various keys
        for key in ("page_no", "printed_page_no", "label", "page_number"):
            val = docling_page_meta.get(key)
            if val is not None:
                return str(val)

    # Fallback: infer Roman numerals for early pages in typical DRHP layout
    if page_idx < ROMAN_NUMERAL_THRESHOLD_PAGE:
        roman_labels = [
            "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
            "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
        ]
        return roman_labels[page_idx] if page_idx < len(roman_labels) else str(page_idx + 1)

    # Arabic pagination for body pages
    # Typical offset: body page 1 = PDF page ~20 (after 20 front-matter pages)
    body_page = page_idx - ROMAN_NUMERAL_THRESHOLD_PAGE + 1
    return str(body_page)


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken gpt-4o encoding."""
    return len(TOKENIZER.encode(text))


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences at natural boundaries."""
    # Split on sentence-ending punctuation followed by whitespace/newline
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    # Also split on double newlines (paragraph breaks)
    result = []
    for sent in sentences:
        parts = re.split(r"\n{2,}", sent)
        result.extend(p.strip() for p in parts if p.strip())
    return result if result else [text.strip()] if text.strip() else []


# ---------------------------------------------------------------------------
# Step 1: Parse
# ---------------------------------------------------------------------------


def parse_drhp(pdf_path: Path) -> dict:
    """Parse the DRHP PDF using Docling 2.95 and return the document dict.

    This is an expensive step (5-15 min on CPU for a 300-500 page DRHP).
    Output is cached to JSON at JSON_CACHE_PATH; subsequent runs load from cache.

    Args:
        pdf_path: Path to the DRHP PDF file.

    Returns:
        Docling document dict (with 'pages', 'body', 'tables', etc.)
    """
    from docling.document_converter import DocumentConverter

    if not pdf_path.exists():
        raise FileNotFoundError(f"DRHP PDF not found at: {pdf_path}")

    console.print(f"[bold]Parsing DRHP PDF:[/bold] {pdf_path.name}")
    console.print("  This may take 5-15 minutes on CPU (Docling 2.95 with TableFormer).")

    start = time.time()

    converter = DocumentConverter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing with Docling...", total=None)
        result = converter.convert(str(pdf_path))
        progress.update(task, description="Parse complete.")

    elapsed = time.time() - start
    doc_dict = result.document.export_to_dict()

    console.print(f"  Parse complete in [bold]{elapsed:.1f}s[/bold]")

    # Save JSON cache
    JSON_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(doc_dict, f, ensure_ascii=False, indent=None)
    console.print(f"  JSON cache saved to: {JSON_CACHE_PATH}")

    return doc_dict


def load_or_parse_drhp(pdf_path: Path) -> dict:
    """Load cached Docling JSON or parse PDF if cache is missing."""
    if JSON_CACHE_PATH.exists():
        console.print(f"[bold]Loading cached Docling JSON:[/bold] {JSON_CACHE_PATH}")
        with open(JSON_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return parse_drhp(pdf_path)


# ---------------------------------------------------------------------------
# Step 2: Section extraction from Docling JSON
# ---------------------------------------------------------------------------


def extract_sections_from_docling(doc_dict: dict) -> list[Section]:
    """Walk the Docling document tree and extract a flat list of sections.

    Docling's export_to_dict() structure varies by version. We support:
    - doc_dict['body'] with nested items that have 'label', 'text', 'prov'
    - Fallback to doc_dict['texts'] list if 'body' is not present

    Per ARCHITECTURE Pattern 1: section boundaries are deeply semantic in DRHPs.
    We never produce cross-section chunks.

    Args:
        doc_dict: Docling document dict from export_to_dict()

    Returns:
        List of Section objects with name, level, page_indices, etc.
    """
    sections: list[Section] = []
    current_section: Section | None = None
    current_text_parts: list[str] = []

    def _flush_current() -> None:
        """Finalize the current section and append it to sections list."""
        nonlocal current_section, current_text_parts
        if current_section is not None and current_text_parts:
            current_section.text = "\n".join(current_text_parts).strip()
            if current_section.text:
                sections.append(current_section)
        current_section = None
        current_text_parts = []

    def _get_page_info(item: dict) -> tuple[list[int], list[str]]:
        """Extract page indices and printed labels from a Docling item."""
        page_indices: list[int] = []
        printed_labels: list[str] = []

        prov = item.get("prov", [])
        if isinstance(prov, list):
            for p in prov:
                if isinstance(p, dict):
                    # Docling uses 'page_no' (1-based) in prov
                    page_no = p.get("page_no")
                    if page_no is not None:
                        # Convert to 0-based index
                        idx = int(page_no) - 1
                        if idx not in page_indices:
                            page_indices.append(idx)
        elif isinstance(prov, dict):
            page_no = prov.get("page_no")
            if page_no is not None:
                page_indices.append(int(page_no) - 1)

        # Generate printed labels from page indices
        for idx in page_indices:
            printed_labels.append(_infer_printed_label(idx, None))

        return page_indices, printed_labels

    def _walk_items(items: list[dict], level: int = 0) -> None:
        """Recursively walk Docling document items."""
        nonlocal current_section, current_text_parts

        for item in items:
            if not isinstance(item, dict):
                continue

            label = item.get("label", "")
            text = item.get("text", "") or ""
            page_indices, printed_labels = _get_page_info(item)

            # Section headings create new sections
            is_heading = label in (
                "section_header", "title", "chapter_title",
                "heading1", "heading2", "heading3",
            ) or (label == "text" and len(text) < 150 and text.isupper() and len(text) > 5)

            if is_heading and text.strip():
                _flush_current()
                lvl = 1 if label in ("title", "chapter_title") else 2
                current_section = Section(
                    name=text.strip(),
                    level=lvl,
                    page_indices=page_indices if page_indices else [0],
                    printed_page_labels=printed_labels if printed_labels else ["i"],
                    text="",
                )
                current_text_parts = []
            elif text.strip():
                # Body text — accumulate into current section
                if current_section is None:
                    # Create a default section for front-matter text
                    current_section = Section(
                        name="Preamble",
                        level=1,
                        page_indices=page_indices if page_indices else [0],
                        printed_page_labels=printed_labels if printed_labels else ["i"],
                        text="",
                    )
                    current_text_parts = []

                current_text_parts.append(text.strip())

                # Update page range
                for idx in page_indices:
                    if idx not in current_section.page_indices:
                        current_section.page_indices.append(idx)

            # Handle tables (keep as flat text in the owning section)
            if label == "table" or item.get("$ref_hash"):
                table_text = item.get("text", "")
                if not table_text:
                    # Try to flatten table data from 'data' key
                    data = item.get("data", {})
                    if isinstance(data, dict):
                        grid = data.get("grid", [])
                        if grid:
                            rows = []
                            for row in grid:
                                if isinstance(row, list):
                                    cell_texts = [
                                        (c.get("text", "") if isinstance(c, dict) else str(c))
                                        for c in row
                                    ]
                                    rows.append(" | ".join(cell_texts))
                            table_text = "\n".join(rows)

                if table_text.strip():
                    if current_section is None:
                        current_section = Section(
                            name="Tables",
                            level=2,
                            page_indices=page_indices if page_indices else [0],
                            printed_page_labels=printed_labels if printed_labels else ["i"],
                            text="",
                        )
                        current_text_parts = []
                    current_text_parts.append(table_text.strip())

            # Recurse into children
            children = item.get("children", [])
            if children:
                _walk_items(children, level + 1)

    # Try the 'body' structure first
    body = doc_dict.get("body", {})
    if isinstance(body, dict):
        children = body.get("children", [])
        if children:
            _walk_items(children)

    # Fallback: try 'texts' key (alternative Docling export format)
    if not sections:
        texts = doc_dict.get("texts", [])
        if texts:
            _walk_items(texts)

    # Fallback: try 'pages' key for raw text extraction
    if not sections:
        pages = doc_dict.get("pages", [])
        for page_data in pages:
            if isinstance(page_data, dict):
                page_idx = page_data.get("page_no", 1) - 1
                printed = _infer_printed_label(page_idx, page_data)
                page_text = page_data.get("text", "") or ""
                if page_text.strip():
                    sections.append(
                        Section(
                            name=f"Page {page_idx + 1}",
                            level=2,
                            page_indices=[page_idx],
                            printed_page_labels=[printed],
                            text=page_text.strip(),
                        )
                    )

    _flush_current()

    # If we still have no sections, create one big section from the markdown export
    if not sections:
        md_text = doc_dict.get("md_text", "") or ""
        if not md_text:
            # Try export to markdown programmatically
            try:
                # Reconstruct text from all item texts
                all_texts = []
                for key in ("texts", "tables", "pictures"):
                    items = doc_dict.get(key, [])
                    for item in items:
                        if isinstance(item, dict):
                            t = item.get("text", "")
                            if t:
                                all_texts.append(t)
                md_text = "\n\n".join(all_texts)
            except Exception:
                pass

        if md_text:
            sections.append(
                Section(
                    name="Full Document",
                    level=1,
                    page_indices=list(range(10)),
                    printed_page_labels=[str(i + 1) for i in range(10)],
                    text=md_text,
                )
            )

    return sections


# ---------------------------------------------------------------------------
# Step 3: Section-aware chunker
# ---------------------------------------------------------------------------


def chunk_sections(
    sections: list[Section],
    drhp_id: str = DRHP_ID,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[ChunkPayload]:
    """Chunk sections into ChunkPayload objects.

    Section-aware: never crosses section boundaries.
    Token-counted via tiktoken gpt-4o.
    Overlap: re-includes last N tokens of previous chunk in next chunk.

    PITFALL 4: stores both page_start (PDF index) and printed_page_label.
    PITFALL 5: sets span_offsets=(0, len(chunk_text)) initially; Wave 3 narrows.

    Args:
        sections: List of Section objects from extract_sections_from_docling
        drhp_id: The DRHP identifier (e.g. "swiggy_2024_11")
        max_tokens: Maximum tokens per chunk (target 512; hard cap 1024)
        overlap_tokens: Token overlap between consecutive chunks

    Returns:
        List of ChunkPayload dataclasses ready for upsert.
    """
    chunks: list[ChunkPayload] = []

    for section in sections:
        if not section.text.strip():
            continue

        page_start = section.page_indices[0] if section.page_indices else 0
        page_end = section.page_indices[-1] if section.page_indices else 0
        printed_label = (
            section.printed_page_labels[0] if section.printed_page_labels else str(page_start + 1)
        )

        # Split section text into sentences for finer-grained chunking
        sentences = _split_into_sentences(section.text)
        if not sentences:
            continue

        current_chunk_sentences: list[str] = []
        current_tokens = 0
        overlap_sentences: list[str] = []

        for sentence in sentences:
            sentence_tokens = _count_tokens(sentence)

            # If a single sentence exceeds max_tokens, hard-split it
            if sentence_tokens > max_tokens:
                # Flush current chunk first
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences).strip()
                    if _count_tokens(chunk_text) >= CHUNK_ABSOLUTE_MIN:
                        chunks.append(
                            ChunkPayload(
                                chunk_id=str(uuid.uuid4()),
                                drhp_id=drhp_id,
                                section=section.name,
                                page_start=page_start,
                                page_end=page_end,
                                printed_page_label=printed_label,
                                chunk_text=chunk_text,
                                span_offsets=(0, len(chunk_text)),
                            )
                        )
                    current_chunk_sentences = []
                    current_tokens = 0

                # Hard-split the long sentence at max_tokens word boundaries
                words = sentence.split()
                word_group: list[str] = []
                group_tokens = 0
                for word in words:
                    wt = _count_tokens(word + " ")
                    if group_tokens + wt > max_tokens and word_group:
                        chunk_text = " ".join(word_group).strip()
                        if _count_tokens(chunk_text) >= CHUNK_ABSOLUTE_MIN:
                            chunks.append(
                                ChunkPayload(
                                    chunk_id=str(uuid.uuid4()),
                                    drhp_id=drhp_id,
                                    section=section.name,
                                    page_start=page_start,
                                    page_end=page_end,
                                    printed_page_label=printed_label,
                                    chunk_text=chunk_text,
                                    span_offsets=(0, len(chunk_text)),
                                )
                            )
                        word_group = [word]
                        group_tokens = wt
                    else:
                        word_group.append(word)
                        group_tokens += wt
                if word_group:
                    overlap_sentences = [" ".join(word_group)]
                    current_chunk_sentences = list(overlap_sentences)
                    current_tokens = group_tokens
                continue

            # If adding this sentence exceeds max_tokens, flush and start new chunk
            if current_tokens + sentence_tokens > max_tokens and current_chunk_sentences:
                chunk_text = " ".join(current_chunk_sentences).strip()
                if _count_tokens(chunk_text) >= CHUNK_ABSOLUTE_MIN:
                    chunks.append(
                        ChunkPayload(
                            chunk_id=str(uuid.uuid4()),
                            drhp_id=drhp_id,
                            section=section.name,
                            page_start=page_start,
                            page_end=page_end,
                            printed_page_label=printed_label,
                            chunk_text=chunk_text,
                            span_offsets=(0, len(chunk_text)),
                        )
                    )

                # Compute overlap: keep last N tokens of the just-flushed chunk
                overlap_text = " ".join(current_chunk_sentences)
                overlap_tokens_actual = _count_tokens(overlap_text)
                if overlap_tokens_actual > overlap_tokens:
                    # Keep only the tail sentences that fit in overlap window
                    overlap_parts: list[str] = []
                    kept_tokens = 0
                    for s in reversed(current_chunk_sentences):
                        st = _count_tokens(s)
                        if kept_tokens + st <= overlap_tokens:
                            overlap_parts.insert(0, s)
                            kept_tokens += st
                        else:
                            break
                    current_chunk_sentences = overlap_parts
                    current_tokens = kept_tokens
                else:
                    current_chunk_sentences = []
                    current_tokens = 0

            current_chunk_sentences.append(sentence)
            current_tokens += sentence_tokens

        # Flush remaining sentences in the section
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences).strip()
            if _count_tokens(chunk_text) >= CHUNK_ABSOLUTE_MIN:
                chunks.append(
                    ChunkPayload(
                        chunk_id=str(uuid.uuid4()),
                        drhp_id=drhp_id,
                        section=section.name,
                        page_start=page_start,
                        page_end=page_end,
                        printed_page_label=printed_label,
                        chunk_text=chunk_text,
                        span_offsets=(0, len(chunk_text)),
                    )
                )

    return chunks


def chunk_docling_json(
    docling_json: dict,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[ChunkPayload]:
    """High-level entry point: docling JSON → list[ChunkPayload].

    Combines section extraction + chunking in one call.
    Useful for tests and pipelines that already have the JSON loaded.
    """
    sections = extract_sections_from_docling(docling_json)
    return chunk_sections(sections, max_tokens=max_tokens, overlap_tokens=overlap_tokens)


# ---------------------------------------------------------------------------
# Step 4: Embed
# ---------------------------------------------------------------------------


def embed_chunks(chunks: list[ChunkPayload]) -> list[list[float]]:
    """Batch-embed chunk texts using bge-m3."""
    from tools.embedder import embed_batch

    if not chunks:
        return []

    texts = [c.chunk_text for c in chunks]
    total = len(texts)

    console.print(f"  Embedding {total} chunks (batch_size=4, ~3 sec/batch on CPU)...")

    start = time.time()
    vectors = embed_batch(texts, batch_size=4)
    elapsed = time.time() - start

    console.print(
        f"  Embed complete: {total} chunks in [bold]{elapsed:.1f}s[/bold] "
        f"({elapsed / total:.2f} s/chunk)"
    )
    return vectors


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


@app.command()
def parse(
    pdf_path: Path = typer.Option(PDF_PATH, "--pdf", help="Path to the DRHP PDF"),
    force: bool = typer.Option(False, "--force", help="Re-parse even if cache exists"),
) -> None:
    """Parse the DRHP PDF with Docling → write JSON cache."""
    if JSON_CACHE_PATH.exists() and not force:
        console.print(f"Cache already exists: {JSON_CACHE_PATH}")
        console.print("Use --force to re-parse.")
        return
    doc = parse_drhp(pdf_path)
    sections = extract_sections_from_docling(doc)
    console.print(f"  Extracted [bold]{len(sections)}[/bold] sections")


@app.command()
def chunk(
    max_tokens: int = typer.Option(CHUNK_MAX_TOKENS, "--max-tokens"),
    overlap: int = typer.Option(CHUNK_OVERLAP_TOKENS, "--overlap"),
) -> None:
    """Chunk the cached Docling JSON and print stats."""
    if not JSON_CACHE_PATH.exists():
        console.print(f"[red]Cache not found:[/red] {JSON_CACHE_PATH}")
        console.print("Run `parse` first.")
        raise typer.Exit(1)

    with open(JSON_CACHE_PATH) as f:
        doc = json.load(f)

    chunks = chunk_docling_json(doc, max_tokens=max_tokens, overlap_tokens=overlap)
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
    if not JSON_CACHE_PATH.exists():
        console.print(f"[red]Cache not found:[/red] {JSON_CACHE_PATH}")
        raise typer.Exit(1)

    with open(JSON_CACHE_PATH) as f:
        doc = json.load(f)

    chunks = chunk_docling_json(doc)
    embed_chunks(chunks)


@app.command()
def upsert(
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip upsert; print stats only"),
) -> None:
    """Upsert chunks to Qdrant (loads cached JSON + re-embeds)."""
    if not JSON_CACHE_PATH.exists():
        console.print(f"[red]Cache not found:[/red] {JSON_CACHE_PATH}")
        raise typer.Exit(1)

    with open(JSON_CACHE_PATH) as f:
        doc = json.load(f)

    chunks = chunk_docling_json(doc)
    vectors = embed_chunks(chunks)

    if dry_run:
        _print_dry_run_report(chunks)
        return

    from storage.vector import ensure_collection, upsert_chunks

    ensure_collection()
    upsert_chunks(chunks, vectors)
    console.print(f"  [bold green]Upserted {len(chunks)} chunks to Qdrant[/bold green]")
    _print_index_size_estimate(len(chunks))


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
    """Run the full pipeline: parse → chunk → embed → upsert.

    With --dry-run: runs parse + chunk + embed but skips the Qdrant upsert.
    Deferred mode: use --dry-run when Qdrant daemon is not yet running.
    """
    console.rule("[bold blue]DRHPLens DRHP Ingestion Pipeline[/bold blue]")

    # Step 1: Parse
    console.print("\n[bold]Step 1/4 — Parse[/bold]")
    doc = load_or_parse_drhp(pdf_path)
    sections = extract_sections_from_docling(doc)
    console.print(f"  Extracted {len(sections)} sections from Docling JSON")

    # Step 2: Chunk
    console.print("\n[bold]Step 2/4 — Chunk[/bold]")
    t0 = time.time()
    chunks = chunk_sections(sections, max_tokens=max_tokens, overlap_tokens=overlap)
    elapsed_chunk = time.time() - t0
    total_tokens = sum(_count_tokens(c.chunk_text) for c in chunks)
    console.print(
        f"  {len(chunks)} chunks | {total_tokens:,} tokens | {elapsed_chunk:.1f}s"
    )

    # Step 3: Embed
    console.print("\n[bold]Step 3/4 — Embed[/bold]")
    vectors = embed_chunks(chunks)

    # Step 4: Upsert (or dry-run)
    console.print("\n[bold]Step 4/4 — Upsert[/bold]")
    if dry_run:
        console.print(
            "  [yellow]--dry-run mode: skipping Qdrant upsert[/yellow]"
        )
        console.print(
            "  Run after starting Qdrant: [bold]python -m pipelines.ingest_swiggy all[/bold]"
        )
        _print_dry_run_report(chunks)
    else:
        from storage.vector import ensure_collection, upsert_chunks as _upsert_chunks

        console.print("  Upserting to Qdrant...")
        t_up = time.time()
        ensure_collection()
        _upsert_chunks(chunks, vectors)
        elapsed_up = time.time() - t_up
        console.print(
            f"  [bold green]Upserted {len(chunks)} chunks in {elapsed_up:.1f}s[/bold green]"
        )
        _print_index_size_estimate(len(chunks))

    console.rule("[bold blue]Pipeline complete[/bold blue]")


def _print_dry_run_report(chunks: list[ChunkPayload]) -> None:
    """Print a formatted dry-run report with stats and sample chunks."""
    if not chunks:
        console.print("  No chunks generated.")
        return

    sizes = [_count_tokens(c.chunk_text) for c in chunks]
    total_tokens = sum(sizes)
    total_bytes = sum(len(c.chunk_text.encode("utf-8")) for c in chunks)

    console.print(f"\n[bold]Dry-Run Report[/bold]")
    console.print(f"  Total chunks:      {len(chunks)}")
    console.print(f"  Total tokens:      {total_tokens:,}")
    console.print(f"  Total bytes:       {total_bytes:,}")
    console.print(f"  Token range:       min={min(sizes)} max={max(sizes)} avg={total_tokens//len(sizes)}")

    # Page coverage
    all_pages = set()
    for c in chunks:
        all_pages.update(range(c.page_start, c.page_end + 1))
    console.print(f"  Page coverage:     {len(all_pages)} unique PDF pages")

    # Sample 3 chunks
    sample_indices = [0, len(chunks) // 2, len(chunks) - 1]
    console.print(f"\n[bold]Sample Chunks:[/bold]")
    for i in sample_indices:
        c = chunks[i]
        preview = c.chunk_text[:120].replace("\n", " ")
        console.print(
            f"\n  chunk[{i}]:\n"
            f"    drhp_id:             {c.drhp_id}\n"
            f"    section:             {c.section}\n"
            f"    page_start:          {c.page_start}\n"
            f"    page_end:            {c.page_end}\n"
            f"    printed_page_label:  {c.printed_page_label}\n"
            f"    span_offsets:        {c.span_offsets}\n"
            f"    chunk_text (120c):   {preview!r}"
        )


def _print_index_size_estimate(chunk_count: int) -> None:
    """Print the estimated Qdrant collection size (per RESEARCH §A4)."""
    from storage.vector import EMBEDDING_DIM

    raw_vector_bytes = chunk_count * EMBEDDING_DIM * 4  # float32
    payload_bytes_estimate = chunk_count * 512  # ~512 bytes avg payload
    total_bytes = raw_vector_bytes + payload_bytes_estimate
    total_mb = total_bytes / (1024 * 1024)

    limit_gb = 1.0
    utilization = total_mb / (limit_gb * 1024) * 100

    console.print(
        f"  Estimated collection size: {total_mb:.1f} MB / {limit_gb * 1024:.0f} MB "
        f"({utilization:.1f}% of Qdrant free tier)"
    )
    if utilization > 50:
        console.print(
            f"  [yellow]Warning: > 50% utilization of Qdrant free tier[/yellow]"
        )


if __name__ == "__main__":
    app()
