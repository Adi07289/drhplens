"""
Unit test stub — data/snapshots/<drhp_id>.json round-trips; carries claim_ids;
scrubber-clean (no threat for the round-trip; tampering threat covered by
T-02-01-adjacent posture — committed JSON is trusted config).

Requirement: SNAP-02..07. Threat: none directly (snapshot-cache poisoning is
mitigated by the existing scrubber + cite-check at pre-compute time, per
02-RESEARCH.md Security Domain table).
Secure behavior: data/snapshots/<drhp_id>.json round-trips a serialized
GroundedAnswer/RefusalResponse losslessly; carries claim_ids; scrubber-clean.

Wave 0 stub — Wave 3 implements (02-VALIDATION.md row "2-snapshot-cache-rw").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 3 — not yet implemented", strict=False)
def test_snapshot_cache_round_trips_grounded_answer() -> None:
    raise NotImplementedError
