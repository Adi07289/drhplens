"""
Integration test stub — ingest a 2nd IPO end-to-end + pre-compute its snapshot;
retrieval scoped to that drhp_id (T-2-DRHP).

Requirement: INGEST + SNAP. Threat: T-2-DRHP (multi-IPO retrieval must stay
scoped to the requested drhp_id; no cross-IPO leakage).
Secure behavior: ingesting a 2nd IPO end-to-end produces chunks searchable
only under that IPO's drhp_id; its snapshot pre-computes 6 fields.

Wave 0 stub — Wave 5 implements (02-VALIDATION.md row "2-2nd-ipo-e2e").
Gated the same way Phase 1 gates tests/integration/test_qdrant_ingest.py:
xfail(run=False) until a live Qdrant instance is available.
"""
from __future__ import annotations

import pytest

pytest.importorskip("qdrant_client", reason="qdrant-client ships in Wave 2 environment")


@pytest.mark.integration
@pytest.mark.xfail(
    run=False,
    reason="Wave 5 — xfail until live Qdrant; ingest a 2nd IPO end-to-end (02-VALIDATION.md 2-2nd-ipo-e2e)",
    strict=False,
)
def test_second_ipo_ingest_and_snapshot_e2e() -> None:
    raise NotImplementedError
