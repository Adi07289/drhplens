"""
Stub: agent/schemas.py — claim_id Pydantic schema contract.

Validates that the GroundedAnswer / Claim / RetrievedChunkRef schemas enforce
the claim_id pattern and reject malformed input.

Wave 1 owns this implementation (schema contract for Phase 3 METHOD-01).
"""
from __future__ import annotations

import pytest

pytest.importorskip("agent.schemas", reason="agent/schemas.py ships in Wave 1")


@pytest.mark.xfail(reason="Wave 1 owns this — implements agent/schemas.py", strict=False)
def test_claim_id_pattern_enforced() -> None:
    """claim_id must match r'^c_[a-z0-9]{6,16}$'; schema must reject invalid patterns."""
    assert False, "Wave 1 must implement: validate claim_id regex via Pydantic v2 model"
