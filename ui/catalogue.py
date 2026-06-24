"""
ui/catalogue.py — IPO card grid renderer (Wave 4, 02-05-PLAN.md Task 1).

Factual-only cards (P2-L1): issuer, sector, listing date, issue size in
lakh/crore. NO listing-gain %, NO badge, NO color verdict — a winner and a
flop must be visually identical in chrome (D2-07 hardest invariant).

Currently-open IPOs (status="open") sort first with a neutral "Open now"
text tag (no color, no badge fill).
"""
from __future__ import annotations

import html

import streamlit as st

from data.catalogue_loader import CatalogueIPO
from ui.copy import CATALOGUE_CARD_ARIA_LABEL_TEMPLATE, CATALOGUE_CARD_OPEN_NOW_TAG

_MONTH_NAMES = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
    "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
    "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}


def _format_listing_date(listing_date: str) -> str:
    """Format 'YYYY-MM' as 'Mon YYYY' (e.g. '2024-11' -> 'Nov 2024')."""
    parts = listing_date.split("-")
    if len(parts) != 2:
        return listing_date
    year, month = parts
    month_name = _MONTH_NAMES.get(month, month)
    return f"{month_name} {year}"


def _format_issue_size(issue_size_cr: int | None) -> str:
    """Format issue size in crore notation (lakh/crore, P2-L6)."""
    if issue_size_cr is None:
        return "Issue size not disclosed"
    return f"₹{issue_size_cr:,} cr"


def _card_html(ipo: CatalogueIPO) -> str:
    """Build the .drhp-ipo-card HTML for one IPO — factual rows only."""
    issuer = html.escape(ipo.issuer)
    sector = html.escape(ipo.sector)
    listed_str = _format_listing_date(ipo.listing_date)
    size_str = _format_issue_size(ipo.issue_size_cr)

    open_tag_html = ""
    if ipo.status == "open":
        open_tag_html = (
            f'<span class="drhp-ipo-card-open-tag">'
            f'{html.escape(CATALOGUE_CARD_OPEN_NOW_TAG)}</span>'
        )
        meta_line = f"Open · {html.escape(listed_str)} · {html.escape(size_str)}"
    else:
        meta_line = f"Listed {html.escape(listed_str)} · {html.escape(size_str)}"

    aria_label = html.escape(
        CATALOGUE_CARD_ARIA_LABEL_TEMPLATE.format(
            issuer=ipo.issuer, sector=ipo.sector, date=listed_str, size=size_str
        ),
        quote=True,
    )

    href = f"/snapshot?drhp_id={html.escape(ipo.drhp_id, quote=True)}"

    return (
        f'<a class="drhp-ipo-card" href="{href}" target="_self" '
        f'role="link" tabindex="0" aria-label="{aria_label}">'
        f'{open_tag_html}'
        f'<div class="drhp-ipo-card-issuer">{issuer}</div>'
        f'<div class="drhp-ipo-card-sector">{sector}</div>'
        f'<div class="drhp-ipo-card-meta">{meta_line}</div>'
        f'</a>'
    )


def render_catalogue_grid(ipos: list[CatalogueIPO]) -> None:
    """Render the responsive IPO card grid (.drhp-catalogue-grid).

    Desktop (>=1024px): 3 columns. Tablet (640-1023px): 2 columns.
    Mobile (<640px): 1 column (handled via CSS — st.columns(3) collapses
    to a single column automatically below Streamlit's internal breakpoint
    per the inherited Phase 1 mobile-first pattern).

    Currently-open IPOs (status="open") sort first; the rest preserve
    catalogue.json order (most-recent-listing-first per data convention).

    Args:
        ipos: list of validated CatalogueIPO models from load_catalogue().
    """
    open_ipos = [ipo for ipo in ipos if ipo.status == "open"]
    other_ipos = [ipo for ipo in ipos if ipo.status != "open"]
    ordered = open_ipos + other_ipos

    st.markdown('<div class="drhp-catalogue-grid">', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, ipo in enumerate(ordered):
        with cols[i % 3]:
            st.markdown(_card_html(ipo), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
