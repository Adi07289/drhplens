"""
ui/snapshot_blocks.py — 6 snapshot field-block renderers (02-05-PLAN.md Task 2).

Every renderer consumes a SnapshotRecord field (GroundedAnswer | RefusalResponse)
and reuses the UNCHANGED Phase 1 citation chip + expander renderer (ui/chip.py,
ui/expander.py) — snapshot fields cite exactly like Q&A answers (P2-L4).

NO green/red anywhere: split bar uses accent (OFS) + neutral grey (fresh);
financials losses render in parentheses in the SAME text color as profits;
risk items carry a descriptive "Risk N of M" counter with no severity color.
"""
from __future__ import annotations

import html as _html

import streamlit as st

from agent.schemas import GroundedAnswer, RefusalResponse
from ui.chip import render_answer_with_chips
from ui.disclaimer import render_per_answer_footer
from ui.expander import render_citation_expanders
from ui.copy import (
    FIELD_NOT_DISCLOSED_NOTE,
    RISK_COUNTER_TEMPLATE,
    SPLIT_BAR_CAPTION_TEMPLATE,
    SPLIT_BAR_PURE_FRESH,
    SPLIT_BAR_PURE_OFS,
)


def _render_not_disclosed() -> None:
    """P2-L8 honesty note — never a fabricated value, never a guess."""
    st.markdown(
        f'<div class="drhp-not-disclosed">{_html.escape(FIELD_NOT_DISCLOSED_NOTE)}</div>',
        unsafe_allow_html=True,
    )


def _render_expanders(content: GroundedAnswer, chip_map: dict[str, int]) -> None:
    """Render one st.expander per unique citation (Phase 1 renderer, unchanged)."""
    expanders = render_citation_expanders(content, chip_map)
    for exp in expanders:
        with st.expander(exp["label"], expanded=False):
            st.markdown(
                f'<div class="drhp-snippet">{exp["snippet"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'[View DRHP page {exp["page_start"]} on SEBI →]({exp["source_url"]})'
            )
            st.markdown(
                f'<div class="drhp-snippet-metadata">{exp["metadata_footer"]}</div>',
                unsafe_allow_html=True,
            )


def render_grounded_block(field: GroundedAnswer | RefusalResponse, heading: str) -> None:
    """Render one of the 6 snapshot blocks (business/financials/risks/promoter/...).

    When `field` is a GroundedAnswer, reuses the Phase 1 chip + expander +
    per-answer-footer path unchanged. When `field` is a RefusalResponse
    (the DRHP did not disclose this — esp. SNAP-07 pledging), renders the
    honest .drhp-not-disclosed note instead of a fabricated value.

    Args:
        field: the SnapshotRecord field value.
        heading: the block's display heading (e.g. "Business").
    """
    st.markdown('<div class="drhp-snapshot-block">', unsafe_allow_html=True)
    st.markdown(
        f'<h2 class="drhp-snapshot-block-heading">{_html.escape(heading)}</h2>',
        unsafe_allow_html=True,
    )

    if isinstance(field, GroundedAnswer):
        rendered_html, chip_map = render_answer_with_chips(field)
        st.markdown(rendered_html, unsafe_allow_html=True)
        _render_expanders(field, chip_map)
        st.markdown(render_per_answer_footer(), unsafe_allow_html=True)
    else:
        _render_not_disclosed()

    st.markdown('</div>', unsafe_allow_html=True)


def render_use_of_proceeds_body(field: GroundedAnswer | RefusalResponse) -> None:
    """Render the use-of-proceeds line items BELOW the split bar.

    Block 5's focal element is render_split_bar() (called separately, first).
    This renders the cited fresh-issue-use line items that follow it, or the
    not-disclosed note if the DRHP did not disclose a use-of-proceeds
    breakdown at all.
    """
    if isinstance(field, GroundedAnswer):
        rendered_html, chip_map = render_answer_with_chips(field)
        st.markdown(rendered_html, unsafe_allow_html=True)
        _render_expanders(field, chip_map)
        st.markdown(render_per_answer_footer(), unsafe_allow_html=True)
    else:
        _render_not_disclosed()


def render_split_bar(ofs_fresh: dict | None) -> None:
    """Render the OFS-vs-fresh split bar — THE Phase 2 signal element.

    Focal element at the TOP of Block 5 (Use of Proceeds). Accent (#1E40AF)
    for the OFS segment, neutral grey (#F4F5F7) for the fresh segment — NO
    red/green anywhere (D2-06). Text percentage labels always present
    (WCAG 1.4.1 — color is never the sole differentiator).

    Args:
        ofs_fresh: {"ofs_pct": float, "fresh_pct": float, "source_claim_id": str|None}
            or None if the split could not be determined from the DRHP (honest
            not-disclosed path — caller should render the not-disclosed note
            instead of calling this function with None).
    """
    if ofs_fresh is None:
        _render_not_disclosed()
        return

    ofs_pct = ofs_fresh["ofs_pct"]
    fresh_pct = ofs_fresh["fresh_pct"]

    if ofs_pct >= 99.95:
        caption = SPLIT_BAR_PURE_OFS
    elif fresh_pct >= 99.95:
        caption = SPLIT_BAR_PURE_FRESH
    else:
        caption = SPLIT_BAR_CAPTION_TEMPLATE.format(fresh_pct=fresh_pct, ofs_pct=ofs_pct)

    aria_label = (
        f"Issue split: OFS {ofs_pct:g} percent, fresh issue {fresh_pct:g} percent."
    )

    st.markdown(
        f'<div class="drhp-split-bar-caption">{_html.escape(caption)}</div>',
        unsafe_allow_html=True,
    )

    ofs_label = f"OFS {ofs_pct:g}%" if ofs_pct >= 20 else ""
    fresh_label = f"Fresh {fresh_pct:g}%" if fresh_pct >= 20 else ""

    st.markdown(
        f'<div class="drhp-split-bar" role="img" aria-label="{_html.escape(aria_label, quote=True)}">'
        f'<div class="drhp-split-bar-ofs" style="width:{ofs_pct}%;">'
        f'<span>{_html.escape(ofs_label)}</span></div>'
        f'<div class="drhp-split-bar-fresh" style="width:{fresh_pct}%;">'
        f'<span>{_html.escape(fresh_label)}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# Row order locked to 02-UI-SPEC.md §Financials Rendering.
_FIN_ROW_LABELS: list[tuple[str, str]] = [
    ("revenue", "Revenue"),
    ("profit_loss", "Profit / (Loss)"),
    ("margin_pct", "Margin %"),
    ("debt", "Debt"),
    ("roe", "ROE"),
    ("roce", "ROCE"),
]


def _format_fin_value(value, row_key: str) -> str:
    """Format one financials cell: losses in parentheses (same color as profits),
    em-dash for missing, % suffix for margin/ROE/ROCE rows."""
    if value is None:
        return f'<span aria-label="Not disclosed in this DRHP">—</span>'
    if isinstance(value, (int, float)):
        if row_key in ("margin_pct", "roe", "roce"):
            return f"{value:.1f}%"
        if value < 0:
            return f"(₹{abs(value):,.0f} cr)"
        return f"₹{value:,.0f} cr"
    return _html.escape(str(value))


def render_financials_table(field: GroundedAnswer | RefusalResponse, years: list[str] | None = None,
                             rows: dict[str, dict[str, float | None]] | None = None) -> None:
    """Render the .drhp-fin-table — years as columns, 6 metric rows.

    Per 02-UI-SPEC.md §Financials Rendering: a TABLE, not sparklines.
    Negatives render as `(₹X cr)` in the SAME text color as a profit — NO
    red for losses. Missing cells render `—` with an aria-label.

    Args:
        field: the financials SnapshotRecord field (GroundedAnswer carrying
            the cited prose, or a RefusalResponse if the DRHP did not
            disclose restated financials at all).
        years: ordered fiscal-year column labels, e.g. ["FY22", "FY23", "FY24"].
            If None/empty, the table is not rendered (falls back to prose only).
        rows: {row_key: {year: value|None}} — structured financial figures.
            If None, only the cited prose (no structured table) is rendered —
            the Phase 2 seed snapshot JSON does not yet carry structured
            per-year figures (CODE-NOW-DEFER; the live precompute runbook
            will populate this once a structured-financials extractor lands).
    """
    if isinstance(field, GroundedAnswer):
        rendered_html, chip_map = render_answer_with_chips(field)
        st.markdown(rendered_html, unsafe_allow_html=True)
        _render_expanders(field, chip_map)
        st.markdown(render_per_answer_footer(), unsafe_allow_html=True)
    else:
        _render_not_disclosed()
        return

    if not years or not rows:
        return

    header_cells = "".join(f"<th scope='col'>{_html.escape(y)}</th>" for y in years)
    body_rows = []
    for row_key, row_label in _FIN_ROW_LABELS:
        row_values = rows.get(row_key, {})
        cells = "".join(
            f"<td>{_format_fin_value(row_values.get(y), row_key)}</td>" for y in years
        )
        body_rows.append(f"<tr><th scope='row'>{_html.escape(row_label)}</th>{cells}</tr>")

    table_html = (
        '<div class="drhp-fin-table-wrap"><table class="drhp-fin-table">'
        f'<thead><tr><th scope="col"></th>{header_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


def render_risk_block(field: GroundedAnswer | RefusalResponse) -> None:
    """Render prioritized risk items with descriptive "Risk N of M" counters.

    Per 02-UI-SPEC.md §Risk-Factors Block: prioritization order is the only
    "weighting" signal — no severity color, no red flag icon, no risk-score
    badge. If the field is a RefusalResponse (extraction failed), renders the
    standard not-disclosed note, never an empty list rendered as "no risks".

    Args:
        field: the risks SnapshotRecord field. Phase 2 (seeded data) stores
            ONE GroundedAnswer whose claims are the risk clusters; each claim
            becomes one Risk N of M item. M = len(field.claims).
    """
    if not isinstance(field, GroundedAnswer):
        _render_not_disclosed()
        return

    rendered_html, chip_map = render_answer_with_chips(field)
    total = len(field.claims) or 1

    # Render each claim as its own "Risk N of M" item by re-using the chip
    # numbering already computed for the full prose (keeps citation numbers
    # stable/consistent with the expanders below).
    for i, claim in enumerate(field.claims, start=1):
        counter = RISK_COUNTER_TEMPLATE.format(n=i, m=total)
        st.markdown(
            f'<div class="drhp-risk-item">'
            f'<div class="drhp-risk-item-counter">{_html.escape(counter)}</div>'
            f'<div>{_html.escape(claim.text)}'
            f'{_chip_for(claim.claim_id, chip_map)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _render_expanders(field, chip_map)
    st.markdown(render_per_answer_footer(), unsafe_allow_html=True)


def _chip_for(claim_id: str, chip_map: dict[str, int]) -> str:
    """Return a small inline chip HTML for one claim_id, or empty string."""
    from ui.chip import build_chip_html

    chip_n = chip_map.get(claim_id)
    if chip_n is None:
        return ""
    return " " + build_chip_html(claim_id, chip_n)
