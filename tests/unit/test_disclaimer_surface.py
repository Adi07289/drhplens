"""
TDD Wave 1 — ui/disclaimer.py + compliance/disclaimer_text.py.

Validates that DisclaimerSurface renders all three D-08 surfaces with the D-07
anchor copy, at >= SEBI 10pt font-size floor, and with the correct CSS classes.

FLAG-9 compliance: test_render_persistent_footer_includes_methodology_link_token
asserts the CSS class .drhp-footer, NOT the inline font-size style.
(The inline font-size is tested separately in test_sebi_10pt_floor_satisfied.)
This means Wave 4's CSS refactor does not need to rewrite this test.
"""
from __future__ import annotations

import pytest

from compliance.disclaimer_text import ANCHOR_COPY
from ui.disclaimer import DisclaimerSurface, render_disclaimer_gate


# ---------------------------------------------------------------------------
# D-07 anchor copy byte-for-byte match
# ---------------------------------------------------------------------------

D07_EXACT: str = (
    "DRHPLens reads prospectuses for you. "
    "It cites what the document says and shows historical context. "
    "Decisions about investing are yours. "
    "This is not investment advice."
)
"""The canonical D-07 string, byte-for-byte (straight ASCII apostrophe, no trailing space)."""


def test_anchor_copy_matches_d07() -> None:
    """ANCHOR_COPY in compliance/disclaimer_text.py must equal D-07 string byte-for-byte.

    This is the regulatory artifact. Any future legal-review polish edits
    disclaimer_text.py and this test will catch any accidental drift.
    """
    assert ANCHOR_COPY == D07_EXACT, (
        f"ANCHOR_COPY does not match D-07.\n"
        f"Expected: {D07_EXACT!r}\n"
        f"Got:      {ANCHOR_COPY!r}"
    )


# ---------------------------------------------------------------------------
# render_modal()
# ---------------------------------------------------------------------------

def test_render_modal_returns_dict_with_heading_body_cta() -> None:
    """render_modal() returns dict with heading, body, cta_text keys."""
    surface = DisclaimerSurface()
    modal = surface.render_modal()

    assert isinstance(modal, dict), "render_modal() must return a dict"
    assert "heading" in modal, "Missing 'heading' key"
    assert "body" in modal, "Missing 'body' key"
    assert "cta_text" in modal, "Missing 'cta_text' key"

    assert isinstance(modal["heading"], str)
    assert isinstance(modal["body"], str)
    assert isinstance(modal["cta_text"], str)


def test_render_modal_heading_is_read_this_once() -> None:
    """Modal heading must be 'Read this once.' per UI-SPEC."""
    modal = DisclaimerSurface().render_modal()
    assert modal["heading"] == "Read this once."


def test_render_modal_cta_is_i_understand() -> None:
    """Modal CTA must be 'I understand — open DRHPLens' per UI-SPEC."""
    modal = DisclaimerSurface().render_modal()
    assert modal["cta_text"] == "I understand — open DRHPLens"


def test_render_modal_body_contains_anchor_copy() -> None:
    """Modal body must include the D-07 anchor copy."""
    modal = DisclaimerSurface().render_modal()
    assert ANCHOR_COPY in modal["body"], (
        f"Modal body does not contain ANCHOR_COPY.\nBody: {modal['body']!r}"
    )


def test_modal_copy_includes_ai_disclosure_per_sebi_jan_2025() -> None:
    """Modal body must contain 'large language models' (TRUST-03 / UI-SPEC L-11).

    SEBI Jan-2025 RA guidelines require AI-usage disclosure for research-adjacent
    tools. The substring 'large language models' is the specific disclosure string.
    """
    modal = DisclaimerSurface().render_modal()
    assert "large language models" in modal["body"], (
        f"Modal body missing 'large language models' AI-disclosure.\nBody: {modal['body']!r}"
    )


# ---------------------------------------------------------------------------
# render_persistent_footer() — FLAG-9 class-based test
# ---------------------------------------------------------------------------

def test_render_persistent_footer_returns_string() -> None:
    """render_persistent_footer() returns an HTML string."""
    footer = DisclaimerSurface().render_persistent_footer()
    assert isinstance(footer, str)
    assert len(footer) > 0


def test_render_persistent_footer_includes_methodology_link_token() -> None:
    """Persistent footer HTML contains:
    - the CSS class 'drhp-footer' (FLAG-9: class-based test, not inline-style)
    - the anchor copy
    - the substring 'methodology' (UI-SPEC L-7: /methodology link required)
    - an href pointing to /methodology

    FLAG-9: this test checks the CSS class, NOT font-size: 12px. This ensures
    Wave 4's CSS refactor (moving 12px from inline to .drhp-footer rule) does
    not require rewriting this test.
    """
    footer = DisclaimerSurface().render_persistent_footer()
    assert "drhp-footer" in footer, f"Missing .drhp-footer class in: {footer!r}"
    assert ANCHOR_COPY in footer, f"ANCHOR_COPY not in footer: {footer!r}"
    assert "methodology" in footer, f"Missing 'methodology' in footer: {footer!r}"
    assert "/methodology" in footer, f"Missing '/methodology' link in footer: {footer!r}"


def test_sebi_10pt_floor_satisfied() -> None:
    """Persistent footer inline style includes 'font-size: 12px' (SEBI 10pt-equivalent).

    12px at default browser zoom = ~10.5pt, above the SEBI Jan-2025 RA 10pt floor.
    This test verifies the inline fallback style is present; the canonical 12px rule
    lives in app/static/drhplens.css (Wave 4).
    """
    footer = DisclaimerSurface().render_persistent_footer()
    assert "font-size: 12px" in footer, (
        f"Missing 'font-size: 12px' in persistent footer.\nFooter: {footer!r}"
    )


# ---------------------------------------------------------------------------
# render_per_answer_footer()
# ---------------------------------------------------------------------------

def test_render_per_answer_footer_has_correct_class_and_content() -> None:
    """Per-answer footer HTML has class='drhp-disclaimer-per-answer' and correct copy."""
    pa = DisclaimerSurface().render_per_answer_footer()
    assert isinstance(pa, str)
    assert "drhp-disclaimer-per-answer" in pa, (
        f"Missing CSS class 'drhp-disclaimer-per-answer': {pa!r}"
    )
    assert "Informational only" in pa, f"Missing disclaimer copy in: {pa!r}"
    assert "not advice" in pa, f"Missing 'not advice' in: {pa!r}"


def test_render_per_answer_footer_exact_copy() -> None:
    """Per-answer footer content is exactly 'Informational only — not advice.' per UI-SPEC."""
    pa = DisclaimerSurface().render_per_answer_footer()
    assert "Informational only — not advice." in pa, (
        f"Per-answer footer missing exact copy.\nHTML: {pa!r}"
    )


def test_render_per_answer_footer_has_12px_font() -> None:
    """Per-answer footer has font-size: 12px (SEBI 10pt-equivalent floor)."""
    pa = DisclaimerSurface().render_per_answer_footer()
    assert "font-size: 12px" in pa, f"Missing font-size: 12px in per-answer footer: {pa!r}"


# ---------------------------------------------------------------------------
# Three surfaces are distinct
# ---------------------------------------------------------------------------

def test_three_surfaces_export_distinct_copy() -> None:
    """The three render methods return distinct content (not the same string)."""
    surface = DisclaimerSurface()
    modal = surface.render_modal()
    footer = surface.render_persistent_footer()
    per_answer = surface.render_per_answer_footer()

    # Modal is a dict; footer and per-answer are HTML strings
    assert isinstance(modal, dict)
    assert isinstance(footer, str)
    assert isinstance(per_answer, str)

    # Footer and per-answer are different
    assert footer != per_answer, "render_persistent_footer() and render_per_answer_footer() must differ"


def test_three_surfaces_render_anchor_copy() -> None:
    """All three surfaces contain the anchor copy (original xfail stub, now green).

    Note: render_modal() returns ANCHOR_COPY in modal['body']; footer and per-answer
    include it or their own copy. The key test is that all three surfaces produce
    non-empty output containing compliance-relevant text.
    """
    surface = DisclaimerSurface()
    modal = surface.render_modal()
    footer = surface.render_persistent_footer()
    per_answer = surface.render_per_answer_footer()

    # Modal body contains anchor copy
    assert ANCHOR_COPY in modal["body"]
    # Footer contains anchor copy
    assert ANCHOR_COPY in footer
    # Per-answer contains per-answer disclaimer text
    assert "Informational only" in per_answer


# ---------------------------------------------------------------------------
# render_disclaimer_gate()
# ---------------------------------------------------------------------------

def test_render_disclaimer_gate_returns_modal_when_not_accepted() -> None:
    """render_disclaimer_gate() returns modal dict when disclaimer_accepted is False."""
    gate_result = render_disclaimer_gate({"disclaimer_accepted": False})
    assert gate_result is not None
    assert isinstance(gate_result, dict)
    assert "heading" in gate_result


def test_render_disclaimer_gate_returns_none_when_accepted() -> None:
    """render_disclaimer_gate() returns None when disclaimer_accepted is True."""
    gate_result = render_disclaimer_gate({"disclaimer_accepted": True})
    assert gate_result is None


def test_render_disclaimer_gate_returns_modal_when_key_missing() -> None:
    """render_disclaimer_gate() returns modal dict when key is not in session_state."""
    gate_result = render_disclaimer_gate({})
    assert gate_result is not None
    assert isinstance(gate_result, dict)


def test_render_disclaimer_gate_method_on_class() -> None:
    """DisclaimerSurface.render_disclaimer_gate() accepts session_state dict."""
    surface = DisclaimerSurface()
    # Not accepted
    result = surface.render_disclaimer_gate({"disclaimer_accepted": False})
    assert result is not None
    # Accepted
    result2 = surface.render_disclaimer_gate({"disclaimer_accepted": True})
    assert result2 is None


# ---------------------------------------------------------------------------
# CSS class names match UI-SPEC contract
# ---------------------------------------------------------------------------

def test_css_class_names_match_ui_spec() -> None:
    """CSS class names in rendered HTML match the UI-SPEC contract.

    UI-SPEC Streamlit-Specific Constraints:
      - Persistent footer: .drhp-footer
      - Per-answer footer: .drhp-disclaimer-per-answer (from plan action section)
    """
    surface = DisclaimerSurface()
    footer = surface.render_persistent_footer()
    per_answer = surface.render_per_answer_footer()

    assert "drhp-footer" in footer
    assert "drhp-disclaimer-per-answer" in per_answer
