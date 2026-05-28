"""
TDD Task 3 — ui/disclaimer.py Wave 4 additions.

Tests Wave 4 rendering functions (render_first_use_modal, render_persistent_footer,
render_per_answer_footer) and regression guards for Wave 1 exports.
"""
from __future__ import annotations

import inspect

import pytest

from compliance.disclaimer_text import ANCHOR_COPY, MODAL_CTA, MODAL_HEADING, PER_ANSWER_FOOTER
from compliance.scrubber import scrub


# ── Wave 1 exports preserved ──────────────────────────────────────────────────

def test_wave1_exports_preserved() -> None:
    """Wave 1 contract MUST NOT be broken."""
    from ui.disclaimer import DisclaimerSurface, render_disclaimer_gate  # noqa: F401


# ── render_persistent_footer ──────────────────────────────────────────────────

def test_render_persistent_footer_html_contains_anchor_copy_and_methodology_link() -> None:
    from ui.disclaimer import render_persistent_footer
    html = render_persistent_footer()

    assert ANCHOR_COPY in html, "ANCHOR_COPY must be present in footer HTML"
    assert "<a" in html, "Footer must contain an anchor tag"
    assert 'href="/methodology"' in html, "Footer must link to /methodology"
    assert "methodology" in html
    assert 'class="drhp-footer"' in html, "Footer must use CSS class (UI-SPEC FLAG-2)"
    assert 'class="drhp-footer-link"' in html
    # No inline style= per UI-SPEC FLAG-2
    assert 'style="' not in html, "No inline style= in footer (UI-SPEC FLAG-2)"


# ── render_per_answer_footer ──────────────────────────────────────────────────

def test_render_per_answer_footer_html_uses_class_not_inline_style() -> None:
    from ui.disclaimer import render_per_answer_footer
    html = render_per_answer_footer()

    assert 'class="drhp-disclaimer-per-answer"' in html
    assert PER_ANSWER_FOOTER in html
    # No inline style= per UI-SPEC FLAG-2 (Wave 1 inline-fallback removed in Wave 4)
    assert 'style="' not in html, "No inline style= in per-answer footer (UI-SPEC FLAG-2)"


# ── render_first_use_modal ────────────────────────────────────────────────────

def test_render_first_use_modal_data_shape() -> None:
    from ui.disclaimer import render_first_use_modal
    from compliance.disclaimer_text import MODAL_BODY_ADDENDUM
    data = render_first_use_modal()

    assert data["heading"] == MODAL_HEADING
    assert data["cta_text"] == MODAL_CTA
    assert "css_class" in data
    assert data["css_class"] == "drhp-modal"
    assert ANCHOR_COPY in data["body"]
    assert MODAL_BODY_ADDENDUM in data["body"]


def test_modal_body_contains_ai_disclosure() -> None:
    from ui.disclaimer import render_first_use_modal
    data = render_first_use_modal()
    assert "large language models" in data["body"], \
        "UI-SPEC L-11 / SEBI Jan-2025 RA AI-disclosure must be present"


# ── ANCHOR_COPY regression guard ──────────────────────────────────────────────

def test_anchor_copy_unchanged_from_wave1() -> None:
    """ANCHOR_COPY must match the D-07 locked string byte-for-byte."""
    expected = (
        "DRHPLens reads prospectuses for you. "
        "It cites what the document says and shows historical context. "
        "Decisions about investing are yours. "
        "This is not investment advice."
    )
    assert ANCHOR_COPY == expected, \
        f"ANCHOR_COPY has drifted from D-07 locked value:\n  got: {ANCHOR_COPY!r}"


# ── All three render functions pass scrubber ──────────────────────────────────

def test_all_three_render_functions_pass_scrubber() -> None:
    from ui.disclaimer import render_first_use_modal, render_per_answer_footer, render_persistent_footer

    for fn_name, fn in [
        ("render_persistent_footer", render_persistent_footer),
        ("render_per_answer_footer", render_per_answer_footer),
    ]:
        result = fn()
        assert isinstance(result, str)
        r = scrub(result)
        assert r.passed, f"{fn_name}() output failed scrubber: matched {r.match!r}"

    modal_data = render_first_use_modal()
    for key, value in modal_data.items():
        if isinstance(value, str):
            r = scrub(value)
            assert r.passed, f"render_first_use_modal()[{key!r}] failed scrubber: {r.match!r}"


# ── per-answer footer not imported inside refusal_banner ─────────────────────

def test_per_answer_footer_does_not_render_inside_refusal_banner() -> None:
    """UI-SPEC §Disclaimer Surfaces §3: per-answer footer must NOT be imported
    by refusal_banner (the banner has its own disclaimer baked in)."""
    import ui.refusal_banner
    source = inspect.getsource(ui.refusal_banner)
    assert "render_per_answer_footer" not in source, \
        "ui/refusal_banner.py must NOT import render_per_answer_footer"
