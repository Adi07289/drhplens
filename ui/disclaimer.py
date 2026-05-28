"""
DisclaimerSurface abstraction — three D-08 surfaces from one source of truth.

No Streamlit imports at module level. Wave 4 (app.py) wraps each render method's
output in st.markdown(..., unsafe_allow_html=True) or st.dialog as appropriate.

Three surfaces (D-08 requirement):
  1. render_modal()              → dict for first-use st.dialog
  2. render_persistent_footer()  → HTML string, sticky footer
  3. render_per_answer_footer()  → HTML string, per-answer disclaimer

render_disclaimer_gate(session_state) is a pure-Python gate function. Wave 4
wraps it with the st.dialog decorator when wiring into app.py.

TRUST-03 compliance:
  - Persistent footer HTML includes font-size: 12px (≈ 10.5pt — SEBI 10pt floor)
  - Modal body contains "large language models" (SEBI Jan-2025 RA AI-disclosure)
  - Both footer surfaces use class="drhp-footer" and class="drhp-disclaimer-per-answer"
    so the app/static/drhplens.css file can apply the canonical 12px rule (Wave 4).
    The inline font-size is a fallback in case CSS is not loaded.

FLAG-9 compliance:
  The CSS class .drhp-footer is present in render_persistent_footer() output.
  Tests assert class presence, not just the inline style, so Wave 4's CSS refactor
  does not need to rewrite these tests.
"""
from __future__ import annotations

from compliance.disclaimer_text import (
    ANCHOR_COPY,
    MODAL_BODY_ADDENDUM,
    MODAL_CTA,
    MODAL_HEADING,
    PER_ANSWER_FOOTER,
)


class DisclaimerSurface:
    """Renders the three D-08 disclaimer surfaces from the canonical copy constants.

    All render methods return pure Python data (dict or str) with no Streamlit calls.
    This keeps the compliance layer testable without a Streamlit runtime.

    Wave 4 usage:
        surface = DisclaimerSurface()
        modal_data = surface.render_modal()
        st.dialog(modal_data["heading"])(lambda: (
            st.write(modal_data["body"]),
            st.button(modal_data["cta_text"])
        ))
    """

    def render_modal(self) -> dict:
        """Return the first-use modal content as a plain dict.

        Returns:
            {
                "heading": str,  — "Read this once." (Heading 20px/600 in UI)
                "body":    str,  — ANCHOR_COPY + " " + MODAL_BODY_ADDENDUM
                "cta_text": str, — "I understand — open DRHPLens"
            }

        The body string contains "large language models" per SEBI Jan-2025 RA
        AI-disclosure requirement (TRUST-03 / UI-SPEC L-11).
        """
        return {
            "heading": MODAL_HEADING,
            "body": ANCHOR_COPY + " " + MODAL_BODY_ADDENDUM,
            "cta_text": MODAL_CTA,
        }

    def render_persistent_footer(self) -> str:
        """Return the persistent slim footer as an HTML string.

        Returns an HTML <div> with:
          - class="drhp-footer" (FLAG-9: test asserts this class, not inline style)
          - Inline font-size: 12px as a fallback for environments without CSS
            (12px ≈ 10.5pt — satisfies SEBI 10pt-equivalent floor, TRUST-03)
          - ANCHOR_COPY text
          - An <a href="/methodology"> link with the "methodology" word
            (UI-SPEC L-7: /methodology stub link must be present in footer)

        Wave 4 injects app/static/drhplens.css which contains the canonical
        .drhp-footer rules at 12px / color: #475569. The inline style is a
        fallback only.
        """
        return (
            '<div class="drhp-footer" style="font-size: 12px; color: #475569;">'
            f"{ANCHOR_COPY}"
            '<a class="drhp-footer-link" href="/methodology"> · methodology</a>'
            "</div>"
        )

    def render_per_answer_footer(self) -> str:
        """Return the per-answer disclaimer as an HTML string.

        Returns an HTML <div> with:
          - class="drhp-disclaimer-per-answer"
          - Inline font-size: 12px italic (Small italic per UI-SPEC typography)
          - Content: "Informational only — not advice." (exact UI-SPEC copy)
        """
        return (
            '<div class="drhp-disclaimer-per-answer" '
            'style="font-size: 12px; font-style: italic; color: #475569;">'
            f"{PER_ANSWER_FOOTER}"
            "</div>"
        )

    def render_disclaimer_gate(self, session_state: dict) -> "dict | None":
        """Pure-Python disclaimer gate function (no Streamlit imports).

        Args:
            session_state: A dict-like object (Streamlit st.session_state or a
                           plain dict in tests). Reads the "disclaimer_accepted" key.

        Returns:
            None if disclaimer_accepted is True (user has already seen the modal).
            The modal dict (same shape as render_modal()) if not yet accepted.
            Wave 4 wraps this return value with the actual st.dialog decorator.
        """
        if session_state.get("disclaimer_accepted", False):
            return None
        return self.render_modal()


def render_disclaimer_gate(session_state: dict) -> "dict | None":
    """Module-level convenience function delegating to DisclaimerSurface.

    Exported per plan frontmatter requirement (exports: DisclaimerSurface,
    render_disclaimer_gate). Accepts session_state dict and returns modal
    dict or None.
    """
    return DisclaimerSurface().render_disclaimer_gate(session_state)


# ---------------------------------------------------------------------------
# Wave 4 additions — class-based rendering delegating to app/static/drhplens.css
# per UI-SPEC FLAG-2. No inline <style> injection. Wave 1 DisclaimerSurface and
# render_disclaimer_gate are preserved for backwards compatibility.
# ---------------------------------------------------------------------------

import html as _html  # noqa: E402


def render_first_use_modal() -> dict:
    """Return the first-use modal content as a plain dict.

    Pure-data function (no Streamlit calls at module level). app.py wraps this
    with @st.dialog. Returns dict with added 'css_class' key for Task 1 CSS.

    Returns:
        {
            "heading":   str,  — MODAL_HEADING
            "body":      str,  — ANCHOR_COPY + " " + MODAL_BODY_ADDENDUM
            "cta_text":  str,  — MODAL_CTA
            "css_class": str,  — "drhp-modal"
        }
    """
    data = DisclaimerSurface().render_modal()
    return {**data, "css_class": "drhp-modal"}


def render_persistent_footer() -> str:
    """Return the persistent slim footer as a class-based HTML string.

    Delegates styling to .drhp-footer in app/static/drhplens.css (UI-SPEC FLAG-2).
    No inline style= attribute. 12px is enforced via CSS class (TRUST-03 SEBI floor).

    Returns HTML string for st.markdown(..., unsafe_allow_html=True).
    """
    return (
        f'<div class="drhp-footer">'
        f'{_html.escape(ANCHOR_COPY)}'
        f' &middot; <a class="drhp-footer-link" href="/methodology">methodology</a>'
        f'</div>'
    )


def render_per_answer_footer() -> str:
    """Return the per-answer disclaimer as a class-based HTML string.

    Delegates styling to .drhp-disclaimer-per-answer in app/static/drhplens.css.
    No inline style= attribute (UI-SPEC FLAG-2).
    """
    return (
        f'<div class="drhp-disclaimer-per-answer">'
        f'{_html.escape(PER_ANSWER_FOOTER)}'
        f'</div>'
    )
