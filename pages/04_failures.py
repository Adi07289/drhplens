"""
pages/04_failures.py — the FAILGAL-01 failure gallery (route: /failures).

A browseable, honestly-labelled gallery of real DRHPLens failures across the three
surfaces (rag / extraction / forecast), rendered READ-ONLY from the committed
eval/failures/failures.yaml — no live LLM / agent / model call at render (P19,
demo-safe). The surface + free-text controls filter the already-loaded entries
IN-MEMORY inside ui.failures.render_failures (the "searchable" FAILGAL-01
mechanism); the page imports nothing from the agent/LLM/model pipeline.
"""
import html as _html

import streamlit as st

st.set_page_config(
    page_title="Failures · DRHPLens",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

from app.util.css_loader import load_global_css  # noqa: E402
from ui.chrome import render_nav, render_site_footer  # noqa: E402
from ui.copy import FAILURES_EYEBROW, FAILURES_HEADING  # noqa: E402
from ui.failures import render_failures  # noqa: E402
from ui.state import init_session_state  # noqa: E402

_css_html = load_global_css(st.session_state)
if _css_html:
    st.markdown(_css_html, unsafe_allow_html=True)
init_session_state(st.session_state)
st.markdown(render_nav(), unsafe_allow_html=True)

# ── Hero (eyebrow + heading from ui/copy.py, scrubber-clean) ──────────────────
st.markdown(
    '<div class="drhp-hero2" style="padding:52px 0 32px">'
    '<div class="drhp-glow drhp-glow-a"></div>'
    f'<div class="drhp-hero-eyebrow">{_html.escape(FAILURES_EYEBROW)}</div>'
    f'<h1 class="drhp-hero-title">{_html.escape(FAILURES_HEADING)}</h1>'
    '<p class="drhp-hero-sub">Every failure below is real, cited to a committed file, and '
    'rendered read-only — no live call. Filter by surface, or search across the whole '
    'gallery by keyword.</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Render-only filter controls (the "searchable" requirement) ────────────────
# Both controls filter the already-loaded entries in-memory inside render_failures;
# neither triggers a live call.
surface_sel = st.selectbox(
    "Surface",
    ["all", "rag", "extraction", "forecast"],
    key="fail_surface",
)
q = st.text_input(
    "Search failures",
    key="fail_query",
    placeholder="filter by keyword…",
)

render_failures(
    surface=None if surface_sel == "all" else surface_sel,
    query=q or None,
)

st.markdown(render_site_footer(), unsafe_allow_html=True)
