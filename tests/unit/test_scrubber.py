"""
Stub: compliance/banned_tokens.py — banned-token scrubber.

Validates that every banned token and its morphological variants (subscribe/subscribed/
subscribing, recommend/recommended/recommending, etc.) trigger a hard block.

Wave 1 owns this implementation (TRUST-02; threat T-1-01 mitigation).
"""
from __future__ import annotations

import pytest

pytest.importorskip("compliance.banned_tokens", reason="compliance/banned_tokens.py ships in Wave 1")


@pytest.mark.xfail(reason="Wave 1 owns this — implements compliance/banned_tokens.py", strict=False)
def test_every_banned_token_conjugation_blocked() -> None:
    """Every banned token conjugation (subscribe/subscribed/subscribing, recommend/recommended, etc.)
    must trigger the scrubber hard block."""
    assert False, "Wave 1 must implement: assert scrubber.is_banned(text) for each conjugation"
