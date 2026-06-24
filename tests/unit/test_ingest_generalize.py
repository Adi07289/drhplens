"""
Unit test — pipelines/ingest.py::ingest_drhp(drhp_id, pdf_path, ...) parameterized.

Requirement: INGEST (reuse). Threat: none.
Secure behavior: pipelines/ingest.py(drhp_id, pdf_path, ...) is parameterized;
no module-level hard-codes remain (generalized from pipelines/ingest_swiggy.py).

Wave 2 implements (02-VALIDATION.md row "2-ingest-generalize").
"""
from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import pytest


def _tiny_docling_doc() -> dict:
    """A minimal Docling-shaped doc dict with enough sections to clear the
    parse-quality gate (>= MIN_SECTIONS, includes a known DRHP section name)."""
    body_children = []
    section_names = [
        "RISK FACTORS",
        "OUR BUSINESS",
        "OBJECTS OF THE ISSUE",
        "OUR PROMOTERS",
        "CAPITAL STRUCTURE",
        "RESTATED FINANCIAL STATEMENTS",
        "GENERAL INFORMATION",
        "THE ISSUE",
        "INDUSTRY OVERVIEW",
        "OUTSTANDING LITIGATION",
        "MANAGEMENT",
    ]
    for i, name in enumerate(section_names):
        body_children.append(
            {
                "label": "section_header",
                "text": name,
                "prov": [{"page_no": i + 1}],
            }
        )
        body_children.append(
            {
                "label": "text",
                "text": f"Body text for section {name}. " * 5,
                "prov": [{"page_no": i + 1}],
            }
        )
    return {"body": {"children": body_children}}


@pytest.fixture
def tiny_docling_json(tmp_path: Path) -> Path:
    import json

    cache_path = tmp_path / "tiny.docling.json"
    cache_path.write_text(json.dumps(_tiny_docling_doc()))
    return cache_path


def test_ingest_drhp_accepts_drhp_id_and_pdf_path(tmp_path: Path, tiny_docling_json: Path) -> None:
    """ingest_drhp(drhp_id=..., pdf_path=..., dry_run=True) tags every chunk
    with the supplied drhp_id, not a Swiggy constant."""
    from pipelines.ingest import ingest_drhp

    pdf_path = tmp_path / "hyundai.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("pipelines.ingest.load_or_parse_drhp") as mock_load:
        import json

        mock_load.return_value = json.loads(tiny_docling_json.read_text())

        report = ingest_drhp(
            drhp_id="hyundai_2024_10",
            pdf_path=pdf_path,
            json_cache_path=tiny_docling_json,
            dry_run=True,
        )

    assert report.drhp_id == "hyundai_2024_10"
    assert report.chunk_count > 0
    assert report.dry_run is True

    # Re-run the chunking step directly to inspect chunk-level drhp_id tagging.
    from pipelines.ingest import chunk_docling_json

    chunks = chunk_docling_json(_tiny_docling_doc(), drhp_id="hyundai_2024_10")
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.drhp_id == "hyundai_2024_10"
        assert chunk.drhp_id != "swiggy_2024_11"


def test_front_matter_pages_is_honored() -> None:
    """A doc ingested with front_matter_pages=12 produces printed labels
    consistent with a 12-page Roman front matter, not the 20-page default."""
    from pipelines.ingest import _infer_printed_label

    # Page index 11 (0-based) is the 12th page — still front matter at threshold=12.
    label_front_matter = _infer_printed_label(11, None, front_matter_pages=12)
    assert label_front_matter == "xii"

    # Page index 12 is the first body page when front_matter_pages=12.
    label_body = _infer_printed_label(12, None, front_matter_pages=12)
    assert label_body == "1"

    # The same page index 12 would still be front matter under the 20-page default.
    label_default = _infer_printed_label(12, None, front_matter_pages=20)
    assert label_default == "xiii"


def test_ingest_swiggy_shim_still_importable() -> None:
    """Importing pipelines.ingest_swiggy still works (shim) — Phase 1 imports
    (Section, chunk_sections, extract_sections_from_docling, CHUNK_ABSOLUTE_MIN)
    remain available."""
    import pipelines.ingest_swiggy as shim

    assert hasattr(shim, "Section")
    assert hasattr(shim, "chunk_sections")
    assert hasattr(shim, "extract_sections_from_docling")
    assert hasattr(shim, "CHUNK_ABSOLUTE_MIN")
    assert hasattr(shim, "DRHP_ID")
    assert shim.DRHP_ID == "swiggy_2024_11"


def test_no_module_level_hardcodes_used_inside_ingest_drhp() -> None:
    """ingest_drhp's source never references a module-level DRHP_ID / PDF_PATH /
    JSON_CACHE_PATH constant — drhp_id and pdf_path are parameters only."""
    from pipelines import ingest

    source = inspect.getsource(ingest.ingest_drhp)

    # These Swiggy-specific module-level names must never appear inside the
    # function body (they don't exist in pipelines/ingest.py at all).
    assert "DRHP_ID" not in source.replace("drhp_id", "")
    assert "PDF_PATH" not in source
    assert not hasattr(ingest, "DRHP_ID")
    assert not hasattr(ingest, "PDF_PATH")
    assert not hasattr(ingest, "JSON_CACHE_PATH")
