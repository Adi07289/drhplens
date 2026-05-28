"""
Single point of CSS injection for DRHPLens.

UI-SPEC FLAG-2 contract: Any code that needs custom styles MUST add a rule to
`app/static/drhplens.css` and reference it via class; NEVER inject inline <style>
tags from other modules. This module is the one and only CSS injection point.

Idempotency: protected against st.rerun()-driven double injection that bloats
the DOM and slows first-meaningful-paint on mobile.
"""
from __future__ import annotations

from pathlib import Path

_CSS_PATH = Path(__file__).parent.parent / "static" / "drhplens.css"
_SESSION_KEY = "_drhp_css_loaded"


def load_global_css(session_state) -> "str | None":
    """Load and return the global CSS as a <style> HTML string.

    Idempotent: second call with the same session_state returns None (the CSS
    is already injected; no need to re-inject on st.rerun()).

    Args:
        session_state: Streamlit st.session_state or any dict-like with
                       __contains__ and __setitem__.

    Returns:
        A string starting with '<style>' and ending with '</style>' on first
        call. None on subsequent calls (idempotency guard).

    Usage in app.py:
        css_html = load_global_css(st.session_state)
        if css_html:
            st.markdown(css_html, unsafe_allow_html=True)
    """
    if _SESSION_KEY in session_state:
        return None
    css_text = _CSS_PATH.read_text(encoding="utf-8")
    session_state[_SESSION_KEY] = True
    return f"<style>{css_text}</style>"
