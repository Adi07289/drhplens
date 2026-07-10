"""
Single point of CSS injection for DRHPLens.

UI-SPEC FLAG-2 contract: Any code that needs custom styles MUST add a rule to
`app/static/drhplens.css` and reference it via class; NEVER inject inline <style>
tags from other modules. This module is the one and only CSS injection point.

Injection cadence: the <style> MUST be (re-)emitted on EVERY script run. Streamlit
removes any element that is not produced by the current run, so a once-per-session
"idempotency" guard silently dropped the whole stylesheet after the first
st.rerun()/st.stop() — most visibly when the user dismisses the first-use modal
(which runs st.stop()), leaving the catalogue and every subsequent page unstyled.
Re-emitting the identical <style> each run is cheap: Streamlit diffs it to the same
delta position and updates in place (no accumulation, no flicker).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_CSS_PATH = Path(__file__).parent.parent / "static" / "drhplens.css"


@lru_cache(maxsize=1)
def _css_text() -> str:
    """Read the stylesheet once per process (it does not change at runtime)."""
    return _CSS_PATH.read_text(encoding="utf-8")


def load_global_css(session_state=None) -> str:
    """Return the global CSS as a <style> HTML string — on EVERY call.

    Callers MUST render the result on every run so the stylesheet is always
    present in the DOM:

        st.markdown(load_global_css(st.session_state), unsafe_allow_html=True)

    Args:
        session_state: accepted for call-site compatibility; unused. (Previously
                       a session flag gated a once-only injection, which is the
                       bug this module now avoids.)

    Returns:
        A string starting with '<style>' and ending with '</style>'. Never None.
    """
    del session_state  # unused; kept so existing call sites need no change
    return f"<style>{_css_text()}</style>"
