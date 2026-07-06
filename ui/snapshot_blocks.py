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

from agent.gmp_schema import GmpRecord
from agent.peer_schema import PeerCell, PeerMetric, PeerRecord
from agent.policies import IDF_BAND_THRESHOLDS
from agent.redflag_schema import RankedRisk, RedFlagRecord
from agent.schemas import GroundedAnswer, RefusalResponse
from pipelines.redflag_queries import REDFLAG_QUERIES
from ui.chip import render_answer_with_chips
from ui.disclaimer import render_per_answer_footer
from ui.expander import render_citation_expanders
from ui.format_inr import format_inr
from ui.methodology_pane import render_methodology_pane
from ui.copy import (
    CONFIDENCE_LABEL_TEMPLATE,
    FIELD_NOT_DISCLOSED_IN_DRHP_NOTE,
    FIELD_NOT_DISCLOSED_NOTE,
    FIELD_NUMERIC_GATE_BLOCKED,
    GLOSSARY,
    GMP_ABSENT,
    GMP_BLOCK_HEADING,
    GMP_CAVEAT,
    GMP_DISCLOSURE_BODY,
    GMP_DISCLOSURE_HEADING,
    GMP_RANGE_ARIA_TEMPLATE,
    GMP_RANGE_HEADLINE_TEMPLATE,
    GMP_SINGLE_SOURCE_NOTE,
    GMP_SOURCE_ASOF_TEMPLATE,
    GMP_SOURCE_ITEM_TEMPLATE,
    GMP_SOURCE_LINE_JOINER,
    PEER_ASOF_DRHP_LABEL,
    PEER_BLOCK_HEADING,
    PEER_BLOCK_SUBLINE,
    PEER_CELL_NOT_AVAILABLE_ARIA,
    PEER_COL_COMPANY,
    PEER_COL_EV_EBITDA,
    PEER_COL_PB,
    PEER_COL_PE,
    PEER_COL_ROE,
    PEER_EMPTY_STATE,
    PEER_IPO_ROW_TAG,
    PEER_NM_NOTE,
    PEER_PROVENANCE_LEGEND,
    PEER_SOURCE_NAMES,
    REDFLAG_BLOCK_HEADING,
    REDFLAG_BLOCK_SUBLINE,
    REDFLAG_FIELD_LABELS,
    RISK_BLOCK_HEADING,
    RISK_BLOCK_SUBLINE,
    RISK_COUNTER_TEMPLATE,
    RISK_SPECIFICITY_COUNTER_TEMPLATE,
    SPEC_METER_ARIA_TEMPLATE,
    SPECIFICITY_BAND_WORDS,
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
    """Format one financials cell via the shared format_inr utility (D4-07).

    Missing → em-dash with aria-label (preserved). Margin/ROE/ROCE rows are
    percentages (not rupees) → plain one-decimal `%`. The rupee rows
    (revenue/profit_loss/debt) are in CRORE units, so convert to rupees
    (* 1e7) before format_inr, which renders Indian grouping + lakh/crore and
    wraps negatives (losses) in parentheses in the SAME text colour as profits
    (no red). Fixes the second bare-Western `:,` FLAG-FORMAT site.
    """
    if value is None:
        return f'<span aria-label="Not disclosed in this DRHP">—</span>'
    if isinstance(value, (int, float)):
        if row_key in ("margin_pct", "roe", "roce"):
            return f"{value:.1f}%"
        return format_inr(value * 1e7)
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


# ===========================================================================
# Phase 3 — Red-flag signals table + IDF-ranked risk list (03-07-PLAN.md Task 1)
# ===========================================================================

# Meter fill saturates at the "issuer_specific" IDF threshold (agent.policies
# IDF_BAND_THRESHOLDS high bound) so the accent magnitude and the specificity
# WORD are driven by the SAME rubric — a risk at/above the issuer-specific
# threshold fills the bar fully. Fill is a magnitude indicator (more fill = more
# issuer-specific), NEVER a danger verdict (L3-1, T-03-14).
_SPEC_METER_MAX_IDF: float = IDF_BAND_THRESHOLDS[1]


def _spec_meter_pct(idf_score: float) -> int:
    """Normalize an IDF score to a 0-100 meter-fill percentage (clamped)."""
    if _SPEC_METER_MAX_IDF <= 0:
        return 0
    pct = idf_score / _SPEC_METER_MAX_IDF * 100.0
    return max(0, min(100, round(pct)))


def _render_redflag_refusal(refusal: RefusalResponse) -> None:
    """Render a red-flag row's honest absence value (L3-3 / L3-9).

    The confidence label is ALWAYS omitted for a refusal (D3-03). A refusal
    carrying the numeric-gate blocked-copy renders that copy (never an unsourced
    number, L3-9); any other refusal renders the honest not-disclosed note.
    """
    if refusal.explanation == FIELD_NUMERIC_GATE_BLOCKED:
        note = FIELD_NUMERIC_GATE_BLOCKED
    else:
        note = FIELD_NOT_DISCLOSED_IN_DRHP_NOTE
    st.markdown(
        f'<div class="drhp-redflag-value drhp-not-disclosed">{_html.escape(note)}</div>',
        unsafe_allow_html=True,
    )


def render_redflag_table(record: RedFlagRecord) -> None:
    """Render the Red-flag signals table — 7 stacked monochrome field rows.

    Per 03-UI-SPEC.md §Red-Flag Signal Table Contract: the 7 canonical fields
    render in the fixed REDFLAG_FIELD_LABELS order, ALWAYS all seven (never a
    hidden row). Each grounded field value renders via the UNCHANGED
    render_answer_with_chips (tabular-nums numeric values with inline citation
    chips), then its per-row citation expanders, then a plain
    `Confidence: high|medium|low` TEXT label (no pill, no color, L3-2), then the
    cached-only `Show your work` methodology pane (METHOD-01). A not-disclosed
    field renders the honest not-disclosed note with the confidence label OMITTED
    (L3-3/D3-03); a numeric-gate-blocked field renders the blocked-copy, never an
    unsourced number (L3-9). NO red/green, NO badge, NO severity icon, NO
    aggregate score anywhere (EXTRACT-01/02, L3-1).
    """
    # Real Streamlit container as the card — a split open/close <div> across two
    # st.markdown calls renders an EMPTY styled box (Streamlit isolates each
    # markdown in its own DOM block), which is why a raw wrapper showed a blank
    # white bar. st.container(border=True) actually wraps the rows.
    with st.container(border=True):
        st.markdown(
            f'<h2 class="drhp-snapshot-block-heading">{_html.escape(REDFLAG_BLOCK_HEADING)}</h2>',
            unsafe_allow_html=True,
        )
        st.caption(REDFLAG_BLOCK_SUBLINE)

        for field_key, label in REDFLAG_FIELD_LABELS.items():
            field = record.fields.get(field_key)
            with st.container():
                st.markdown(
                    f'<div class="drhp-redflag-label">{_html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )

                if field is None:
                    # Field not present in the cached record — honest absence
                    # (never a fabricated row); confidence omitted.
                    st.markdown(
                        f'<div class="drhp-redflag-value drhp-not-disclosed">'
                        f'{_html.escape(FIELD_NOT_DISCLOSED_IN_DRHP_NOTE)}</div>',
                        unsafe_allow_html=True,
                    )
                elif isinstance(field.value, GroundedAnswer):
                    rendered_html, chip_map = render_answer_with_chips(field.value)
                    st.markdown(
                        f'<div class="drhp-redflag-value">{rendered_html}</div>',
                        unsafe_allow_html=True,
                    )
                    _render_expanders(field.value, chip_map)
                    if field.confidence_tier is not None:
                        st.markdown(
                            f'<div class="drhp-confidence-label">'
                            f'{_html.escape(CONFIDENCE_LABEL_TEMPLATE.format(confidence_tier=field.confidence_tier))}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    # METHOD-01: cached-only Show-your-work pane on each field.
                    # key=field_key keeps each pane's toggle id unique.
                    render_methodology_pane(
                        query=REDFLAG_QUERIES.get(field_key, ""),
                        grounded_answer=field.value,
                        confidence_tier=field.confidence_tier,
                        confidence_score=field.confidence_score,
                        key=f"redflag_{field_key}",
                    )
                else:
                    _render_redflag_refusal(field.value)


def _claim_lookup(record: RedFlagRecord) -> dict:
    """Map claim_id -> (Claim, parent GroundedAnswer, field_key) over grounded fields.

    RankedRisk carries only claim_id/idf_score/specificity_band, so the risk
    text + citations are resolved back to the originating Claim here.
    """
    lookup: dict = {}
    for field_key, field in record.fields.items():
        value = field.value
        if isinstance(value, GroundedAnswer):
            for claim in value.claims:
                lookup[claim.claim_id] = (claim, value, field_key)
    return lookup


def render_idf_risk_list(ranked_risks: list[RankedRisk], record: RedFlagRecord) -> None:
    """Render the SINGLE IDF-ranked risk list (supersedes the Phase 2 ordering).

    Per 03-UI-SPEC.md §IDF-Ranked Risk List Contract (L3-4): one ranked list,
    descending idf_score (most issuer-specific first), each item carrying the
    `Risk n of m · {specificity}` counter, a monochrome `.drhp-spec-meter`
    (accent fill proportional to the normalized IDF on a neutral track — more
    fill = more issuer-specific, NEVER a danger verdict, T-03-14), a text `{pct}%`
    label, and the cited risk text (chips + citation expander) via the UNCHANGED
    render_answer_with_chips. Industry-standard risks render LOWER in the SAME
    list (no collapsed bucket). NO red/green anywhere (L3-1).
    """
    lookup = _claim_lookup(record)
    total = len(ranked_risks)

    st.markdown('<div class="drhp-snapshot-block">', unsafe_allow_html=True)
    st.markdown(
        f'<h2 class="drhp-snapshot-block-heading">{_html.escape(RISK_BLOCK_HEADING)}</h2>',
        unsafe_allow_html=True,
    )
    st.caption(RISK_BLOCK_SUBLINE)

    # ranked_risks arrives ordered by descending idf_score (pipeline contract);
    # re-sort defensively so the render never depends on caller ordering.
    ordered = sorted(ranked_risks, key=lambda r: r.idf_score, reverse=True)

    for i, risk in enumerate(ordered, start=1):
        specificity = SPECIFICITY_BAND_WORDS.get(
            risk.specificity_band, risk.specificity_band
        )
        counter = RISK_SPECIFICITY_COUNTER_TEMPLATE.format(
            n=i, m=total, specificity=specificity
        )
        pct = _spec_meter_pct(risk.idf_score)

        st.markdown('<div class="drhp-risk-item">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="drhp-risk-item-counter">{_html.escape(counter)}</div>',
            unsafe_allow_html=True,
        )

        # Monochrome specificity meter — accent fill on neutral track (copies the
        # render_split_bar grammar), always accompanied by a text % + word label.
        aria_label = SPEC_METER_ARIA_TEMPLATE.format(pct=pct)
        st.markdown(
            f'<div class="drhp-spec-meter" role="img" '
            f'aria-label="{_html.escape(aria_label, quote=True)}">'
            f'<div class="drhp-spec-meter-fill" style="width:{pct}%;"></div>'
            f'</div>'
            f'<div class="drhp-spec-meter-label">{pct}% · {_html.escape(specificity)}</div>',
            unsafe_allow_html=True,
        )

        entry = lookup.get(risk.claim_id)
        if entry is not None:
            claim, _parent, _field_key = entry
            # Isolate this risk's citation to a single-claim GroundedAnswer so the
            # chip numbering + its expander are scoped to this one item; reuses the
            # UNCHANGED render_answer_with_chips / expander renderers.
            single = GroundedAnswer(
                answer_prose=f"{{{{{claim.claim_id}}}}}",
                claims=[claim],
            )
            _rendered, chip_map = render_answer_with_chips(single)
            st.markdown(
                f'<div class="drhp-risk-item-text">{_html.escape(claim.text)}'
                f'{_chip_for(claim.claim_id, chip_map)}</div>',
                unsafe_allow_html=True,
            )
            _render_expanders(single, chip_map)

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ===========================================================================
# Phase 4 — Peer-multiples comparison table + glossary helper (04-05-PLAN.md)
# ===========================================================================

# Fixed column order (04-UI-SPEC.md R-2): Company · P/E · P/B · EV/EBITDA · ROE.
# The (metric_key, header_copy) pairs drive both the <thead> and each row's cells.
_PEER_METRIC_COLUMNS: list[tuple[str, str]] = [
    ("pe", PEER_COL_PE),
    ("pb", PEER_COL_PB),
    ("ev_ebitda", PEER_COL_EV_EBITDA),
    ("roe", PEER_COL_ROE),
]


def glossary_term(term: str) -> str:
    """Return HTML wrapping `term` in the pure-CSS glossary tooltip (UI-04, R-1).

    The trigger is an inline `.drhp-glossary` span (dotted underline, tabindex=0,
    role="button") whose sibling `.drhp-glossary-pop` popover is revealed by CSS
    on :hover / :focus / :focus-within — NO JavaScript. Definitions come from the
    scrubber-guarded ui.copy.GLOSSARY map (D4-08). An unknown term degrades to its
    HTML-escaped text (never an exception). Reusable across any rendered prose.
    """
    entry = GLOSSARY.get(term)
    if entry is None:
        return _html.escape(term)
    label, definition = entry
    slug = "".join(ch if ch.isalnum() else "-" for ch in term.lower()).strip("-")
    pop_id = f"gl-{slug}"
    return (
        f'<span class="drhp-glossary" tabindex="0" role="button" '
        f'aria-describedby="{pop_id}">{_html.escape(label)}'
        f'<span class="drhp-glossary-pop" role="tooltip" id="{pop_id}">'
        f'{_html.escape(definition)}</span></span>'
    )


def _peer_source_sup(source: str | None) -> str:
    """Muted superscript provenance flag for one cell's source letter (R-3).

    The `<sup>` is muted + unfilled — deliberately distinct from the accent,
    filled citation chip. Its aria-label carries the FULL source name so a screen
    reader never has to resolve a single letter (04-UI-SPEC a11y). No colour
    encodes the source (monochrome invariant); an unknown source renders nothing.
    """
    if source is None:
        return ""
    name = PEER_SOURCE_NAMES.get(source, source)
    return (
        f'<sup class="drhp-provenance-flag" '
        f'aria-label="source: {_html.escape(name, quote=True)}">'
        f'{_html.escape(source)}</sup>'
    )


def _peer_missing_cell() -> str:
    """Honest `—` for a value missing from EVERY source (D4-05); never a zero."""
    return (
        f'<span aria-label="{_html.escape(PEER_CELL_NOT_AVAILABLE_ARIA, quote=True)}">'
        f'—</span>'
    )


def _peer_nm_cell(source: str | None) -> str:
    """`NM` for a negative/undefined ratio (loss-making issuer), never a red number.

    Carries the glossary-popover note `Not meaningful — the company reported a
    loss` via the SAME pure-CSS .drhp-glossary mechanism (R-1), plus its per-cell
    provenance flag. Distinguishable from both a real value and a missing cell.
    """
    return (
        f'<span class="drhp-glossary" tabindex="0" role="button" '
        f'aria-label="{_html.escape(PEER_NM_NOTE, quote=True)}">NM'
        f'<span class="drhp-glossary-pop" role="tooltip">'
        f'{_html.escape(PEER_NM_NOTE)}</span></span>'
        f'{_peer_source_sup(source)}'
    )


def _format_peer_ratio(value: float, metric_key: str) -> str:
    """One-decimal ratio (ROE as `%`); negatives in parentheses, SAME colour.

    No red for negatives — the inherited financials no-red-for-losses rule
    (D4-09). ROE is stored as a percent (×100 at precompute, 04-03).
    """
    neg = value < 0
    magnitude = abs(value)
    if metric_key == "roe":
        s = f"{magnitude:.1f}%"
    else:
        s = f"{magnitude:.1f}"
    return f"({s})" if neg else s


def _render_peer_cell_value(cell: PeerCell | None, metric_key: str) -> str:
    """Render ONE (company, metric, as-of) cell's inner HTML honestly.

    Order of honesty (04-UI-SPEC §cell edge cases): NM sentinel first (a
    loss-making ratio), then missing (`—`), then the value + provenance flag.
    """
    if cell is None:
        return _peer_missing_cell()
    if cell.not_meaningful:
        return _peer_nm_cell(cell.source)
    if cell.value is None:
        return _peer_missing_cell()
    return f"{_format_peer_ratio(cell.value, metric_key)}{_peer_source_sup(cell.source)}"


def _render_peer_metric_cell(metric: PeerMetric | None, metric_key: str) -> str:
    """Render a full table cell: the current-market value + an optional as-of-DRHP.

    Carries BOTH dimensions where the record supplies them (D4-05): the headline
    is the current-market value (per the sub-line); a muted secondary
    `… as of DRHP` line renders when the drhp_date cell holds a value or the NM
    sentinel. A metric a company has no cell for renders an honest `—`.
    """
    if metric is None:
        return _peer_missing_cell()

    parts = [
        f'<span class="drhp-peer-current">'
        f'{_render_peer_cell_value(metric.current, metric_key)}</span>'
    ]
    drhp_cell = metric.drhp_date
    if drhp_cell is not None and (drhp_cell.value is not None or drhp_cell.not_meaningful):
        parts.append(
            f'<span class="drhp-peer-asof">'
            f'{_render_peer_cell_value(drhp_cell, metric_key)} '
            f'{_html.escape(PEER_ASOF_DRHP_LABEL)}</span>'
        )
    return "".join(parts)


def _build_peer_table_html(record: PeerRecord) -> str:
    """Build the self-contained `<table class="drhp-peer-table">` HTML (one call).

    Rows = companies (the IPO's own row first, tagged + neutral-filled); columns =
    Company · P/E · P/B · EV/EBITDA · ROE. Every scraped company name is
    HTML-escaped (T-04-05-XSS) before interpolation. Wrapped in the inherited
    .drhp-fin-table-wrap so the company column stays sticky-left while the metric
    columns scroll (R-2). A single st.markdown call renders this — never a split
    div (the Phase 3 white-bar lesson).
    """
    header_cells = "".join(
        f'<th scope="col">{_html.escape(header)}</th>'
        for _key, header in _PEER_METRIC_COLUMNS
    )
    thead = (
        f'<thead><tr><th scope="col">{_html.escape(PEER_COL_COMPANY)}</th>'
        f'{header_cells}</tr></thead>'
    )

    body_rows: list[str] = []
    for company in record.companies:
        metrics_by_key = {m.metric: m for m in company.metrics}
        # T-04-05-XSS: escape the scraped/DRHP-derived peer name before interpolation.
        name_html = _html.escape(company.name)
        if company.is_ipo:
            name_html += (
                f'<span class="drhp-peer-ipo-tag">'
                f'{_html.escape(PEER_IPO_ROW_TAG)}</span>'
            )
        row_class = ' class="drhp-peer-ipo-row"' if company.is_ipo else ""
        cells = "".join(
            f'<td>{_render_peer_metric_cell(metrics_by_key.get(key), key)}</td>'
            for key, _header in _PEER_METRIC_COLUMNS
        )
        body_rows.append(
            f'<tr{row_class}><th scope="row">{name_html}</th>{cells}</tr>'
        )

    return (
        '<div class="drhp-fin-table-wrap"><table class="drhp-peer-table">'
        f'{thead}<tbody>{"".join(body_rows)}</tbody></table></div>'
    )


def render_peer_table(record: PeerRecord) -> None:
    """Render the peer-multiples comparison block (PEER-01, PEER-02, D4-04/05/06/09).

    Wrapped in `st.container(border=True)` — NEVER a split open/close <div> across
    two st.markdown calls (the Phase 3 empty-white-bar lesson). Renders entirely
    from the CACHED PeerRecord (04-03) — NO live source call happens here.

    Structure:
      - heading `Comparison with listed peers`;
      - when the DRHP disclosed a peer set (GroundedAnswer): the sub-line, the
        peer-SET citation via the UNCHANGED render_answer_with_chips / expander
        path (the ONLY accent element in the block, D4-04), then the sticky-left
        peer table + the muted per-cell provenance legend (R-3);
      - when the peer set is a RefusalResponse: the honest D4-06 empty-state note
        `This DRHP disclosed no listed-peer comparison.` — no table, no fabrication.

    No red/green anywhere; a low and a high multiple render identically (D4-09).
    """
    with st.container(border=True):
        st.markdown(
            f'<h2 class="drhp-snapshot-block-heading">'
            f'{_html.escape(PEER_BLOCK_HEADING)}</h2>',
            unsafe_allow_html=True,
        )

        peer_set = record.peer_set
        if not isinstance(peer_set, GroundedAnswer):
            # D4-06 honest empty-state — the DRHP named no listed peers.
            st.markdown(
                f'<div class="drhp-not-disclosed">'
                f'{_html.escape(PEER_EMPTY_STATE)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(render_per_answer_footer(), unsafe_allow_html=True)
            return

        # Sub-line + the peer-SET citation (the only accent element, D4-04) via the
        # UNCHANGED Phase 1 chip + expander renderers.
        st.caption(PEER_BLOCK_SUBLINE)
        rendered_html, chip_map = render_answer_with_chips(peer_set)
        st.markdown(
            f'<div class="drhp-peer-citation">{rendered_html}</div>',
            unsafe_allow_html=True,
        )
        _render_expanders(peer_set, chip_map)

        # The table — a SINGLE self-contained st.markdown call (never a split div).
        st.markdown(_build_peer_table_html(record), unsafe_allow_html=True)

        # Per-cell provenance legend (R-3), then the inherited per-block disclaimer.
        st.markdown(
            f'<div class="drhp-provenance-legend">'
            f'{_html.escape(PEER_PROVENANCE_LEGEND)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(render_per_answer_footer(), unsafe_allow_html=True)


# ===========================================================================
# Phase 4 — Read-only GMP block (04-06-PLAN.md Task 2, 04-UI-SPEC.md R-4)
# ===========================================================================
#
# The QUIETEST surface in the app (D4-02): monochrome, NO accent, NO red/green,
# no up/down arrow, no single big authoritative number — the cross-source spread
# is the honesty signal (D4-01). Renders ONLY from the cached GmpRecord passed in
# (04-04) — no live scrape happens here. GMP-02/D4-03: this render path imports
# nothing from any model/prediction module (pinned by the Task 2 inspect audit).


def _gmp_source_line_html(record: GmpRecord) -> str:
    """Build the Small muted per-source list: `{source} {value} · … · as of {date}`.

    Each ₹ value routes through format_inr (safe numeric string); every scraped
    source label is _html.escape'd before interpolation (T-04-06-XSS). The as-of
    date is a controlled ISO string, escaped defensively.
    """
    items = [
        GMP_SOURCE_ITEM_TEMPLATE.format(
            source=_html.escape(quote.source), value=format_inr(quote.value)
        )
        for quote in record.quotes
    ]
    asof = GMP_SOURCE_ASOF_TEMPLATE.format(date=_html.escape(record.as_of))
    line = GMP_SOURCE_LINE_JOINER.join([*items, asof])
    return f'<div class="drhp-gmp-source-line">{line}</div>'


def _render_gmp_spread(record: GmpRecord) -> None:
    """Render the monochrome multi-source range strip — the spread IS the point.

    A single self-contained st.markdown (never a split div): the min–max headline
    (₹ via format_inr, deliberately NOT bold), then a `surface-secondary` track
    carrying one muted tick per aggregator positioned by inline `left:%`, then the
    per-source list. `role="img"` + a text aria-label states the spread so it is
    never conveyed by tick position alone (WCAG 1.4.1). NO accent, no red/green.
    """
    spread = record.spread()  # GmpSpread with n >= 2 (guaranteed by caller).
    low_str = format_inr(spread.low)
    high_str = format_inr(spread.high)
    headline = GMP_RANGE_HEADLINE_TEMPLATE.format(
        low=low_str, high=high_str, n=spread.n
    )
    aria = GMP_RANGE_ARIA_TEMPLATE.format(low=low_str, high=high_str, n=spread.n)

    span = spread.high - spread.low
    ticks = []
    for quote in record.quotes:
        pct = 50.0 if span <= 0 else (quote.value - spread.low) / span * 100.0
        pct = max(0.0, min(100.0, pct))
        ticks.append(f'<span class="drhp-gmp-tick" style="left:{pct:g}%;"></span>')

    st.markdown(
        f'<div class="drhp-gmp-range-headline">{_html.escape(headline)}</div>'
        f'<div class="drhp-gmp-range" role="img" '
        f'aria-label="{_html.escape(aria, quote=True)}">'
        f'{"".join(ticks)}</div>'
        f'{_gmp_source_line_html(record)}',
        unsafe_allow_html=True,
    )


def _render_gmp_single_source(record: GmpRecord) -> None:
    """Render the single-source state: the one value + an explicit no-cross-check note.

    Absence of divergence is STATED, not hidden (04-UI-SPEC §States). No range
    strip (a spread needs >= 2 sources), no fabricated second quote.
    """
    st.markdown(
        f'{_gmp_source_line_html(record)}'
        f'<div class="drhp-gmp-caveat">{_html.escape(GMP_SINGLE_SOURCE_NOTE)}</div>',
        unsafe_allow_html=True,
    )


def render_gmp_block(record: GmpRecord) -> None:
    """Render the read-only grey-market-premium block (GMP-01, D4-01/02/03).

    The last read block on the snapshot page and, by design, the calmest: wrapped
    in `st.container(border=True)` (never a split div — the Phase 3 white-bar
    lesson), monochrome, with NO accent anywhere. Renders ENTIRELY from the CACHED
    GmpRecord (04-04) — no live scrape happens here, and this module imports no
    model/prediction code (GMP-02, D4-03).

    Structure, top to bottom (04-UI-SPEC R-4):
      - heading `Grey-market premium (unofficial)` with the GMP glossary tooltip;
      - the persistent caveat (always visible, never collapsed);
      - the state body:
          * absent (`quotes == []`, the COMMON already-listed case) → the honest
            `.drhp-not-disclosed` note (never a zero, never an error);
          * single-source (`len == 1`) → the value + the no-cross-source note;
          * default (>= 2 sources) → the monochrome spread strip (the honesty
            signal);
      - the `What is GMP? Why we don't trust it` explanation behind a collapsed
        `st.expander` with a UNIQUE key;
      - the inherited per-block disclaimer.
    """
    with st.container(border=True):
        # Heading + persistent caveat in ONE self-contained markdown. The GMP
        # glossary term (04-05 helper) rides the heading; glossary_term returns
        # trusted CSS-tooltip HTML (already escaped internally) so it is not
        # re-escaped. The heading is rendered calm — no bold headline number.
        st.markdown(
            f'<div class="drhp-gmp-block">'
            f'<h2 class="drhp-snapshot-block-heading">'
            f'{_html.escape(GMP_BLOCK_HEADING)} {glossary_term("GMP")}</h2>'
            f'<div class="drhp-gmp-caveat">{_html.escape(GMP_CAVEAT)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if record.is_absent:
            st.markdown(
                f'<div class="drhp-not-disclosed">{_html.escape(GMP_ABSENT)}</div>',
                unsafe_allow_html=True,
            )
        elif record.is_single_source:
            _render_gmp_single_source(record)
        else:
            _render_gmp_spread(record)

        # The disclosure — default-collapsed, a UNIQUE per-drhp_id key so the
        # toggle never collides with another expander (StreamlitDuplicateElementId).
        with st.expander(
            GMP_DISCLOSURE_HEADING,
            expanded=False,
            key=f"gmp_disclosure_{record.drhp_id}",
        ):
            st.markdown(
                f'<div class="drhp-gmp-disclosure-body">'
                f'{_html.escape(GMP_DISCLOSURE_BODY)}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(render_per_answer_footer(), unsafe_allow_html=True)
