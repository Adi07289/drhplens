"""
Stub: ui/disclaimer.py — DisclaimerSurface three render surfaces.

Validates that the DisclaimerSurface abstraction renders all three required surfaces
(first-use modal, persistent footer, per-answer footer) with the anchor copy from
compliance/disclaimer_text.py and at >= SEBI 10pt font-size floor.

Wave 1 owns this implementation (TRUST-01, TRUST-03; D-08 three-surface requirement).
"""
from __future__ import annotations

import pytest

pytest.importorskip("ui.disclaimer", reason="ui/disclaimer.py ships in Wave 1")


@pytest.mark.xfail(reason="Wave 1 owns this — implements ui/disclaimer.py + DisclaimerSurface", strict=False)
def test_three_surfaces_render_anchor_copy() -> None:
    """render_modal(), render_footer(), render_per_answer() must all return non-empty HTML
    containing the anchor copy from compliance/disclaimer_text.py."""
    assert False, "Wave 1 must implement: assert anchor copy in each surface render output"
