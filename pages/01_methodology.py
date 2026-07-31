"""
pages/01_methodology.py — the DS-rigor / transparency surface (route: /methodology).

Distinct from /how_it_works (the retail-investor explainer): this page is for the
data-science reviewer — the RAG architecture, the evaluation plan + metrics, the
honesty guardrails, and the stack. Phase 6 (LAND-01) wires the LIVE eval numbers
and the failure gallery in; today the targets/gates and status are shown honestly.
"""
import html
import json
from pathlib import Path

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
_ARCH = [
    ("01", "Parse", "Docling · layout-aware · page-anchored chunks"),
    ("02", "Retrieve", "hybrid · BM25 + bge-m3 · Qdrant"),
    ("03", "Rerank", "bge-reranker-v2-m3 · top-50 &rarr; top-5"),
    ("04", "Synthesise", "LLM answers only from retrieved context"),
    ("05", "Cite-check", "verify each claim's page · drop unsupported"),
]
_STAGES_UNUSED = [
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
_stages_html = '<div class="drhp-arch-arrow">&rarr;</div>'.join(
    f'<div class="drhp-arch-stage"><div class="s-n">{n}</div>'
    f'<div class="s-t">{t}</div><div class="s-d">{sd}</div></div>'
    for n, t, sd in _ARCH
)
st.markdown(f'<div class="drhp-arch">{_stages_html}</div>', unsafe_allow_html=True)

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

# ── Forecaster model card ────────────────────────────────────────────────────
# The destination of the snapshot forecast block's "Full model card →" link (UI-03,
# FCAST-05). RENDER-ONLY isolation (T-05-10-ISO): this section reads the committed
# model_card/ artifacts (card_data.json + the calibration/PIT/SHAP PNGs) and imports
# NO xgboost / mapie / sklearn / shap / model-training module — it never touches the
# model pipeline (mirrors the 05-07 forecast-block cache-only posture). Every
# card-derived string is HTML-escaped before interpolation (T-05-10-XSS).
st.markdown(
    render_section_head("Forecaster", "The listing-day model card"),
    unsafe_allow_html=True,
)
_MODEL_CARD_DIR = Path(__file__).resolve().parents[1] / "model_card"
_card_data_path = _MODEL_CARD_DIR / "card_data.json"


def _mc_num(value, nd: int = 3) -> str:
    """Format a card number honestly; NaN / non-numeric renders as an em-dash."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    return "—" if num != num else f"{num:.{nd}f}"


# ── Historical panel survivorship sanity (04-07 / SC-5) ──────────────────────
# The forecaster's backtest universe is a survivorship-corrected panel; its median
# listing-day return is sanity-checked against the ~7% MAAR baseline (P3). Render-only:
# reads the committed data/historical/panel_sanity.json (json ONLY — never a
# pipelines import, T-05-10-ISO). A divergence flag is shown VERBATIM only when it
# actually fires; within-band is stated honestly, never a fabricated alarm.
_panel_sanity_path = (
    Path(__file__).resolve().parents[1] / "data" / "historical" / "panel_sanity.json"
)
if _panel_sanity_path.is_file():
    _ps = json.loads(_panel_sanity_path.read_text(encoding="utf-8"))
    if _ps.get("flag"):
        _ps_verdict = (
            f'<span class="drhp-not-disclosed">{html.escape(str(_ps["flag"]))}</span>'
        )
    else:
        _ps_verdict = (
            "The built panel's median listing-day return is "
            f"<strong>{_mc_num(_ps.get('median_pct'), 2)}%</strong> over "
            f"{html.escape(str(_ps.get('n_scored', '—')))} scored IPOs — above the "
            f"~{_mc_num(_ps.get('baseline_pct'), 2)}% point estimate but WITHIN the "
            f"[{_mc_num(_ps.get('band_lower_pct'), 0)}%, "
            f"{_mc_num(_ps.get('band_upper_pct'), 0)}%] sanity band, so no "
            "survivorship-inflation flag fires (withdrawn / delisted IPOs are retained "
            "as NaN, not dropped — P3)."
        )
    st.markdown(
        '<p class="drhp-method-note"><strong>Survivorship sanity.</strong> '
        f"{html.escape(str(_ps.get('methodology', '')))} {_ps_verdict}</p>",
        unsafe_allow_html=True,
    )


if not _card_data_path.is_file():
    st.markdown(
        '<p class="drhp-method-note drhp-not-disclosed">'
        "The forecaster model card has not been generated yet.</p>",
        unsafe_allow_html=True,
    )
else:
    _card = json.loads(_card_data_path.read_text(encoding="utf-8"))

    if _card.get("seed"):
        st.markdown(
            '<p class="drhp-method-note">Seed / not-yet-regenerated: these numbers are '
            "assembled from the current seed artifacts so the card renders offline. "
            "They regenerate from the live walk-forward at the Phase 5 live build — "
            "seed numbers are never shown as live results.</p>",
            unsafe_allow_html=True,
        )

    # Held-out coverage / MAE / R²-alarm status (the real numbers, P17).
    _r2_line = (
        "R² leakage alarm FIRED — see the card."
        if _card.get("r2_alarm")
        else f"Out-of-sample median R² = {_mc_num(_card.get('r2'))} ≤ 0.5 — no leakage "
        "alarm (a humble R² is expected for a pre-apply, no-demand model)."
    )
    st.markdown(
        '<p class="drhp-method-note">Held-out 80% interval coverage '
        f"<strong>{_mc_num(_card.get('coverage'))}</strong> · mean absolute error "
        f"<strong>{_mc_num(_card.get('mae_pts'), 2)}</strong> points over "
        f"{html.escape(str(_card.get('n_scored', '—')))} scored IPOs. "
        f"{html.escape(_r2_line)}</p>",
        unsafe_allow_html=True,
    )

    # Committed diagnostic plots: calibration reliability, PIT histogram, SHAP.
    for _fname, _cap in (
        ("calibration.png",
         "Reliability diagram — nominal vs empirical coverage (held-out)."),
        ("pit.png",
         "PIT histogram — grid-derived; a flat histogram means calibrated."),
        ("shap.png",
         "Feature importance over the lean feature set."),
    ):
        _plot_path = _MODEL_CARD_DIR / _fname
        if _plot_path.is_file():
            st.image(str(_plot_path), caption=_cap, use_container_width=True)

    # Four baselines + Diebold–Mariano table with the P9 release-gate verdict.
    _gate = "PASS" if _card.get("gate_passed") else "FAIL"
    _dm_rows = "".join(
        f'<tr><td class="m-name">{html.escape(str(b.get("name", "")))}</td>'
        f'<td class="m-target">{_mc_num(b.get("dm_stat"))}</td>'
        f'<td class="m-target">{_mc_num(b.get("p_value"))}</td>'
        f'<td class="m-status">{html.escape(str(b.get("verdict", "")))}</td></tr>'
        for b in _card.get("baselines", [])
    )
    st.markdown(
        '<p class="drhp-method-note">Four naive baselines under the identical '
        "as-of-T0 protocol, tested with Diebold–Mariano (Harvey-corrected). "
        f"<strong>P9 release gate: {_gate}.</strong></p>"
        '<div class="drhp-metrics-wrap"><table class="drhp-metrics">'
        "<thead><tr><th>Baseline</th><th>DM stat</th><th>p-value</th>"
        "<th>Verdict</th></tr></thead>"
        f"<tbody>{_dm_rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )

    # available_at ≤ T0 leakage audit (the lean feature list) + the anchor pre-open
    # audit (D5-08).
    _leak = _card.get("leakage_audit", [])
    # The live card stamps each feature with populated_live (whether its source was
    # actually populated on the live panel); the seed card omits it. Show the column
    # only when present — a deferred feature is marked "no (deferred)", never hidden.
    _has_pop = any("populated_live" in r for r in _leak)

    def _pop_cell(r: dict) -> str:
        if "populated_live" not in r:
            return ""
        label = "yes" if r.get("populated_live") else "no (deferred)"
        return f'<td class="m-status">{label}</td>'

    _leak_rows = "".join(
        f'<tr><td class="m-name">{html.escape(str(r.get("feature", "")))}</td>'
        f'<td class="m-how">{html.escape(str(r.get("family", "")))}</td>'
        f'<td class="m-target">{html.escape(str(r.get("available_at_rule", "")))}</td>'
        f'{_pop_cell(r)}'
        f'<td class="m-status">{html.escape(str(r.get("verdict", "")))}</td></tr>'
        for r in _leak
    )
    _pop_th = "<th>Populated live?</th>" if _has_pop else ""
    _pop_note = (
        " The <code>Populated live?</code> column flags a feature whose source was "
        "deferred at the live build — marked, not hidden."
        if _has_pop
        else ""
    )
    st.markdown(
        '<p class="drhp-method-note">Every feature carries a verified '
        "<code>available_at ≤ T0</code> stamp — the leakage gate that keeps the model "
        f"honest (FCAST-02).{_pop_note}</p>"
        '<div class="drhp-metrics-wrap"><table class="drhp-metrics">'
        "<thead><tr><th>Feature</th><th>Family</th><th>available_at</th>"
        f"{_pop_th}<th>Verdict</th></tr></thead>"
        f"<tbody>{_leak_rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )

    _anchor_rows = "".join(
        f'<tr><td class="m-name">{html.escape(str(r.get("feature", "")))}</td>'
        f'<td class="m-how">{html.escape(str(r.get("source_field", "")))}</td>'
        f'<td class="m-target">{html.escape(str(r.get("disclosure_timestamp", "")))}</td>'
        f'<td class="m-status">{html.escape(str(r.get("verdict", "")))}</td></tr>'
        for r in _card.get("anchor_audit", [])
    )
    st.markdown(
        '<p class="drhp-method-note">Anchor pre-open leakage audit (D5-08): only the '
        "pre-open anchor allocation (disclosed T0−1) may be read — post-open book-build "
        "demand can never be a feature.</p>"
        '<div class="drhp-metrics-wrap"><table class="drhp-metrics">'
        "<thead><tr><th>Anchor feature</th><th>Pre-open source</th><th>Disclosed</th>"
        "<th>Verdict</th></tr></thead>"
        f"<tbody>{_anchor_rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )

    # N-per-sector thinness report (D5-10).
    _sector_rows = "".join(
        f'<tr><td class="m-name">{html.escape(str(_sector))}</td>'
        f'<td class="m-target">{html.escape(str(_n))}</td></tr>'
        for _sector, _n in sorted(_card.get("n_per_sector", {}).items())
    )
    st.markdown(
        '<p class="drhp-method-note">N per sector (D5-10): thin sectors are pooled into '
        "<code>Other</code> so a small slice never becomes a noise-prone single value; "
        "the original counts stay visible.</p>"
        '<div class="drhp-metrics-wrap"><table class="drhp-metrics">'
        "<thead><tr><th>Sector</th><th>N</th></tr></thead>"
        f"<tbody>{_sector_rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )

    # Known limitations — the honest D5-01 grid (low R² is a feature, not a bug).
    _lim_cards = "".join(
        f'<div class="drhp-hiw-card"><h3>{html.escape(str(_lim.get("title", "")))}</h3>'
        f'<p>{html.escape(str(_lim.get("body", "")))}</p></div>'
        for _lim in _card.get("limitations", [])
    )
    st.markdown(
        f'<div class="drhp-hiw drhp-guard-grid">{_lim_cards}</div>',
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
