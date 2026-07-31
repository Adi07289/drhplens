"""
DRHPLens Streamlit entry point — Phase 2 catalogue landing.

`/` is now the multi-IPO catalogue (factual IPO card grid, no green/red, no
performance badges — P2-L1). Click a card -> /snapshot?drhp_id=<id> (the
per-IPO snapshot page, pages/02_snapshot.py).

FLAG-ROUTING (02-UI-SPEC.md): the Phase 1 chat/metadata/answer-rendering
code that used to live here has been extracted into
ui/snapshot_chat.py:render_snapshot_chat(drhp_id), parameterized by drhp_id,
and is now invoked from pages/02_snapshot.py (Block 9 — co-located chat).
"""
import logging

import streamlit as st

# ── Page config (MUST be the first Streamlit call) ───────────────────────────
st.set_page_config(
    page_title="DRHPLens · Indian IPOs, read honestly",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

from app.util.css_loader import load_global_css  # noqa: E402
from compliance.disclaimer_text import MODAL_HEADING  # noqa: E402
from data.catalogue_loader import load_catalogue  # noqa: E402
from ui.catalogue import render_catalogue_grid  # noqa: E402
from ui.copy import (  # noqa: E402
    CATALOGUE_EMPTY_BODY,
    CATALOGUE_EMPTY_HEADING,
    CATALOGUE_HERO_HEADING,
    CATALOGUE_HERO_SUBHEADING,
)
from ui.chrome import (  # noqa: E402
    render_how_it_works,
    render_landing_hero,
    render_nav,
    render_section_head,
    render_site_footer,
    render_trust_band,
)
from ui.disclaimer import render_first_use_modal, render_persistent_footer  # noqa: E402
from ui.state import has_seen_modal, init_session_state, mark_modal_seen  # noqa: E402

logger = logging.getLogger(__name__)


def _load_css() -> None:
    """Load global CSS once per session (UI-SPEC FLAG-2)."""
    css_html = load_global_css(st.session_state)
    if css_html:
        st.markdown(css_html, unsafe_allow_html=True)


def _set_lang() -> None:
    """Set HTML lang attribute for screen readers.

    ## FLAG-LANG-ATTR: Streamlit 1.36 has no config for <html lang>. This JS
    workaround runs after first render. Phase 6 may use Streamlit Components.
    """
    st.markdown(
        '<script>document.documentElement.lang = "en-IN";</script>',
        unsafe_allow_html=True,
    )


def _show_modal_gate() -> None:
    """First-use modal — shown once per session (UI-SPEC §Disclaimer Surfaces §1)."""
    @st.dialog(MODAL_HEADING)
    def _first_use_modal() -> None:
        data = render_first_use_modal()
        st.markdown(data["body"])
        if st.button(data["cta_text"], type="primary", use_container_width=True):
            mark_modal_seen(st.session_state)
            st.rerun()

    if not has_seen_modal(st.session_state):
        _first_use_modal()
        st.stop()


def _render_hero() -> None:
    """Catalogue hero — Display 28px heading + subheading (always expanded)."""
    st.markdown(
        f'<h1 class="drhp-hero-display">{CATALOGUE_HERO_HEADING}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="drhp-hero-subheading">{CATALOGUE_HERO_SUBHEADING}</p>',
        unsafe_allow_html=True,
    )


def _render_empty_state() -> None:
    """Catalogue empty state — heading 20px + body (no spinner)."""
    st.markdown(
        f'<h2 class="drhp-empty-heading">{CATALOGUE_EMPTY_HEADING}</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(CATALOGUE_EMPTY_BODY)


def main() -> None:
    """Main app entry point — the premium catalogue landing, top-to-bottom."""
    _set_lang()
    _load_css()
    init_session_state(st.session_state)
    st.markdown(render_nav(), unsafe_allow_html=True)
    _show_modal_gate()  # first-use modal + st.stop() until dismissed

    st.markdown(render_landing_hero(), unsafe_allow_html=True)

    ipos = load_catalogue()
    st.markdown(render_trust_band(len(ipos)), unsafe_allow_html=True)
    st.markdown(render_how_it_works(), unsafe_allow_html=True)
    st.markdown(
        render_section_head("The catalogue", "Recent Indian IPOs", anchor="drhp-catalogue"),
        unsafe_allow_html=True,
    )

    if not ipos:
        _render_empty_state()
    else:
        render_catalogue_grid(ipos)

    st.markdown(render_site_footer(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
else:
    # Streamlit runs the module top-to-bottom; call main() unconditionally
    main()
