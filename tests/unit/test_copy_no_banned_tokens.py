"""
Stub: ui/copy.py — user-visible copy strings must pass the banned-token scrubber (TRUST-03).

Validates that no string in ui/copy.py contains a banned token.
This prevents DRHPLens's own UI copy from violating the SEBI compliance posture it enforces
on LLM output — the scrubber applies to both.

Wave 4 owns this implementation (TRUST-03; defends against internal copy violations).
"""
from __future__ import annotations

import pytest

pytest.importorskip("ui.copy", reason="ui/copy.py ships in Wave 4")


@pytest.mark.xfail(reason="Wave 4 owns this — implements ui/copy.py and validates against scrubber", strict=False)
def test_every_copy_string_passes_scrubber() -> None:
    """Every string constant in ui/copy.py must pass the banned-token scrubber.
    No UI copy may contain subscribe, recommend, buy, sell, target, etc."""
    assert False, "Wave 4 must implement: import all copy strings, run each through scrubber, assert none blocked"
