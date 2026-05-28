"""
Stub: pipelines/ingest_swiggy.py — section-aware chunker.

Validates that the section-aware chunker:
- Preserves page anchors (page_start, page_end) on every chunk
- Keeps chunk sizes within 512-1024 tokens
- Does NOT split across DRHP sections
- Produces 1500-2500 chunks for the Swiggy DRHP

Wave 2 owns this implementation (INGEST-02, INGEST-03).
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 2 owns this — implements section-aware chunker", strict=False)
def test_section_aware_chunks_preserve_page_anchor() -> None:
    """Every chunk in the output must have non-null page_start and page_end from the
    source DRHP section; no chunk may span two different DRHP sections."""
    assert False, "Wave 2 must implement: run chunker on parsed DRHP, assert page anchors preserved"
