"""
pages/03_how_it_works.py — dedicated "How it works" page (route: /how_it_works).

A plain-English walkthrough of the DRHP → cited-answer pipeline for the retail
investor, plus the honesty "will / won't" contract. Distinct from /methodology,
which is the DS-rigor surface (eval scores, model card, failure gallery).
"""
import streamlit as st

st.set_page_config(
    page_title="DRHPLens · How it works",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

from app.util.css_loader import load_global_css  # noqa: E402
from ui.chrome import render_nav, render_section_head, render_site_footer  # noqa: E402
from ui.state import init_session_state  # noqa: E402

_css_html = load_global_css(st.session_state)
if _css_html:
    st.markdown(_css_html, unsafe_allow_html=True)
init_session_state(st.session_state)
st.markdown(render_nav(), unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="drhp-hero2" style="padding:52px 0 36px">'
    '<div class="drhp-glow drhp-glow-a"></div>'
    '<div class="drhp-hero-eyebrow">How it works</div>'
    '<h1 class="drhp-hero-title">From a 400-page PDF<br>to an honest answer.</h1>'
    '<p class="drhp-hero-sub">No black box. Here is exactly what DRHPLens does with a '
    'prospectus — and the lines it refuses to cross.</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ── The pipeline (vertical numbered flow) ────────────────────────────────────
_STEPS = [
    ("01", "Ingest the prospectus",
     "We pull the official DRHP/RHP PDF straight from SEBI / NSE / BSE — the same "
     "300–500 page document filed with the regulator — and mirror it locally so a "
     "citation link never rots."),
    ("02", "Parse it, layout-aware",
     "A document model reads the structure — sections, tables, and page numbers — so "
     "every figure keeps a handle to the exact page it came from. Financial tables are "
     "extracted as real numbers, not flattened text."),
    ("03", "Extract the signals",
     "Structured red-flags — RPT % of revenue, OFS vs fresh issue, promoter pledge, "
     "auditor history, debt trajectory, going-concern mentions — each pulled with a "
     "visible confidence score, so the extractor's uncertainty is never hidden."),
    ("04", "Answer with citations",
     "You ask in plain English. Retrieval finds the exact passages, and every claim in "
     "the answer renders as a superscript citation you can click through to its DRHP "
     "page. If a number isn't in the document, it doesn't appear."),
    ("05", "Add real context",
     "Peer multiples against the DRHP's own listed comparables, and how similar Indian "
     "IPOs have actually behaved — so a prospectus is read against reality, not "
     "marketing gloss."),
    ("06", "Refuse when unsure",
     "If the prospectus doesn't address something, DRHPLens says so instead of guessing. "
     "No fabricated numbers, and never a buy / sell / subscribe call."),
]
_steps_html = "".join(
    f'<div class="drhp-flow-step"><div class="drhp-flow-num">{n}</div>'
    f'<div class="drhp-flow-body"><h3>{t}</h3><p>{d}</p></div></div>'
    for n, t, d in _STEPS
)
st.markdown(f'<div class="drhp-flow">{_steps_html}</div>', unsafe_allow_html=True)

# ── The honesty contract (will / won't) ──────────────────────────────────────
st.markdown(
    render_section_head("The contract", "What DRHPLens will and won't do"),
    unsafe_allow_html=True,
)
_WILL = [
    "Cite every claim back to a DRHP page",
    "Show the extractor's confidence, out loud",
    "Read a prospectus against listed peers &amp; history",
    "Say “not disclosed” when the document is silent",
]
_WONT = [
    "Say buy, sell, subscribe, or avoid",
    "Invent a number the DRHP never states",
    "Hide uncertainty behind a confident tone",
    "Colour a low or high figure as good or bad",
]
_will_li = "".join(f"<li>{x}</li>" for x in _WILL)
_wont_li = "".join(f"<li>{x}</li>" for x in _WONT)
st.markdown(
    '<div class="drhp-principles">'
    f'<div class="drhp-principle-card drhp-will"><h4>DRHPLens will</h4><ul>{_will_li}</ul></div>'
    f'<div class="drhp-principle-card drhp-wont"><h4>DRHPLens won\'t</h4><ul>{_wont_li}</ul></div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── CTA band ─────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="drhp-cta-band">'
    '<div class="drhp-glow drhp-glow-b" style="opacity:.28"></div>'
    '<h2>See it on a real prospectus.</h2>'
    '<p>Swiggy is the fully worked example — every figure cited back to the DRHP.</p>'
    '<a class="drhp-btn drhp-btn-primary" href="/snapshot?drhp_id=swiggy_2024_11" target="_self">'
    'Open the Swiggy snapshot&nbsp;&rarr;</a>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(render_site_footer(), unsafe_allow_html=True)
