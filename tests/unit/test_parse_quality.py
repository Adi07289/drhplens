"""
Unit test — a DRHP that parses to < N sections / fails table extraction is
flagged, not silently ingested (Pitfall P14).

Requirement: (P14). Threat: none (data-quality robustness concern).
Secure behavior: parse-quality gate flags fallback/garbage parses; flagged IPOs
are excluded from catalogue.json rather than silently shipped with bad data.

Wave 2 implements (02-VALIDATION.md row "2-parse-quality-gate").
"""
from __future__ import annotations

from pipelines.ingest import MIN_SECTIONS, Section, parse_quality_gate


def _section(name: str, text: str = "some body text") -> Section:
    return Section(name=name, level=1, page_indices=[0], printed_page_labels=["1"], text=text)


def test_low_section_count_parse_flagged_as_fallback() -> None:
    """A parse producing fewer than MIN_SECTIONS sections is flagged 'fallback'."""
    sections = [_section(f"Section {i}") for i in range(MIN_SECTIONS - 1)]
    assert len(sections) < MIN_SECTIONS

    quality = parse_quality_gate(sections)

    assert quality == "fallback"


def test_full_document_fallback_section_flagged() -> None:
    """A single 'Full Document' fallback section (the extract_sections_from_docling
    last-resort branch) is flagged 'fallback' regardless of count."""
    sections = [_section("Full Document", text="entire prospectus dumped as one blob")]

    quality = parse_quality_gate(sections)

    assert quality == "fallback"


def test_page_n_fallback_sections_flagged() -> None:
    """Sections named only 'Page N' (the raw per-page fallback branch) with no
    known DRHP section name are flagged 'fallback' even if there are many of them."""
    sections = [_section(f"Page {i}") for i in range(MIN_SECTIONS + 5)]

    quality = parse_quality_gate(sections)

    assert quality == "fallback"


def test_no_known_section_name_flagged_as_fallback() -> None:
    """Plenty of sections, but none matching a known DRHP section regex, is
    still flagged 'fallback' (heterogeneous-layout signal)."""
    sections = [_section(f"Unrecognized Heading {i}") for i in range(MIN_SECTIONS + 2)]

    quality = parse_quality_gate(sections)

    assert quality == "fallback"


def test_healthy_parse_yields_ok() -> None:
    """A healthy parse (>= MIN_SECTIONS, at least one section matching a known
    DRHP section regex) yields extraction_quality='ok'."""
    section_names = [
        "Risk Factors",
        "Our Business",
        "Objects of the Issue",
        "Our Promoters",
        "Capital Structure",
        "Restated Financial Statements",
        "General Information",
        "The Issue",
        "Industry Overview",
        "Outstanding Litigation",
        "Management's Discussion and Analysis",
    ]
    sections = [_section(name) for name in section_names]
    assert len(sections) >= MIN_SECTIONS

    quality = parse_quality_gate(sections)

    assert quality == "ok"


def test_healthy_parse_with_objects_of_the_offer_variant() -> None:
    """'Objects of the Offer' (RHP/Prospectus naming variant) also satisfies
    the known-section regex."""
    section_names = [
        "Objects of the Offer",
        "Section A", "Section B", "Section C", "Section D",
        "Section E", "Section F", "Section G", "Section H", "Section I",
    ]
    sections = [_section(name) for name in section_names]
    assert len(sections) >= MIN_SECTIONS

    quality = parse_quality_gate(sections)

    assert quality == "ok"
