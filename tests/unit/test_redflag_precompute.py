"""
Unit test stub — the red-flag precompute loop runs the 7 canned queries through
GRAPH and stores a RedFlagField per key; a not-disclosed result becomes a
RefusalResponse (D3-03).

Requirement: EXTRACT-01. Wave 0 stub — Plan 03 implements pipelines/redflag.py.
Function names are LOCKED; Plan 03 fills the bodies.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Plan 03 implements pipelines/redflag.py")


def test_seven_field_loop_monkeypatched() -> None:
    """With GRAPH.invoke monkeypatched, the precompute loop produces a
    RedFlagField for each of the 7 REDFLAG_QUERIES keys."""
    raise NotImplementedError


def test_not_disclosed_becomes_refusal() -> None:
    """A field with no grounded answer is stored as a RefusalResponse value
    (Not disclosed in DRHP), with confidence_tier None."""
    raise NotImplementedError
