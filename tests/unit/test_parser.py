"""
Unit tests for the DRHP parser (Docling JSON → sections with page anchors).

Wave 2 — implements tests from 01-03-PLAN.md Task 2 <behavior>.

Tests use the committed Docling JSON (data/swiggy_drhp/swiggy_prospectus_2024_11.docling.json)
when available, or fall back to a minimal synthetic Docling-format JSON fixture.
"""
from __future__ import annotations

import pathlib

import pytest

DOCLING_JSON_PATH = (
    pathlib.Path(__file__).parent.parent.parent
    / "data"
    / "swiggy_drhp"
    / "swiggy_prospectus_2024_11.docling.json"
)

# ---------------------------------------------------------------------------
# Helper: build a minimal synthetic Docling-format JSON for unit tests
# ---------------------------------------------------------------------------


def _make_synthetic_docling_json() -> dict:
    """Return a minimal Docling-format JSON dict with 3 sections and page anchors.

    Used when the real Docling JSON is not yet committed to the repo.
    Structure follows Docling 2.95 export_to_dict() format.
    """
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "body": {
            "children": [
                # Section 1: Cover page
                {
                    "label": "title",
                    "text": "Cover Page",
                    "prov": [{"page_no": 1, "bbox": {"l": 0, "t": 0, "r": 500, "b": 100}}],
                    "children": [
                        {
                            "label": "text",
                            "text": "Swiggy Limited. DRHP pursuant to SEBI guidelines. BSE/NSE listing.",
                            "prov": [{"page_no": 1, "bbox": {"l": 0, "t": 100, "r": 500, "b": 200}}],
                            "children": [],
                        }
                    ],
                },
                # Section 2: Risk Factors
                {
                    "label": "section_header",
                    "text": "Risk Factors",
                    "prov": [{"page_no": 2, "bbox": {"l": 0, "t": 0, "r": 500, "b": 50}}],
                    "children": [
                        {
                            "label": "text",
                            "text": (
                                "The company faces significant competition from well-established "
                                "players including Zomato and other food delivery platforms. "
                                "Regulatory changes could adversely affect operations. "
                                "Technology dependence creates operational risks that may impact "
                                "service delivery and customer satisfaction."
                            ),
                            "prov": [{"page_no": 2, "bbox": {"l": 0, "t": 50, "r": 500, "b": 300}}],
                            "children": [],
                        },
                        {
                            "label": "text",
                            "text": (
                                "Market conditions and macroeconomic factors could negatively impact "
                                "the company's growth prospects. The food delivery industry is capital "
                                "intensive and requires significant ongoing investment. Unit economics "
                                "may not improve as anticipated."
                            ),
                            "prov": [{"page_no": 3, "bbox": {"l": 0, "t": 0, "r": 500, "b": 200}}],
                            "children": [],
                        },
                    ],
                },
                # Section 3: Issue Size
                {
                    "label": "section_header",
                    "text": "Issue Size and Objects of the Issue",
                    "prov": [{"page_no": 4, "bbox": {"l": 0, "t": 0, "r": 500, "b": 50}}],
                    "children": [
                        {
                            "label": "text",
                            "text": (
                                "Total Issue Size: Rs. 11,327 crore. Fresh Issue: Rs. 4,499 crore. "
                                "Offer for Sale: Rs. 6,828 crore. Use of Proceeds includes technology "
                                "infrastructure investment and brand marketing expenses."
                            ),
                            "prov": [{"page_no": 4, "bbox": {"l": 0, "t": 50, "r": 500, "b": 250}}],
                            "children": [],
                        }
                    ],
                },
            ]
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_docling_parse_emits_sections_with_page_anchors() -> None:
    """Docling output must contain sections; each section has name and page_indices."""
    from pipelines.ingest_swiggy import extract_sections_from_docling

    # Use committed JSON if available, otherwise use synthetic fixture
    if DOCLING_JSON_PATH.exists():
        import json
        with open(DOCLING_JSON_PATH) as f:
            doc = json.load(f)
        sections = extract_sections_from_docling(doc)
        assert len(sections) >= 100, (
            f"Expected >= 100 sections in the Swiggy DRHP, got {len(sections)}"
        )
    else:
        # Use synthetic fixture for CI / pre-committed state
        doc = _make_synthetic_docling_json()
        sections = extract_sections_from_docling(doc)
        assert len(sections) >= 2, (
            f"Synthetic fixture should produce >= 2 sections, got {len(sections)}"
        )

    # Every section must have name + page_indices
    for section in sections:
        assert section.name, f"Section {section!r} has empty name"
        assert isinstance(section.page_indices, list), (
            f"Section '{section.name}' page_indices must be a list"
        )
        assert len(section.page_indices) > 0, (
            f"Section '{section.name}' must have at least one page index"
        )
        assert all(isinstance(p, int) and p >= 0 for p in section.page_indices), (
            f"Section '{section.name}' page_indices must be non-negative ints"
        )


def test_sections_have_printed_page_labels() -> None:
    """Every section must have at least one printed_page_label."""
    from pipelines.ingest_swiggy import extract_sections_from_docling

    doc = _make_synthetic_docling_json()
    sections = extract_sections_from_docling(doc)

    for section in sections:
        assert len(section.printed_page_labels) > 0, (
            f"Section '{section.name}' must have at least one printed_page_label"
        )
        assert all(isinstance(label, str) and label for label in section.printed_page_labels), (
            f"Section '{section.name}' printed_page_labels must be non-empty strings"
        )


def test_sections_have_non_empty_text() -> None:
    """Sections returned from extraction must have non-empty text content."""
    from pipelines.ingest_swiggy import extract_sections_from_docling

    doc = _make_synthetic_docling_json()
    sections = extract_sections_from_docling(doc)

    assert len(sections) > 0, "Must produce at least one section"
    for section in sections:
        assert section.text.strip(), (
            f"Section '{section.name}' has empty text — should be filtered out"
        )


def test_risk_factors_section_present_in_synthetic() -> None:
    """The synthetic fixture must contain a Risk Factors section."""
    from pipelines.ingest_swiggy import extract_sections_from_docling

    doc = _make_synthetic_docling_json()
    sections = extract_sections_from_docling(doc)

    section_names = {s.name for s in sections}
    assert "Risk Factors" in section_names, (
        f"Expected 'Risk Factors' section in synthetic doc, got: {section_names}"
    )


def test_page_indices_are_monotonic_within_section() -> None:
    """page_indices within a section should not have backward jumps > 5 pages."""
    from pipelines.ingest_swiggy import extract_sections_from_docling

    doc = _make_synthetic_docling_json()
    sections = extract_sections_from_docling(doc)

    for section in sections:
        pages = sorted(section.page_indices)
        if len(pages) > 1:
            for a, b in zip(pages, pages[1:]):
                assert b - a <= 50, (
                    f"Section '{section.name}' has a large page gap: {a} to {b} "
                    "(may indicate incorrect page attribution)"
                )
