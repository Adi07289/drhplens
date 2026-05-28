"""
Stub: pipelines/ingest_swiggy.py — Docling PDF parser.

Validates that Docling 2.95 parses the Swiggy DRHP into structured JSON
with section names and page anchors. Financial tables must extract without
merged-cell mangling (pdfplumber fallback for flagged pages).

Wave 2 owns this implementation (INGEST-01, INGEST-02).
"""
from __future__ import annotations

import pytest

pytest.importorskip("docling", reason="docling ships in Wave 2 environment")


@pytest.mark.xfail(reason="Wave 2 owns this — runs Docling parse on Swiggy DRHP", strict=False)
def test_docling_parse_emits_sections_with_page_anchors() -> None:
    """Docling output must contain > 100 sections; each section has page_start, page_end,
    and section name. Financial-statement pages must not have merged-cell mangling."""
    assert False, "Wave 2 must implement: run Docling on fixture DRHP, assert section count and page anchors"
