"""
Unit test stub — drhp_id threads through GraphState -> retrieve -> search (V5).

Requirement: SNAP-01. Threat: V5 (input validation — drhp_id must reach search()
as a validated value, not bypass the catalogue allow-list).
Secure behavior: drhp_id flows through GraphState -> retrieve -> search; the
intake node's default preserves Phase 1 behavior when drhp_id is absent.

Wave 0 stub — Wave 1 implements (02-VALIDATION.md row "2-drhp_id-thread").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 1 — not yet implemented", strict=False)
def test_drhp_id_threads_through_graph_state_to_search() -> None:
    raise NotImplementedError
