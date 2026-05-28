"""
Unit tests for the section-aware chunker in pipelines/ingest_swiggy.py.

Wave 2 — implements tests from 01-03-PLAN.md Task 2 <behavior>.

Tests run entirely in-memory with synthetic section data (no PDF required).
All tests target the ChunkPayload contract without needing Qdrant.
"""
from __future__ import annotations

import pytest

import tiktoken

TOKENIZER = tiktoken.encoding_for_model("gpt-4o")


def _count_tokens(text: str) -> int:
    return len(TOKENIZER.encode(text))


def _make_sections(n: int = 3):
    """Return a list of synthetic Section objects for testing."""
    from pipelines.ingest_swiggy import Section

    return [
        Section(
            name="Risk Factors",
            level=1,
            page_indices=[1, 2, 3],
            printed_page_labels=["ii", "iii", "iv"],
            text=(
                "The company faces significant competition from established players. "
                "Technology dependence creates operational risks that could impact service delivery. "
                "Market conditions may adversely affect financial performance. "
                "Regulatory changes in the food delivery sector pose compliance risks. "
                "The business model depends on a large network of delivery partners and restaurants. "
                "Customer acquisition costs remain high in a competitive market environment. "
                "Foreign exchange fluctuations could impact imported technology costs. "
                "The company has a history of net losses and may continue to incur losses. "
                "Key personnel departures could negatively affect operations and strategy. "
                "Data security breaches could harm reputation and result in financial penalties."
            ),
        ),
        Section(
            name="Issue Size",
            level=1,
            page_indices=[10, 11],
            printed_page_labels=["1", "2"],
            text=(
                "Total Issue Size is Rs. 11,327 crore comprising Fresh Issue of Rs. 4,499 crore "
                "and Offer for Sale of Rs. 6,828 crore. "
                "The objects of the Fresh Issue include investment in technology infrastructure, "
                "brand and marketing expenditure, and general corporate purposes. "
                "The company intends to use approximately Rs. 982 crore for technology investments. "
                "Brand marketing expenses are estimated at Rs. 1,179 crore over three fiscal years. "
                "General corporate purposes will absorb the remaining balance of the Fresh Issue proceeds."
            ),
        ),
        Section(
            name="Financial Statements",
            level=1,
            page_indices=[50, 51, 52, 53],
            printed_page_labels=["41", "42", "43", "44"],
            text=(
                "Revenue from Operations for FY2024 was Rs. 11,634 crore compared to "
                "Rs. 8,265 crore in FY2023, representing growth of 40.8 percent. "
                "EBITDA for FY2024 was negative Rs. 342 crore compared to negative Rs. 1,419 crore. "
                "Net Loss for FY2024 was Rs. 2,350 crore, improving from Rs. 3,629 crore in FY2023. "
                "Gross Order Value for FY2024 reached Rs. 28,173 crore. "
                "Average order value increased to Rs. 485 in Q4 FY2024 from Rs. 432 in Q4 FY2023. "
                "The company achieved platform profitability in Q2 FY2025 for the first time. "
                "Cash and cash equivalents at year end were Rs. 2,196 crore. "
                "Total equity as of March 2024 stood at Rs. 4,891 crore."
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Test 1: Section-aware page anchors preserved
# ---------------------------------------------------------------------------


def test_section_aware_chunks_preserve_page_anchor() -> None:
    """Every chunk from a section must have page_start/page_end from that section."""
    from pipelines.ingest_swiggy import chunk_sections

    sections = _make_sections()
    chunks = chunk_sections(sections)

    assert len(chunks) > 0, "Chunker must produce at least one chunk"

    for chunk in chunks:
        # Find the source section
        source_sections = [s for s in sections if s.name == chunk.section]
        assert source_sections, f"Chunk section '{chunk.section}' not found in source sections"
        source = source_sections[0]

        # page_start and page_end must be within the source section's page range
        section_min_page = min(source.page_indices)
        section_max_page = max(source.page_indices)
        assert chunk.page_start >= section_min_page, (
            f"Chunk in section '{chunk.section}' has page_start={chunk.page_start} "
            f"below section minimum page {section_min_page}"
        )
        assert chunk.page_end <= section_max_page, (
            f"Chunk in section '{chunk.section}' has page_end={chunk.page_end} "
            f"above section maximum page {section_max_page}"
        )
        assert chunk.page_start <= chunk.page_end, (
            f"Chunk page_start ({chunk.page_start}) > page_end ({chunk.page_end})"
        )


# ---------------------------------------------------------------------------
# Test 2: Chunk size in target band
# ---------------------------------------------------------------------------


def test_chunk_size_in_target_band() -> None:
    """Every chunk's token count must be between CHUNK_ABSOLUTE_MIN and 1280 tokens.

    The plan target is 384-1280 (512 +/- 25%).
    We use the absolute minimum (50 tokens) as the floor to account for small sections.
    """
    from pipelines.ingest_swiggy import CHUNK_ABSOLUTE_MIN, chunk_sections

    sections = _make_sections()
    chunks = chunk_sections(sections, max_tokens=512, overlap_tokens=100)

    assert len(chunks) > 0, "Must produce at least one chunk"

    for chunk in chunks:
        token_count = _count_tokens(chunk.chunk_text)
        # Floor: above absolute minimum
        assert token_count >= CHUNK_ABSOLUTE_MIN, (
            f"Chunk in '{chunk.section}' has {token_count} tokens, "
            f"below minimum {CHUNK_ABSOLUTE_MIN}"
        )
        # Ceiling: max 1280 (512 * 2.5 as hard upper bound)
        assert token_count <= 1280, (
            f"Chunk in '{chunk.section}' has {token_count} tokens, exceeds 1280"
        )


# ---------------------------------------------------------------------------
# Test 3: span_offsets present and valid
# ---------------------------------------------------------------------------


def test_chunker_attaches_span_offsets_within_chunk_text() -> None:
    """Every chunk must have span_offsets set to (0, len(chunk_text)).

    Wave 3 cite-check narrows this per-claim; Wave 2 stores the full span.
    PITFALL 5 mitigation: span_offsets is REQUIRED to exist.
    """
    from pipelines.ingest_swiggy import chunk_sections

    sections = _make_sections()
    chunks = chunk_sections(sections)

    for chunk in chunks:
        assert chunk.span_offsets is not None, (
            f"Chunk in '{chunk.section}' missing span_offsets (PITFALL 5 violation)"
        )
        start, end = chunk.span_offsets
        assert start == 0, f"Default span_offsets start must be 0, got {start}"
        assert end == len(chunk.chunk_text), (
            f"Default span_offsets end must be len(chunk_text)={len(chunk.chunk_text)}, got {end}"
        )
        assert start <= end, f"span_offsets start ({start}) > end ({end})"


# ---------------------------------------------------------------------------
# Test 4: printed_page_label preserved
# ---------------------------------------------------------------------------


def test_chunker_preserves_printed_page_label() -> None:
    """Every chunk must have a non-empty printed_page_label (PITFALL 4 mitigation)."""
    from pipelines.ingest_swiggy import chunk_sections

    sections = _make_sections()
    chunks = chunk_sections(sections)

    for chunk in chunks:
        assert chunk.printed_page_label, (
            f"Chunk in '{chunk.section}' has empty printed_page_label "
            "(PITFALL 4: must store human-readable page label)"
        )
        assert isinstance(chunk.printed_page_label, str), (
            f"printed_page_label must be a string"
        )


# ---------------------------------------------------------------------------
# Test 5: Non-empty sections produce non-empty chunks
# ---------------------------------------------------------------------------


def test_sections_produce_non_empty_chunks() -> None:
    """Non-empty sections must produce at least one chunk."""
    from pipelines.ingest_swiggy import Section, chunk_sections

    # A single section with substantial text (well above CHUNK_ABSOLUTE_MIN=50 tokens)
    section = Section(
        name="Test Section",
        level=1,
        page_indices=[5, 6],
        printed_page_labels=["vi", "vii"],
        text=(
            "This is a test section with enough content to produce at least one chunk. "
            "The section discusses various topics including financial performance, "
            "operational metrics, and strategic objectives of the company under review. "
            "It contains multiple sentences to ensure chunking logic is properly exercised. "
            "The company has demonstrated consistent revenue growth over the past three years. "
            "Profitability metrics have improved substantially in recent quarters. "
            "Management has outlined a clear strategy for future growth and market expansion. "
            "The operational efficiency ratio has improved from 72 percent to 68 percent. "
            "These improvements reflect cost optimization initiatives undertaken by the team."
        ),
    )
    chunks = chunk_sections([section])
    assert len(chunks) >= 1, "A non-empty section must produce at least one chunk"


# ---------------------------------------------------------------------------
# Test 6: drhp_id propagated correctly
# ---------------------------------------------------------------------------


def test_chunker_propagates_drhp_id() -> None:
    """All chunks must carry the correct drhp_id."""
    from pipelines.ingest_swiggy import chunk_sections

    sections = _make_sections()
    chunks = chunk_sections(sections, drhp_id="test_ipo_2024")

    for chunk in chunks:
        assert chunk.drhp_id == "test_ipo_2024", (
            f"Expected drhp_id='test_ipo_2024', got '{chunk.drhp_id}'"
        )


# ---------------------------------------------------------------------------
# Test 7: chunk_text is non-empty string
# ---------------------------------------------------------------------------


def test_chunk_text_is_non_empty() -> None:
    """Every chunk must have non-empty chunk_text."""
    from pipelines.ingest_swiggy import chunk_sections

    sections = _make_sections()
    chunks = chunk_sections(sections)

    for chunk in chunks:
        assert chunk.chunk_text.strip(), (
            f"Chunk in '{chunk.section}' has empty chunk_text"
        )


# ---------------------------------------------------------------------------
# Test 8: No cross-section contamination
# ---------------------------------------------------------------------------


def test_no_cross_section_contamination() -> None:
    """Chunks must not reference text from a different section than their section field."""
    from pipelines.ingest_swiggy import Section, chunk_sections

    # Two distinctly-named sections with unique keywords
    sections = [
        Section(
            name="Alpha Section",
            level=1,
            page_indices=[1],
            printed_page_labels=["1"],
            text=(
                "ALPHA_MARKER: This section is about alpha content only. "
                "The alpha data contains unique identifiers. Alpha metrics are positive."
            ),
        ),
        Section(
            name="Beta Section",
            level=1,
            page_indices=[2],
            printed_page_labels=["2"],
            text=(
                "BETA_MARKER: This section is about beta content only. "
                "The beta data contains unique identifiers. Beta metrics are measured."
            ),
        ),
    ]

    chunks = chunk_sections(sections)

    alpha_chunks = [c for c in chunks if c.section == "Alpha Section"]
    beta_chunks = [c for c in chunks if c.section == "Beta Section"]

    # Alpha chunks must not contain BETA_MARKER
    for chunk in alpha_chunks:
        assert "BETA_MARKER" not in chunk.chunk_text, (
            f"Alpha chunk contains Beta section content (cross-contamination)"
        )

    # Beta chunks must not contain ALPHA_MARKER
    for chunk in beta_chunks:
        assert "ALPHA_MARKER" not in chunk.chunk_text, (
            f"Beta chunk contains Alpha section content (cross-contamination)"
        )
