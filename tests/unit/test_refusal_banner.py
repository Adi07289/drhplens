"""
TDD Task 3 — ui/refusal_banner.py

Tests the refusal banner renderer (amber-not-red, aria-live, XSS escape,
chip cap at 2, banned-token policy, per-answer disclaimer baked in).
"""
from __future__ import annotations

import pytest

from agent.schemas import RefusalResponse
from ui.refusal_banner import (
    MAX_CHIPS_RENDERED,
    REFUSAL_HEADING_BANNED_TOKEN,
    REFUSAL_HEADING_INFRASTRUCTURE,
    REFUSAL_HEADING_LOW_RETRIEVAL,
    REFUSAL_HEADING_PARTIAL_GROUNDING,
    render_refusal_banner,
)


def _refusal(reason: str, message: str, suggestions: list[str] | None = None) -> RefusalResponse:
    return RefusalResponse(
        reason=reason,
        explanation=message,
        reformulation_suggestions=suggestions or [],
    )


# ── low_retrieval_score ───────────────────────────────────────────────────────

def test_render_refusal_banner_low_retrieval() -> None:
    refusal = _refusal(
        "low_retrieval_score",
        "This DRHP does not address Mars colonization. Try asking about Swiggy.",
        ["What is the issue size?", "Who are the promoters?"],
    )
    html = render_refusal_banner(refusal)

    assert 'class="drhp-refusal"' in html
    # heading is HTML-escaped; check escaped form
    import html as _html
    assert _html.escape(REFUSAL_HEADING_LOW_RETRIEVAL) in html
    assert "Mars colonization" in html
    assert html.count('class="drhp-suggest"') == 2, "Two suggestion chips expected"


# ── partial_grounding (unsupported_claim with 'addresses parts of') ───────────

def test_render_refusal_banner_partial_grounding() -> None:
    import html as _html
    refusal = _refusal(
        "unsupported_claim",
        "The DRHP addresses parts of your question about financials.",
    )
    output = render_refusal_banner(refusal)
    assert _html.escape(REFUSAL_HEADING_PARTIAL_GROUNDING) in output


# ── banned_token → zero chips ─────────────────────────────────────────────────

def test_render_refusal_banner_banned_token() -> None:
    """banned_token: NO chips even with non-empty suggestions."""
    refusal = _refusal(
        "banned_token",
        "Couldn't return that answer because it implied advice.",
        ["What are the risk factors?"],
    )
    import html as _html
    html = render_refusal_banner(refusal)

    assert _html.escape(REFUSAL_HEADING_BANNED_TOKEN) in html
    assert 'class="drhp-suggest"' not in html, \
        "No suggestion chips for banned_token refusal (UI-SPEC anti-pattern)"


# ── caps at 2 suggestions ─────────────────────────────────────────────────────

def test_render_refusal_banner_caps_at_two_suggestions() -> None:
    """UI policy: max 2 chips regardless of how many suggestions the schema provides."""
    refusal = _refusal(
        "low_retrieval_score",
        "Not in the DRHP.",
        ["a", "b", "c"],
    )
    html = render_refusal_banner(refusal)

    chip_count = html.count('class="drhp-suggest"')
    assert chip_count == MAX_CHIPS_RENDERED, \
        f"Expected {MAX_CHIPS_RENDERED} chips, got {chip_count}"


# ── XSS escape ───────────────────────────────────────────────────────────────

def test_render_refusal_banner_escapes_xss_in_message_and_suggestions() -> None:
    refusal = _refusal(
        "low_retrieval_score",
        "<script>alert(1)</script>",
        ["<img onerror=alert(1)>"],
    )
    html = render_refusal_banner(refusal)

    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    assert "&lt;img onerror=alert(1)&gt;" in html
    assert "<img onerror" not in html


# ── aria-live ─────────────────────────────────────────────────────────────────

def test_refusal_banner_includes_aria_live_polite() -> None:
    refusal = _refusal("low_retrieval_score", "Not in the DRHP.")
    html = render_refusal_banner(refusal)
    assert 'aria-live="polite"' in html


# ── per-answer disclaimer baked in ───────────────────────────────────────────

def test_refusal_banner_includes_per_answer_disclaimer() -> None:
    refusal = _refusal("low_retrieval_score", "Not in the DRHP.")
    html = render_refusal_banner(refusal)
    assert "Informational only" in html
    assert "not advice" in html
