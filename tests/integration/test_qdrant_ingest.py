"""
Stub: integration test — Swiggy DRHP ingestion upserts to Qdrant (INGEST-03).

Validates the full ingest pipeline end-to-end:
- Chunks are upserted to Qdrant (in-memory mock for CI)
- Collection contains 1500-2500 points for drhp_id=swiggy_2024_11
- Each point payload has: drhp_id, section, page_start, page_end, chunk_text

Wave 2 owns this implementation (INGEST-03; storage bus write leg).
"""
from __future__ import annotations

import pytest

pytest.importorskip("qdrant_client", reason="qdrant-client ships in Wave 2 environment")


@pytest.mark.xfail(reason="Wave 2 owns this — runs ingest pipeline against in-memory Qdrant", strict=False)
def test_swiggy_ingest_upserts_to_qdrant(mock_qdrant_client) -> None:
    """Running ingest_swiggy.py against the committed PDF must produce 1500-2500 chunks
    in the drhp_chunks collection with correct payload schema."""
    assert False, "Wave 2 must implement: run ingest, query mock_qdrant_client, assert chunk count and payload"
