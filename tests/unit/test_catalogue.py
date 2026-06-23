"""
Unit test stub — data/catalogue.json loads + validates against schema (no threat).

Requirement: SNAP-01, OPS-01. Threat: none (trusted repo config; see threat
register T-02-01 in 02-01-PLAN.md — accept, PR-reviewed).
Secure behavior: catalogue.json loads + validates against schema; all entries
have required fields.

Wave 0 stub — Wave 1 implements (02-VALIDATION.md row "2-catalogue-loader").
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Wave 1 — not yet implemented", strict=False)
def test_catalogue_loads_and_validates_schema() -> None:
    raise NotImplementedError
