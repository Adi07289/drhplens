"""
pages/01_methodology.py — the DS-rigor / transparency surface (route: /methodology).

Distinct from /how_it_works (the retail-investor explainer): this page is for the
data-science reviewer — the RAG architecture, the evaluation plan + metrics, the
honesty guardrails, and the stack. Phase 6 (LAND-01) wires the LIVE eval numbers
and the failure gallery in; today the targets/gates and status are shown honestly.
"""
import streamlit as st

st.set_page_config(
    page_title="Methodology · DRHPLens",
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
    '<div class="drhp-hero-eyebrow">Methodology</div>'
    '<h1 class="drhp-hero-title">How DRHPLens<br>keeps itself honest.</h1>'
    '<p class="drhp-hero-sub">The rigour behind the answers — retrieval, evaluation, and the '
    'guardrails that keep it factual. Built to be inspected, not trusted blindly.</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ── The retrieval pipeline ───────────────────────────────────────────────────
st.markdown(render_section_head("Retrieval", "The RAG pipeline"), unsafe_allow_html=True)
_STAGES = [
    ("01", "Parse &amp; chunk",
     "Docling parses the DRHP layout-aware. Chunks are 512–1024 tokens, page-anchored "
     "(<code>drhp_id · section · page</code>), and never split across a section boundary — "
     "financial tables are stored as structured records, not flattened text."),
    ("02", "Retrieve (hybrid)",
     "BM25 sparse retrieval + <code>bge-m3</code> dense embeddings over Qdrant, so both exact-term "
     "and semantic matches surface — recall is easy on repetitive DRHP boilerplate; precision is hard."),
    ("03", "Rerank",
     "A <code>bge-reranker-v2-m3</code> cross-encoder reranks the top ~50 hits down to the ~5 the "
     "model actually reads — the step that turns high recall into high precision."),
    ("04", "Synthesise",
     "The LLM answers only from those retrieved passages. Whole-section long-context synthesis is "
     "used when a query needs it, RAG when it's a needle-in-haystack lookup."),
    ("05", "Cite-check",
     "A verification step confirms each claim's cited page actually contains it. Unsupported claims "
     "are dropped, not shown — this is the anti-hallucination gate, not a nice-to-have."),
]
_stages_html = "".join(
    f'<div class="drhp-flow-step"><div class="drhp-flow-num">{n}</div>'
    f'<div class="drhp-flow-body"><h3>{t}</h3><p>{d}</p></div></div>'
    for n, t, d in _STAGES
)
st.markdown(f'<div class="drhp-flow">{_stages_html}</div>', unsafe_allow_html=True)

# ── Evaluation ───────────────────────────────────────────────────────────────
st.markdown(render_section_head("Evaluation", "Measured, not vibed"), unsafe_allow_html=True)
st.markdown(
    '<p class="drhp-method-note">Every metric is computed on a hand-curated gold set and committed '
    'to the repo. Targets and release gates are shown below; the full harness '
    '(RAGAS · DeepEval · Langfuse) lands in Phase 6.</p>',
    unsafe_allow_html=True,
)
_ROWS = [
    ("Faithfulness", "RAGAS · answer grounded in retrieved context", "&ge; 0.95", "Phase 6"),
    ("Citation accuracy", "custom · did the cited page contain the claim", "&ge; 0.95 · release gate", "Phase 6"),
    ("Context recall@k", "RAGAS · k = 5 / 10 / 30", "reported", "Phase 6"),
    ("Extraction F1", "hand-labeled gold set · 20–30 DRHPs, per field", "reported", "Phase 3"),
    ("Forecast coverage", "MAPIE conformal · empirical interval coverage", "≈ 80%", "Phase 5"),
]
_rows_html = "".join(
    f'<tr><td class="m-name">{a}</td><td class="m-how">{b}</td>'
    f'<td class="m-target">{c}</td><td class="m-status">{d}</td></tr>'
    for a, b, c, d in _ROWS
)
st.markdown(
    '<div class="drhp-metrics-wrap"><table class="drhp-metrics">'
    '<thead><tr><th>Metric</th><th>How it\'s measured</th><th>Target</th><th>Status</th></tr></thead>'
    f'<tbody>{_rows_html}</tbody></table></div>',
    unsafe_allow_html=True,
)

# ── Honesty guardrails ───────────────────────────────────────────────────────
st.markdown(render_section_head("Guardrails", "Safe by design"), unsafe_allow_html=True)
_GUARDS = [
    ("Refuses, doesn't fabricate",
     "If the prospectus is silent on something, DRHPLens says “not disclosed” — it never invents a figure."),
    ("Banned-token scrubber",
     "buy · sell · subscribe · avoid · target · fair value — prescriptive tokens are scrubbed before any answer leaves the model."),
    ("Numeric-faithfulness gate",
     "A 50-query numeric-only eval track; the app refuses to ship below the 0.95 gate. Wrong numbers fail CI, not users."),
    ("No verdict UX",
     "No red/green, no badges, no up/down arrows. A low and a high multiple render identically; confidence is shown, never hidden."),
]
_guards_html = "".join(
    f'<div class="drhp-hiw-card"><h3>{t}</h3><p>{d}</p></div>' for t, d in _GUARDS
)
st.markdown(f'<div class="drhp-hiw drhp-guard-grid">{_guards_html}</div>', unsafe_allow_html=True)

# ── Stack ────────────────────────────────────────────────────────────────────
st.markdown(render_section_head("Stack", "Built with"), unsafe_allow_html=True)
_STACK = [
    "LangGraph", "LlamaIndex", "Docling", "bge-m3", "bge-reranker-v2-m3", "Qdrant",
    "Instructor", "Pydantic", "RAGAS", "DeepEval", "Langfuse", "XGBoost", "MAPIE", "Streamlit",
]
_chips = "".join(f'<span class="drhp-chip">{s}</span>' for s in _STACK)
st.markdown(f'<div class="drhp-stack">{_chips}</div>', unsafe_allow_html=True)

# ── Show your work + source ──────────────────────────────────────────────────
st.markdown(
    '<div class="drhp-cta-band" style="margin-top:56px">'
    '<div class="drhp-glow drhp-glow-b" style="opacity:.28"></div>'
    '<h2>See the work on every answer.</h2>'
    '<p>Each Q&amp;A answer carries a “Show your work” pane — the retrieval query, the retrieved '
    'chunks with scores, the prompt, and the eval scores. Nothing is hidden.</p>'
    '<a class="drhp-btn drhp-btn-primary" href="https://github.com/REPLACE-ME/drhplens" target="_blank">'
    'Read the source on GitHub&nbsp;&rarr;</a>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(render_site_footer(), unsafe_allow_html=True)
