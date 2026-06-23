"""
Unit test stub — re-ingest deletes existing points by drhp_id filter first (no threat).

Requirement: INGEST (reuse). Threat: none (data-integrity correctness concern,
not a STRIDE security threat).
Secure behavior: re-ingest deletes existing points filtered by drhp_id before
upserting — no duplicate points accumulate in Qdrant.

Wave 0 stub — Wave 2 implements (02-VALIDATION.md row "2-ingest-idempotent").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 2 — not yet implemented", strict=False)
def test_reingest_deletes_existing_points_before_upsert() -> None:
    raise NotImplementedError
