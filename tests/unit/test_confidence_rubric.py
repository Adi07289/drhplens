"""
Unit test stub — the deterministic confidence rubric (D3-01): verbatim -> high,
light parse/aggregation -> medium, cross-section inference -> low, absence ->
no tier.

Requirement: EXTRACT-02. Wave 0 stub — Plan 02 implements pipelines/confidence.py
(classify_confidence). Function names are LOCKED; Plan 02 fills the bodies.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Plan 02 implements pipelines/confidence.py")


def test_verbatim_is_high() -> None:
    """A value stated verbatim in the cited span classifies as high."""
    raise NotImplementedError


def test_light_parse_is_medium() -> None:
    """A value that is a numeric transformation of source numbers (e.g. a ratio)
    classifies as medium."""
    raise NotImplementedError


def test_cross_section_is_low() -> None:
    """Support spanning multiple sources with different .section values
    classifies as low."""
    raise NotImplementedError


def test_absence_has_no_tier() -> None:
    """A not-disclosed (RefusalResponse) field carries no confidence tier (D3-03)."""
    raise NotImplementedError
