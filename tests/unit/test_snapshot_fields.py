"""
Unit test stub — 6 field blocks computed via agent; "not disclosed" stored
honestly when DRHP silent (esp. SNAP-07 pledging) (no threat).

Requirement: SNAP-02..07. Threat: none (honesty-first correctness invariant,
not a STRIDE threat).
Secure behavior: each of the 6 snapshot field blocks is computed via the
existing agent pipeline; when the DRHP is silent on a field, a RefusalResponse
is stored instead of a fabricated GroundedAnswer.

Wave 0 stub — Wave 3 implements (02-VALIDATION.md row "2-snapshot-fields").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 3 — not yet implemented", strict=False)
def test_snapshot_field_stores_refusal_when_drhp_silent() -> None:
    raise NotImplementedError
