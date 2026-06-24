"""
pipelines/ingest.py — Generalized offline DRHP ingestion pipeline (Typer CLI).

Generalizes pipelines/ingest_swiggy.py (Wave 0/1 single-IPO pipeline) into a
parameterized, multi-IPO entry point per 02-RESEARCH.md §Pattern 2.

Storage-bus invariant (SKELETON §A):
- This pipeline ONLY writes to Qdrant. The runtime agent ONLY reads.
- They never share Python state and never invoke each other.

Pipeline steps (per IPO):
  1. parse   — Docling 2.95 PDF -> structured JSON (sections, tables, page anchors)
  2. chunk   — Section-aware chunker (512-1024 tokens, 100-200 overlap), drhp_id-tagged
  3. embed   — bge-m3 batch encode (CPU; batch_size=4)
  4. upsert  — delete-by-drhp_id (idempotency, T-02-A6) then Qdrant upsert

Usage:
    python -m pipelines.ingest ingest <drhp_id> --pdf <path>   # single IPO
    python -m pipelines.ingest ingest-all                      # loop over catalogue.json
    python -m pipelines.ingest ingest-all --dry-run            # parse+chunk+embed only

PITFALL mitigations:
  P14 item 1: per-IPO failure isolation in ingest-all (try/except per IPO).
  P14 item 2: parse_quality_gate flags fallback/garbage parses (extraction_quality).
  P14 item 3: front_matter_pages is a per-IPO parameter, not a hard-coded constant.
  P14 item 4: SHA-256 pin verified before parse when catalogue source_sha256 is set.
  A6: delete_by_drhp_id() called before upsert_chunks() — idempotent re-ingest.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tiktoken
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from storage.vector import ChunkPayload

app = typer.Typer(help="DRHPLens generalized offline DRHP ingestion pipeline.")
console = Console()

# ---------------------------------------------------------------------------
# Constants — defaults only; never used as the value inside ingest_drhp().
# ---------------------------------------------------------------------------

CHUNK_MAX_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 100
CHUNK_ABSOLUTE_MIN = 50   # Discard chunks shorter than this (table headers etc.)

# Default front-matter page count when an IPO doesn't specify one (Swiggy-tuned
# historical default; per-IPO override is the P14-item-3 fix — see front_matter_pages
# parameter on ingest_drhp / chunk_sections / _infer_printed_label).
DEFAULT_FRONT_MATTER_PAGES = 20

# P14 item 2: parse-quality gate thresholds.
MIN_SECTIONS = 10
FALLBACK_SECTION_NAMES = {"full document", "tables", "preamble"}
KNOWN_DRHP_SECTION_RE = re.compile(
    r"risk factors|objects of the (issue|offer)|our business|restated",
    re.IGNORECASE,
)

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
# IngestReport — return value of ingest_drhp()
# ---------------------------------------------------------------------------


@dataclass
class IngestReport:
    """Summary of a single ingest_drhp() run.

    extraction_quality: "ok" | "fallback" — set by parse_quality_gate().
    sha_verified: True if a source_sha256 was supplied and matched; None if
      no SHA pin was supplied (verification skipped, not failed).
    """

    drhp_id: str
    chunk_count: int
    page_coverage: int
    token_stats: dict[str, int] = field(default_factory=dict)
    sha_verified: Optional[bool] = None
    extraction_quality: str = "ok"
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_printed_label(
    page_idx: int,
    docling_page_meta: dict | None,
    front_matter_pages: int = DEFAULT_FRONT_MATTER_PAGES,
) -> str:
    """Infer the printed page label from Docling metadata or page index.

    PITFALL 4 mitigation: Indian DRHPs have Roman-numeral front matter (i, ii, iii...)
    before switching to Arabic pagination. We store BOTH the PDF index (0-based)
    AND the visible printed label.

    P14 item 3 fix: front_matter_pages is a parameter (per-IPO), not a hard-coded
    Swiggy-tuned constant.

    Args:
        page_idx: 0-based PDF page index
        docling_page_meta: Docling page metadata dict (may contain label)
        front_matter_pages: number of Roman-numeral front-matter pages for this IPO
    """
    if docling_page_meta:
        for key in ("page_no", "printed_page_no", "label", "page_number"):
            val = docling_page_meta.get(key)
            if val is not None:
                return str(val)

    if page_idx < front_matter_pages:
        roman_labels = [
            "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
            "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
        ]
        return roman_labels[page_idx] if page_idx < len(roman_labels) else str(page_idx + 1)

    body_page = page_idx - front_matter_pages + 1
    return str(body_page)


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken gpt-4o encoding."""
    return len(TOKENIZER.encode(text))


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences at natural boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    result = []
    for sent in sentences:
        parts = re.split(r"\n{2,}", sent)
        result.extend(p.strip() for p in parts if p.strip())
    return result if result else [text.strip()] if text.strip() else []


def verify_sha256(pdf_path: Path, expected_sha256: str | None) -> bool | None:
    """Verify the PDF bytes against a SHA-256 pin (P14 item 4 / T-02-V6).

    Returns:
        True if expected_sha256 was supplied and matched.
        None if expected_sha256 is None (no pin to verify — not a failure).

    Raises:
        ValueError: if expected_sha256 was supplied and did NOT match.
    """
    if expected_sha256 is None:
        return None
    actual = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if actual.lower() != expected_sha256.lower():
        raise ValueError(
            f"SHA-256 mismatch for {pdf_path.name}: "
            f"expected {expected_sha256}, got {actual}. Refusing to ingest "
            "(possible version drift — T-02-V6)."
        )
    return True


# ---------------------------------------------------------------------------
# Step 1: Parse
# ---------------------------------------------------------------------------


def parse_drhp(pdf_path: Path, json_cache_path: Path) -> dict:
    """Parse the DRHP PDF using Docling 2.95 and return the document dict.

    This is an expensive step (5-15 min on CPU for a 300-500 page DRHP).
    Output is cached to JSON at json_cache_path; subsequent runs load from cache.

    Args:
        pdf_path: Path to the DRHP PDF file.
        json_cache_path: Where to write/read the cached Docling JSON.

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

    json_cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_cache_path, "w", encoding="utf-8") as f:
        json.dump(doc_dict, f, ensure_ascii=False, indent=None)
    console.print(f"  JSON cache saved to: {json_cache_path}")

    return doc_dict


def load_or_parse_drhp(pdf_path: Path, json_cache_path: Path) -> dict:
    """Load cached Docling JSON or parse PDF if cache is missing."""
    if json_cache_path.exists():
        console.print(f"[bold]Loading cached Docling JSON:[/bold] {json_cache_path}")
        with open(json_cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return parse_drhp(pdf_path, json_cache_path)


# ---------------------------------------------------------------------------
# Step 2: Section extraction from Docling JSON
# ---------------------------------------------------------------------------


def extract_sections_from_docling(
    doc_dict: dict, front_matter_pages: int = DEFAULT_FRONT_MATTER_PAGES
) -> list[Section]:
    """Walk the Docling document tree and extract a flat list of sections.

    Docling's export_to_dict() structure varies by version. We support:
    - doc_dict['body'] with nested items that have 'label', 'text', 'prov'
    - Fallback to doc_dict['texts'] list if 'body' is not present

    Per ARCHITECTURE Pattern 1: section boundaries are deeply semantic in DRHPs.
    We never produce cross-section chunks.

    Args:
        doc_dict: Docling document dict from export_to_dict()
        front_matter_pages: per-IPO Roman-numeral front-matter page count (P14 item 3)

    Returns:
        List of Section objects with name, level, page_indices, etc.
    """
    sections: list[Section] = []
    current_section: Section | None = None
    current_text_parts: list[str] = []

    def _flush_current() -> None:
        nonlocal current_section, current_text_parts
        if current_section is not None and current_text_parts:
            current_section.text = "\n".join(current_text_parts).strip()
            if current_section.text:
                sections.append(current_section)
        current_section = None
        current_text_parts = []

    def _get_page_info(item: dict) -> tuple[list[int], list[str]]:
        page_indices: list[int] = []
        printed_labels: list[str] = []

        prov = item.get("prov", [])
        if isinstance(prov, list):
            for p in prov:
                if isinstance(p, dict):
                    page_no = p.get("page_no")
                    if page_no is not None:
                        idx = int(page_no) - 1
                        if idx not in page_indices:
                            page_indices.append(idx)
        elif isinstance(prov, dict):
            page_no = prov.get("page_no")
            if page_no is not None:
                page_indices.append(int(page_no) - 1)

        for idx in page_indices:
            printed_labels.append(_infer_printed_label(idx, None, front_matter_pages))

        return page_indices, printed_labels

    def _walk_items(items: list[dict], level: int = 0) -> None:
        nonlocal current_section, current_text_parts

        for item in items:
            if not isinstance(item, dict):
                continue

            label = item.get("label", "")
            text = item.get("text", "") or ""
            page_indices, printed_labels = _get_page_info(item)

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
                if current_section is None:
                    current_section = Section(
                        name="Preamble",
                        level=1,
                        page_indices=page_indices if page_indices else [0],
                        printed_page_labels=printed_labels if printed_labels else ["i"],
                        text="",
                    )
                    current_text_parts = []

                current_text_parts.append(text.strip())

                for idx in page_indices:
                    if idx not in current_section.page_indices:
                        current_section.page_indices.append(idx)

            if label == "table" or item.get("$ref_hash"):
                table_text = item.get("text", "")
                if not table_text:
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

            children = item.get("children", [])
            if children:
                _walk_items(children, level + 1)

    body = doc_dict.get("body", {})
    if isinstance(body, dict):
        children = body.get("children", [])
        if children:
            _walk_items(children)

    if not sections:
        texts = doc_dict.get("texts", [])
        if texts:
            _walk_items(texts)

    if not sections:
        pages = doc_dict.get("pages", [])
        for page_data in pages:
            if isinstance(page_data, dict):
                page_idx = page_data.get("page_no", 1) - 1
                printed = _infer_printed_label(page_idx, page_data, front_matter_pages)
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

    if not sections:
        md_text = doc_dict.get("md_text", "") or ""
        if not md_text:
            try:
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
# Step 2b: Parse-quality gate (P14 item 2)
# ---------------------------------------------------------------------------


def parse_quality_gate(sections: list[Section]) -> str:
    """Flag a parse as "fallback" rather than silently ingesting garbage (P14).

    Returns "fallback" if ANY of:
      - len(sections) < MIN_SECTIONS, OR
      - every section name matches the fallback pattern (Full Document / Page N /
        Tables / Preamble, in isolation), OR
      - no section name matches a known DRHP section regex (Risk Factors |
        Objects of the Issue/Offer | Our Business | Restated).

    Returns "ok" otherwise.
    """
    if len(sections) < MIN_SECTIONS:
        return "fallback"

    def _is_fallback_name(name: str) -> bool:
        lowered = name.strip().lower()
        if lowered in FALLBACK_SECTION_NAMES:
            return True
        if re.match(r"^page \d+$", lowered):
            return True
        return False

    if all(_is_fallback_name(s.name) for s in sections):
        return "fallback"

    if not any(KNOWN_DRHP_SECTION_RE.search(s.name) for s in sections):
        return "fallback"

    return "ok"


# ---------------------------------------------------------------------------
# Step 3: Section-aware chunker
# ---------------------------------------------------------------------------


def chunk_sections(
    sections: list[Section],
    drhp_id: str,
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
        drhp_id: The DRHP identifier (e.g. "hyundai_2024_10") — REQUIRED, no
          module-level default (P14/generalization — every chunk is explicitly
          tagged with the IPO it belongs to).
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

        sentences = _split_into_sentences(section.text)
        if not sentences:
            continue

        current_chunk_sentences: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = _count_tokens(sentence)

            if sentence_tokens > max_tokens:
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
                    current_chunk_sentences = [" ".join(word_group)]
                    current_tokens = group_tokens
                continue

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

                overlap_text = " ".join(current_chunk_sentences)
                overlap_tokens_actual = _count_tokens(overlap_text)
                if overlap_tokens_actual > overlap_tokens:
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
    drhp_id: str,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    front_matter_pages: int = DEFAULT_FRONT_MATTER_PAGES,
) -> list[ChunkPayload]:
    """High-level entry point: docling JSON -> list[ChunkPayload].

    Combines section extraction + chunking in one call.
    """
    sections = extract_sections_from_docling(docling_json, front_matter_pages=front_matter_pages)
    return chunk_sections(
        sections, drhp_id=drhp_id, max_tokens=max_tokens, overlap_tokens=overlap_tokens
    )


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
# Step 5: ingest_drhp — the generalized entry point (Pattern 2)
# ---------------------------------------------------------------------------


def ingest_drhp(
    drhp_id: str,
    pdf_path: Path,
    *,
    json_cache_path: Path | None = None,
    front_matter_pages: int = DEFAULT_FRONT_MATTER_PAGES,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    source_sha256: str | None = None,
    dry_run: bool = False,
) -> IngestReport:
    """Parse -> chunk(drhp_id) -> embed -> [delete-by-drhp_id ->] upsert.

    Idempotent per drhp_id: existing points for drhp_id are deleted before
    upsert (A6 — re-ingest cannot duplicate points). Skipped entirely when
    dry_run=True (no Qdrant access at all in dry-run mode).

    No module-level hard-codes are used inside this function — drhp_id,
    pdf_path, front_matter_pages, etc. are all parameters.

    Args:
        drhp_id: e.g. "hyundai_2024_10"
        pdf_path: data/<drhp_id>/<file>.pdf
        json_cache_path: defaults to pdf_path.with_suffix(".docling.json")
        front_matter_pages: per-IPO Roman-numeral front-matter page count (P14 item 3)
        max_tokens: chunk token cap
        overlap_tokens: chunk overlap
        source_sha256: optional SHA-256 pin to verify before parsing (P14 item 4)
        dry_run: if True, skip the Qdrant delete+upsert step entirely

    Returns:
        IngestReport summarizing the run.
    """
    if json_cache_path is None:
        json_cache_path = pdf_path.with_suffix(".docling.json")

    sha_verified = verify_sha256(pdf_path, source_sha256)

    doc = load_or_parse_drhp(pdf_path, json_cache_path)
    sections = extract_sections_from_docling(doc, front_matter_pages=front_matter_pages)
    quality = parse_quality_gate(sections)

    chunks = chunk_sections(
        sections, drhp_id=drhp_id, max_tokens=max_tokens, overlap_tokens=overlap_tokens
    )

    token_stats: dict[str, int] = {}
    if chunks:
        sizes = [_count_tokens(c.chunk_text) for c in chunks]
        token_stats = {
            "min": min(sizes),
            "max": max(sizes),
            "avg": sum(sizes) // len(sizes),
            "total": sum(sizes),
        }

    page_coverage_set: set[int] = set()
    for c in chunks:
        page_coverage_set.update(range(c.page_start, c.page_end + 1))

    if quality == "fallback":
        console.print(
            f"  [yellow]Warning: parse-quality gate flagged {drhp_id} as 'fallback' "
            f"({len(sections)} sections) — review before shipping this IPO's snapshot.[/yellow]"
        )

    if dry_run:
        return IngestReport(
            drhp_id=drhp_id,
            chunk_count=len(chunks),
            page_coverage=len(page_coverage_set),
            token_stats=token_stats,
            sha_verified=sha_verified,
            extraction_quality=quality,
            dry_run=True,
        )

    vectors = embed_chunks(chunks)

    from storage.vector import delete_by_drhp_id, ensure_collection, upsert_chunks

    ensure_collection()
    delete_by_drhp_id(drhp_id)  # A6 idempotency — delete before upsert
    upsert_chunks(chunks, vectors)

    return IngestReport(
        drhp_id=drhp_id,
        chunk_count=len(chunks),
        page_coverage=len(page_coverage_set),
        token_stats=token_stats,
        sha_verified=sha_verified,
        extraction_quality=quality,
        dry_run=False,
    )


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    drhp_id: str = typer.Argument(..., help="The drhp_id to ingest, e.g. hyundai_2024_10"),
    pdf: Path = typer.Option(..., "--pdf", help="Path to the DRHP PDF"),
    front_matter_pages: int = typer.Option(DEFAULT_FRONT_MATTER_PAGES, "--front-matter-pages"),
    max_tokens: int = typer.Option(CHUNK_MAX_TOKENS, "--max-tokens"),
    overlap: int = typer.Option(CHUNK_OVERLAP_TOKENS, "--overlap"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip the Qdrant upsert"),
) -> None:
    """Ingest a single IPO: python -m pipelines.ingest ingest <drhp_id> --pdf <path>."""
    console.rule(f"[bold blue]Ingesting {drhp_id}[/bold blue]")
    report = ingest_drhp(
        drhp_id=drhp_id,
        pdf_path=pdf,
        front_matter_pages=front_matter_pages,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        dry_run=dry_run,
    )
    console.print(
        f"  chunks={report.chunk_count} page_coverage={report.page_coverage} "
        f"quality={report.extraction_quality} dry_run={report.dry_run}"
    )
    if report.extraction_quality == "fallback":
        console.print("  [yellow]This IPO should be reviewed before adding to catalogue.json[/yellow]")


@app.command(name="ingest-all")
def ingest_all(
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip the Qdrant upsert for every IPO"),
) -> None:
    """Loop over data/catalogue.json and ingest every IPO.

    Per-IPO failure isolation (P14 item 1): one IPO's exception is logged and
    skipped; it does not abort the batch.
    """
    from data.catalogue_loader import load_catalogue

    catalogue = load_catalogue()
    console.rule(f"[bold blue]Ingesting {len(catalogue)} IPOs[/bold blue]")

    results: list[tuple[str, str]] = []  # (drhp_id, status)
    for ipo in catalogue:
        pdf_path = Path(f"data/{ipo.drhp_id}") / f"{ipo.drhp_id}.pdf"
        console.print(f"\n[bold]{ipo.drhp_id}[/bold] ({ipo.issuer})")
        try:
            report = ingest_drhp(
                drhp_id=ipo.drhp_id,
                pdf_path=pdf_path,
                front_matter_pages=ipo.front_matter_pages,
                source_sha256=ipo.source_sha256,
                dry_run=dry_run,
            )
            status = report.extraction_quality
            console.print(f"  chunks={report.chunk_count} quality={status}")
            results.append((ipo.drhp_id, status))
        except Exception as exc:  # noqa: BLE001 — per-IPO failure isolation (P14)
            console.print(f"  [red]FAILED: {exc}[/red]")
            results.append((ipo.drhp_id, "failed"))

    console.print("\n[bold]Summary[/bold]")
    for drhp_id, status in results:
        console.print(f"  {drhp_id}: {status}")


if __name__ == "__main__":
    app()
