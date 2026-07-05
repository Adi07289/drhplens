"""
pages/02_snapshot.py — Per-IPO snapshot page (Phase 2 Wave 4, 02-05-PLAN.md Task 2).

Route: /snapshot?drhp_id=<id>. Reads drhp_id from st.query_params, validates
it via is_known_drhp_id (T-02-V5 — untrusted query param, allow-list gated
BEFORE any load_snapshot/chat call), then renders the 6 cited blocks in the
locked UI-SPEC order with the OFS-vs-fresh split bar as Block 5's focal
element, followed by the co-located Q&A chat (Block 9, bound to this page's
drhp_id).
"""
import streamlit as st

# ── Page config (MUST be the first Streamlit call) ───────────────────────────
st.set_page_config(
    page_title="DRHPLens · Snapshot",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed",
)

from app.util.css_loader import load_global_css  # noqa: E402
from data.catalogue_loader import is_known_drhp_id, load_catalogue  # noqa: E402
from pipelines.redflag import load_redflag  # noqa: E402
from pipelines.snapshot import load_snapshot  # noqa: E402
from ui.copy import (  # noqa: E402
    REDFLAG_EMPTY_BODY,
    REDFLAG_EMPTY_HEADING,
    REDFLAG_ERROR_STATE,
    SNAPSHOT_BLOCK_HEADING_BUSINESS,
    SNAPSHOT_BLOCK_HEADING_FINANCIALS,
    SNAPSHOT_BLOCK_HEADING_PROMOTER,
    SNAPSHOT_BLOCK_HEADING_RISKS,
    SNAPSHOT_BLOCK_HEADING_USE_OF_PROCEEDS,
    SNAPSHOT_BREADCRUMB_BACK,
    SNAPSHOT_CACHE_UNREACHABLE,
    SNAPSHOT_PRECOMPUTING_BODY_TEMPLATE,
    SNAPSHOT_PRECOMPUTING_HEADING,
    UNKNOWN_DRHP_ID_COPY,
)
from ui.disclaimer import render_persistent_footer  # noqa: E402
from ui.snapshot_blocks import (  # noqa: E402
    render_financials_table,
    render_grounded_block,
    render_idf_risk_list,
    render_redflag_table,
    render_risk_block,
    render_split_bar,
    render_use_of_proceeds_body,
)
from ui.snapshot_chat import render_snapshot_chat  # noqa: E402
from ui.state import init_session_state  # noqa: E402

import html as _html  # noqa: E402

# ── Load global CSS + session state (idempotent) ──────────────────────────────
_css_html = load_global_css(st.session_state)
if _css_html:
    st.markdown(_css_html, unsafe_allow_html=True)
init_session_state(st.session_state)

st.markdown(
    '<script>document.documentElement.lang = "en-IN";</script>',
    unsafe_allow_html=True,
)


def _render_breadcrumb(issuer: str | None) -> None:
    suffix = f' / {_html.escape(issuer)}' if issuer else ""
    st.markdown(
        f'<div class="drhp-breadcrumb">'
        f'<a href="/">{_html.escape(SNAPSHOT_BREADCRUMB_BACK)}</a>{suffix}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_unknown_id() -> None:
    """T-02-V5: unknown/missing drhp_id -> honesty note, never an exception."""
    _render_breadcrumb(None)
    st.markdown(
        f'<h1 class="drhp-hero-display">{_html.escape(UNKNOWN_DRHP_ID_COPY)}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown("[← All IPOs](/)")
    st.markdown(render_persistent_footer(), unsafe_allow_html=True)


def _issuer_for(drhp_id: str) -> str:
    for ipo in load_catalogue():
        if ipo.drhp_id == drhp_id:
            return ipo.issuer
    return drhp_id


def _render_redflag_block(redflag_record, redflag_state: str) -> None:
    """Render the Red-flag signals block high on the page (UI-SPEC IA).

    A cache miss renders the empty-state copy in the block slot (never fabricated
    rows); an error renders the amber .drhp-refusal banner; a present record
    renders the 7-row table. The rest of the page renders regardless.
    """
    if redflag_state == "error":
        st.markdown(
            f'<div class="drhp-refusal" role="alert" aria-live="polite">'
            f'<p class="drhp-refusal-body">{_html.escape(REDFLAG_ERROR_STATE)}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return
    if redflag_record is None:
        st.markdown('<div class="drhp-redflag-table">', unsafe_allow_html=True)
        st.markdown(
            f'<h2 class="drhp-empty-heading">{_html.escape(REDFLAG_EMPTY_HEADING)}</h2>',
            unsafe_allow_html=True,
        )
        st.markdown(REDFLAG_EMPTY_BODY)
        st.markdown('</div>', unsafe_allow_html=True)
        return
    render_redflag_table(redflag_record)


def main() -> None:
    raw_drhp_id = st.query_params.get("drhp_id")

    # T-02-V5: validate via allow-list BEFORE any load_snapshot/chat call.
    if not raw_drhp_id or not is_known_drhp_id(raw_drhp_id):
        _render_unknown_id()
        return

    drhp_id = raw_drhp_id
    issuer = _issuer_for(drhp_id)

    _render_breadcrumb(issuer)
    st.markdown(
        f'<h1 class="drhp-hero-display">{_html.escape(issuer)}</h1>',
        unsafe_allow_html=True,
    )

    try:
        record = load_snapshot(drhp_id)
    except FileNotFoundError:
        # Snapshot cache not yet pre-computed — still-precomputing state.
        # Chat remains usable below (UI-SPEC §Loading).
        st.markdown(
            f'<h2 class="drhp-empty-heading">{_html.escape(SNAPSHOT_PRECOMPUTING_HEADING)}</h2>',
            unsafe_allow_html=True,
        )
        st.markdown(SNAPSHOT_PRECOMPUTING_BODY_TEMPLATE.format(issuer=issuer))
        record = None
    except Exception:
        st.markdown(
            f'<div class="drhp-refusal" role="alert" aria-live="polite">'
            f'<p class="drhp-refusal-body">{_html.escape(SNAPSHOT_CACHE_UNREACHABLE)}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        record = None

    # Phase 3 red-flag cache read — same allow-list guard (drhp_id validated
    # above) + try/except posture as load_snapshot. A cache miss -> empty-state
    # copy; any other error -> amber .drhp-refusal banner; never an unhandled
    # exception (T-03-01).
    redflag_record = None
    redflag_state = "ok"
    try:
        redflag_record = load_redflag(drhp_id)
    except FileNotFoundError:
        redflag_record = None
        redflag_state = "missing"
    except Exception:
        redflag_record = None
        redflag_state = "error"

    # Red-flag signals block — HIGH on the page (after the metadata header,
    # above-the-fold-adjacent on mobile), before the Phase 2 field blocks.
    _render_redflag_block(redflag_record, redflag_state)

    if record is not None:
        # Locked block order: metadata, business, financials, risks,
        # use-of-proceeds (split bar first), promoter.
        render_grounded_block(record.fields.get("metadata"), "")
        render_grounded_block(record.fields.get("business"), SNAPSHOT_BLOCK_HEADING_BUSINESS)

        st.markdown('<div class="drhp-snapshot-block">', unsafe_allow_html=True)
        st.markdown(
            f'<h2 class="drhp-snapshot-block-heading">'
            f'{_html.escape(SNAPSHOT_BLOCK_HEADING_FINANCIALS)}</h2>',
            unsafe_allow_html=True,
        )
        render_financials_table(record.fields.get("financials"))
        st.markdown('</div>', unsafe_allow_html=True)

        # SINGLE risk list (UI-SPEC IA reconciliation, L3-4): the IDF-ranked list
        # SUPERSEDES the Phase 2 prioritized ordering. Exactly ONE renders at
        # runtime — the IDF list when ranked_risks exist, else the UNCHANGED
        # Phase 2 render_risk_block as the empty-state fallback.
        if redflag_record is not None and redflag_record.ranked_risks:
            render_idf_risk_list(redflag_record.ranked_risks, redflag_record)
        else:
            st.markdown('<div class="drhp-snapshot-block">', unsafe_allow_html=True)
            st.markdown(
                f'<h2 class="drhp-snapshot-block-heading">'
                f'{_html.escape(SNAPSHOT_BLOCK_HEADING_RISKS)}</h2>',
                unsafe_allow_html=True,
            )
            render_risk_block(record.fields.get("risks"))
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="drhp-snapshot-block">', unsafe_allow_html=True)
        st.markdown(
            f'<h2 class="drhp-snapshot-block-heading">'
            f'{_html.escape(SNAPSHOT_BLOCK_HEADING_USE_OF_PROCEEDS)}</h2>',
            unsafe_allow_html=True,
        )
        render_split_bar(record.ofs_fresh)
        render_use_of_proceeds_body(record.fields.get("use_of_proceeds"))
        st.markdown('</div>', unsafe_allow_html=True)

        render_grounded_block(record.fields.get("promoter"), SNAPSHOT_BLOCK_HEADING_PROMOTER)

    # 2xl gap + divider before the co-located Q&A chat (D2-08).
    st.markdown(
        '<div style="margin-top: 48px; border-top: 1px solid #E2E8F0;"></div>',
        unsafe_allow_html=True,
    )
    render_snapshot_chat(drhp_id)

    st.markdown(render_persistent_footer(), unsafe_allow_html=True)


main()
