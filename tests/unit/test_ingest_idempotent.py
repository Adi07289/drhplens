"""
Unit test — re-ingest deletes existing points by drhp_id filter first.

Requirement: INGEST (reuse). Threat: none (data-integrity correctness concern,
not a STRIDE security threat).
Secure behavior: re-ingest deletes existing points filtered by drhp_id before
upserting — no duplicate points accumulate in Qdrant (T-02-A6).

Wave 2 implements (02-VALIDATION.md row "2-ingest-idempotent").
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_delete_by_drhp_id_issues_filter_condition() -> None:
    """delete_by_drhp_id() issues a Qdrant delete with a drhp_id FieldCondition
    filter (assert via monkeypatched client capturing the filter)."""
    from qdrant_client.http import models as rest

    from storage import vector

    mock_client = MagicMock()

    with patch("storage.vector.client", return_value=mock_client), patch(
        "storage.vector.ensure_collection"
    ):
        vector.delete_by_drhp_id("swiggy_2024_11")

    mock_client.delete.assert_called_once()
    call_kwargs = mock_client.delete.call_args.kwargs
    assert call_kwargs["collection_name"] == vector.COLLECTION_NAME

    points_selector = call_kwargs["points_selector"]
    assert isinstance(points_selector, rest.FilterSelector)
    must_conditions = points_selector.filter.must
    assert len(must_conditions) == 1
    condition = must_conditions[0]
    assert condition.key == "drhp_id"
    assert condition.match.value == "swiggy_2024_11"


def test_ingest_drhp_calls_delete_before_upsert(tmp_path: Path) -> None:
    """ingest_drhp calls delete_by_drhp_id(drhp_id) before upsert_chunks
    (ordering asserted via a call recorder) so re-ingest cannot duplicate
    points (A6)."""
    from pipelines.ingest import ingest_drhp

    pdf_path = tmp_path / "swiggy.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    cache_path = tmp_path / "swiggy.docling.json"

    call_order: list[str] = []

    section_names = [
        "RISK FACTORS", "OUR BUSINESS", "OBJECTS OF THE ISSUE", "OUR PROMOTERS",
        "CAPITAL STRUCTURE", "RESTATED FINANCIAL STATEMENTS", "GENERAL INFORMATION",
        "THE ISSUE", "INDUSTRY OVERVIEW", "OUTSTANDING LITIGATION", "MANAGEMENT",
    ]
    body_children = []
    for i, name in enumerate(section_names):
        body_children.append({"label": "section_header", "text": name, "prov": [{"page_no": i + 1}]})
        body_children.append(
            {"label": "text", "text": f"Body text for {name}. " * 5, "prov": [{"page_no": i + 1}]}
        )
    doc_dict = {"body": {"children": body_children}}

    def _fake_delete(drhp_id: str) -> None:
        call_order.append("delete")

    def _fake_upsert(chunks, vectors) -> None:
        call_order.append("upsert")

    with patch("pipelines.ingest.load_or_parse_drhp", return_value=doc_dict), patch(
        "pipelines.ingest.embed_chunks", return_value=[[0.1] * 1024] * 50
    ), patch("storage.vector.delete_by_drhp_id", side_effect=_fake_delete) as mock_delete, patch(
        "storage.vector.upsert_chunks", side_effect=_fake_upsert
    ) as mock_upsert, patch("storage.vector.ensure_collection"):
        ingest_drhp(
            drhp_id="swiggy_2024_11",
            pdf_path=pdf_path,
            json_cache_path=cache_path,
            dry_run=False,
        )

    mock_delete.assert_called_once_with("swiggy_2024_11")
    mock_upsert.assert_called_once()
    assert call_order == ["delete", "upsert"], (
        f"Expected delete before upsert, got order: {call_order}"
    )


def test_dry_run_does_not_call_delete_or_upsert(tmp_path: Path) -> None:
    """dry_run=True skips the Qdrant delete+upsert step entirely (no live
    Qdrant access needed for unit tests)."""
    from pipelines.ingest import ingest_drhp

    pdf_path = tmp_path / "swiggy.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    cache_path = tmp_path / "swiggy.docling.json"

    section_names = [
        "RISK FACTORS", "OUR BUSINESS", "OBJECTS OF THE ISSUE", "OUR PROMOTERS",
        "CAPITAL STRUCTURE", "RESTATED FINANCIAL STATEMENTS", "GENERAL INFORMATION",
        "THE ISSUE", "INDUSTRY OVERVIEW", "OUTSTANDING LITIGATION", "MANAGEMENT",
    ]
    body_children = []
    for i, name in enumerate(section_names):
        body_children.append({"label": "section_header", "text": name, "prov": [{"page_no": i + 1}]})
        body_children.append(
            {"label": "text", "text": f"Body text for {name}. " * 5, "prov": [{"page_no": i + 1}]}
        )
    doc_dict = {"body": {"children": body_children}}

    with patch("pipelines.ingest.load_or_parse_drhp", return_value=doc_dict), patch(
        "storage.vector.delete_by_drhp_id"
    ) as mock_delete, patch("storage.vector.upsert_chunks") as mock_upsert:
        report = ingest_drhp(
            drhp_id="swiggy_2024_11",
            pdf_path=pdf_path,
            json_cache_path=cache_path,
            dry_run=True,
        )

    mock_delete.assert_not_called()
    mock_upsert.assert_not_called()
    assert report.dry_run is True
