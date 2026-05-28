"""
/methodology stub page per UI-SPEC §L-7 — must not 404.
Phase 6 LAND-01 replaces this with the full recruiter-grade methodology surface.

Streamlit multipage routing: this file's route is /methodology (Streamlit strips
the '01_' prefix; the URL slug is derived from the filename without the NN_ prefix).
"""
import streamlit as st

# Page config must be the first Streamlit call
st.set_page_config(
    page_title="Methodology · DRHPLens",
    initial_sidebar_state="collapsed",
)

from app.util.css_loader import load_global_css  # noqa: E402
from ui.state import init_session_state  # noqa: E402
from ui.copy import METHODOLOGY_STUB_BODY, METHODOLOGY_STUB_HEADING  # noqa: E402
from ui.disclaimer import render_persistent_footer  # noqa: E402

# Load global CSS (same as home page)
_css_html = load_global_css(st.session_state)
if _css_html:
    st.markdown(_css_html, unsafe_allow_html=True)

# Initialize session state (needed for CSS loader + potential future stateful use)
init_session_state(st.session_state)

# Set lang attribute for screen readers (Phase 6 may use a Components solution)
# ## FLAG-LANG-ATTR: Phase 6 polish — migrate to Streamlit Components or Next.js
st.markdown(
    '<script>document.documentElement.lang = "en-IN";</script>',
    unsafe_allow_html=True,
)

# ── Heading (Display 28px via .drhp-hero-display class) ─────────────────────
st.markdown(
    f'<h1 class="drhp-hero-display">{METHODOLOGY_STUB_HEADING}</h1>',
    unsafe_allow_html=True,
)

# ── Body paragraph ───────────────────────────────────────────────────────────
st.markdown(METHODOLOGY_STUB_BODY)

# ── GitHub link ──────────────────────────────────────────────────────────────
# ## FLAG-GITHUB-URL: No git remote configured. Placeholder URL below.
# Wave 5 deploy planner: replace with the actual GitHub repo URL before HF Spaces ship.
st.markdown("[GitHub repository →](https://github.com/REPLACE-ME/drhplens)")

# ── Back to home ─────────────────────────────────────────────────────────────
st.markdown("[← Back to DRHPLens](/)")

# ── Persistent footer (same disclaimer as home, per UI-SPEC L-7 §Page structure §5) ──
st.markdown(render_persistent_footer(), unsafe_allow_html=True)

# What NOT to render in Phase 1's stub (UI-SPEC §/methodology Stub Page Contract):
# - No fake eval scores (no "0.91 faithfulness" placeholder)
# - No methodology pane preview (Phase 3 METHOD-01 owns)
# - No model card stub (Phase 5 FCAST-05 owns)
# - No chat input, hero metadata header, or citation chips (home-only)
