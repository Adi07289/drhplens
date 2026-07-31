"""Unit test — the torch-free page-anchored parser (pipelines.ingest.parse_drhp_pages).

Pins the core invariant the parser exists to guarantee: EVERY chunk is anchored to
exactly one PDF page (page_start == page_end). The previous committed PyMuPDF-fallback
JSON flattened the whole prospectus into one section whose chunks all inherited page
span (0, 284), poisoning the cite-check windows and the numeric-faithfulness gate.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.ingest import chunk_sections, parse_drhp_pages

FIXTURE = Path("tests/fixtures/synthetic_drhp.pdf")


@pytest.mark.skipif(not FIXTURE.exists(), reason="synthetic DRHP fixture missing")
def test_parse_drhp_pages_single_page_anchoring() -> None:
    sections = parse_drhp_pages(FIXTURE)
    assert sections, "expected at least one page-section from the fixture"

    # Every section anchors to exactly one page (one Section per PDF page).
    for s in sections:
        assert len(s.page_indices) == 1, f"section {s.name!r} spans {s.page_indices}"

    # Page indices are non-decreasing across the document (page order preserved).
    pages = [s.page_indices[0] for s in sections]
    assert pages == sorted(pages)

    # Chunks inherit single-page anchoring — the fix's whole point (no (0, N) spans).
    chunks = chunk_sections(sections, drhp_id="test_drhp")
    for c in chunks:
        assert c.page_start == c.page_end, (
            f"chunk anchored to a page RANGE ({c.page_start},{c.page_end}) — "
            "page anchoring regressed"
        )
