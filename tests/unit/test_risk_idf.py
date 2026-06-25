"""
Unit test stub — in-corpus IDF risk specificity (P12 / D3-14): issuer-specific
risks rank above boilerplate; the hand-curated boilerplate floor clamps a
matching phrase to the bottom band regardless of IDF.

Requirement: P12 mitigation. Wave 0 stub — Plan 03 implements pipelines/risk_idf.py.
Function names are LOCKED; Plan 03 fills the bodies (the idf_corpus_3doc fixture
in tests/eval/conftest.py is the input corpus).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Plan 03 implements pipelines/risk_idf.py")


def test_issuer_specific_ranks_above_boilerplate() -> None:
    """A risk with unique (high-IDF) terms ranks above a shared-boilerplate risk."""
    raise NotImplementedError


def test_boilerplate_floor_clamps() -> None:
    """A risk matching a boilerplate-floor phrase (token_set_ratio >=
    IDF_BOILERPLATE_FUZZ_THRESHOLD) clamps to the industry_standard band."""
    raise NotImplementedError
