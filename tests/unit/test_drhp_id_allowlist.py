"""
Unit test stub — drhp_id validated against catalogue allow-list (V5).

Requirement: SNAP-01. Threat: V5 (input validation — an unknown/unvalidated
drhp_id from session/query-param must never reach the Qdrant filter).
Secure behavior: drhp_id is validated against catalogue.json keys before
reaching search(); unknown ids are rejected.

Wave 0 stub — Wave 1 implements (02-VALIDATION.md row "2-drhp_id-allowlist").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 1 — not yet implemented", strict=False)
def test_unknown_drhp_id_rejected_by_allowlist() -> None:
    raise NotImplementedError
