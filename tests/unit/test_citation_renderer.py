"""
Stub: ui/citation_chip.py — citation chip HTML renderer (UI-02).

Validates the renderer contract from SKELETON.md §F:
- Emits <sup class="drhp-cite" data-claim-id="..."> chips
- Includes aria-describedby for accessibility
- Deduplicates chips per-cluster (D-03): same claim_id referenced 3x → 1 chip
- XSS-attempt input in chunk_text is HTML-escaped before rendering (T-1-06 mitigation)

Wave 4 owns this implementation (UI-02; T-1-06 mitigation).
"""
from __future__ import annotations

import pytest

pytest.importorskip("ui.citation_chip", reason="ui/citation_chip.py ships in Wave 4")


@pytest.mark.xfail(reason="Wave 4 owns this — implements ui/citation_chip.py renderer", strict=False)
def test_renderer_emits_sup_chip_html_and_escapes_xss() -> None:
    """render_citation_chip(claim_id='c_abc123') must emit HTML matching
    '<sup class=\"drhp-cite\" data-claim-id=\"c_abc123\"...>' and must escape
    <script> tags in chunk_text to prevent XSS."""
    assert False, "Wave 4 must implement: call renderer, assert chip HTML and XSS escaping"
