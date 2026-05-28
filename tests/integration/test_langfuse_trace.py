"""
Stub: integration test — Langfuse trace contains claim_ids through every node (cross-cutting invariant).

Validates that:
- Every agent run writes a Langfuse trace with >= 1 span per node
- claim_ids are propagated through intake → retrieve → generate → cite_check → emit spans
- The trace shape matches the Phase 3 METHOD-01 consumer contract (SKELETON.md §B)

Wave 5 owns this implementation (Langfuse wiring; requires --run-langfuse flag).
"""
from __future__ import annotations

import pytest

pytest.importorskip("langfuse", reason="langfuse trace wiring ships in Wave 5")


@pytest.mark.xfail(reason="Wave 5 owns this — wires Langfuse CallbackHandler and validates trace shape", strict=False)
def test_every_node_writes_a_span_with_claim_ids() -> None:
    """Running the agent with Langfuse enabled must produce a trace where
    the cite_check span carries per-claim results with claim_ids."""
    assert False, "Wave 5 must implement: run agent with Langfuse mock, assert trace spans and claim_ids"
