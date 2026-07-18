"""
ui/forecast_block.py — the Phase 5 listing-day-forecast render (FCAST-01,
FCAST-04, GMP-03, UI-03; 05-UI-SPEC.md §Visuals — Forecast Section Contract).

The phase's HEADLINE user-facing surface, rendered ENTIRELY from a cached
ForecastRecord (data/forecasts/<drhp_id>.json) plus the cached GmpRecord for the
marker only. No model/training call happens at render time and this module
imports NO model/prediction/feature/historical module — it is the render side of
the FCAST-02 cache-only isolation seam, pinned by tests/unit/test_forecast_
isolation.py. The band WIDTH is the dominant visual; there is NO point-estimate-
as-headline, NO green/red, NO badge (P21). Empirical coverage / MAE / per-year
RMSE are ALWAYS visible (P17, FCAST-04). abstain / not-covered / no-GMP / error
each render an honest note — never a fabricated band, metric, or GMP.

The GMP-implied listing-day return is a DISPLAY-layer conversion
(gmp_premium / issue_price * 100) reading only the cached GMP premium + the
cached issue price; it is never a model feature (GMP-02 / D4-03 / FCAST-02). If
the issue price is unavailable the marker + gap line are omitted (the band still
renders) with the honest no-gap note.

Streamlit runtime constraints honoured (the Phase 3 white-bar lesson): the block
is ONE st.container(border=True, key="drhpcard-forecast") (never a split div);
the plot (axis + band + median tick + 0% rule + GMP marker + scale) is ONE
self-contained st.markdown with markers positioned by inline left:%. Every
record-sourced string is html.escape'd before interpolation (T-05-07-XSS);
interpolated numeric strings are formatted floats (safe).
"""
from __future__ import annotations

import html as _html
import math
import statistics
from typing import TYPE_CHECKING

import streamlit as st

from ui.copy import (
    FORECAST_BACKTEST_STAT_LABEL,
    FORECAST_BAND_ARIA_TEMPLATE,
    FORECAST_BLOCK_HEADING,
    FORECAST_COVERAGE_HONESTY_NOTE,
    FORECAST_COVERAGE_STAT_LABEL,
    FORECAST_DIRECTION_ABOVE,
    FORECAST_DIRECTION_BELOW,
    FORECAST_EMPTY_ABSTAIN,
    FORECAST_EMPTY_NOT_COVERED,
    FORECAST_ERROR_STATE,
    FORECAST_FRAMING_SUBLINE,
    FORECAST_GMP_ARIA_TEMPLATE,
    FORECAST_GMP_BASIS_TITLE_TEMPLATE,
    FORECAST_GMP_GAP_TEMPLATE,
    FORECAST_INTERVAL_CAPTION_TEMPLATE,
    FORECAST_MAE_STAT_LABEL,
    FORECAST_MEDIAN_ANNOTATION_TEMPLATE,
    FORECAST_METRIC_NA,
    FORECAST_METRIC_NA_ARIA,
    FORECAST_MODEL_CARD_LINK,
    FORECAST_NO_GMP_NOTE,
    FORECAST_RMSE_TABLE_CAPTION,
    FORECAST_RMSE_TH_RMSE,
    FORECAST_RMSE_TH_YEAR,
    FORECAST_TESTED_EYEBROW,
    FORECAST_ZERO_LABEL,
)
from ui.disclaimer import render_per_answer_footer
from ui.format_inr import format_inr

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime import cost
    from agent.forecast_schema import ForecastRecord
    from agent.gmp_schema import GmpRecord

# The href for the model-card link — the /methodology page is the model card's
# in-app home (FCAST-05, L5-3).
_MODEL_CARD_HREF = "/methodology"


# ===========================================================================
# D-1 — deterministic axis-domain + marker-position math (pure helpers)
# ===========================================================================


def _floor_to_5(x: float) -> float:
    """Round x DOWN to the nearest multiple of 5 (outward-rounding domain floor)."""
    return math.floor(x / 5.0) * 5.0


def _ceil_to_5(x: float) -> float:
    """Round x UP to the nearest multiple of 5 (outward-rounding domain ceiling)."""
    return math.ceil(x / 5.0) * 5.0


def _domain(anchors) -> tuple[float, float]:
    """Compute the visible return-axis domain [domain_lo, domain_hi] (D-1).

    anchors: the anchor set A = {0, interval_low, interval_high, median}
        (plus {gmp_implied} when a GMP marker is present). 0 is always an anchor,
        so it always sits inside the domain.

    pad = max(2.0, 0.08 * (raw_max - raw_min)); the domain rounds OUTWARD to the
    nearest 5 points so every IPO renders on a consistent, breathing-room axis.
    """
    a = list(anchors)
    raw_min = min(a)
    raw_max = max(a)
    pad = max(2.0, 0.08 * (raw_max - raw_min))
    domain_lo = _floor_to_5(raw_min - pad)
    domain_hi = _ceil_to_5(raw_max + pad)
    if domain_hi <= domain_lo:
        # Degenerate guard (all anchors identical) — keep a non-zero span.
        domain_hi = domain_lo + 5.0
    return domain_lo, domain_hi


def pos(v: float, lo: float, hi: float) -> float:
    """Map a return value v to a left:% position on the axis, clamped to [0, 100]."""
    if hi <= lo:
        return 0.0
    return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100.0))


def _gmp_implied_return_pct(
    gmp_premium_rupees: float, issue_price_rupees: float | None
) -> float | None:
    """DISPLAY-layer GMP-implied listing-day return: premium / issue_price * 100.

    Reads only the cached GMP premium + the cached issue price — never a model
    feature (GMP-02 / D4-03 / FCAST-02). Returns None when the issue price is
    unavailable or zero, in which case the caller omits the marker + gap line (the
    band still renders) with the honest no-gap note.
    """
    if issue_price_rupees is None or issue_price_rupees == 0:
        return None
    return gmp_premium_rupees / issue_price_rupees * 100.0


# ===========================================================================
# Number + string formatting (returns/coverage in %, errors in points; no ₹)
# ===========================================================================


def _fmt1(x: float) -> str:
    """One-decimal fixed formatting for every figure (tabular-nums aligns it)."""
    return f"{x:.1f}"


def _pct_left(v: float, lo: float, hi: float) -> str:
    """A trimmed left:% string for inline positioning (no trailing zeros)."""
    return f"{pos(v, lo, hi):g}"


def _resolve_gmp_implied(
    gmp_record: "GmpRecord | None", issue_price: float | None
) -> tuple[float | None, float | None]:
    """Resolve the representative GMP premium (₹) + its implied return (%).

    Uses the MEDIAN of the cached aggregator quotes as the single representative
    premium (robust across a 2-3 source spread), then converts it in the display
    layer. Returns (None, None) — the marker + gap line are omitted, the band
    still renders — when no GMP is reported or the issue price is unavailable.
    """
    if gmp_record is None or not gmp_record.quotes:
        return None, None
    premium = statistics.median([q.value for q in gmp_record.quotes])
    implied = _gmp_implied_return_pct(premium, issue_price)
    if implied is None:
        return None, None
    return premium, implied


# ===========================================================================
# HTML builders (pure; return strings — testable without a Streamlit runtime)
# ===========================================================================


def _plot_html(
    record: "ForecastRecord",
    gmp_implied: float | None,
    gmp_premium: float | None,
    issue_price: float | None,
) -> str:
    """Build the ONE self-contained plot markup string (D-1/D-2).

    A neutral axis track carrying the amber interval band, the faint neutral
    median tick, the full-height 0% rule, and (when a GMP is present) the hollow
    muted GMP diamond + stem — all absolutely positioned by inline left:%. Axis-end
    scale labels and the Small muted median / 0% annotations sit beneath. role=img
    + a full aria-label state the interval in WORDS (WCAG 1.4.1).
    """
    interval = record.interval
    assert interval is not None  # covered record only (caller guards abstain)
    low = interval.low_pct
    high = interval.high_pct
    median = interval.median_pct
    width = interval.width_pts

    anchors = [0.0, low, high, median]
    if gmp_implied is not None:
        anchors.append(gmp_implied)
    lo, hi = _domain(anchors)

    band_left = _pct_left(low, lo, hi)
    band_width = f"{pos(high, lo, hi) - pos(low, lo, hi):g}"

    band_aria = FORECAST_BAND_ARIA_TEMPLATE.format(
        low=_fmt1(low), high=_fmt1(high), median=_fmt1(median), width=_fmt1(width)
    )

    markers = [
        # 0% baseline — a full-height neutral rule (D-2).
        f'<span class="drhp-forecast-zero" style="left:{_pct_left(0.0, lo, hi)}%;"></span>',
        # The interval band — the ONE amber element; width is the message.
        f'<span class="drhp-forecast-band" '
        f'style="left:{band_left}%;width:{band_width}%;"></span>',
        # Median tick — a short faint neutral stub (never a headline).
        f'<span class="drhp-forecast-median" '
        f'style="left:{_pct_left(median, lo, hi)}%;"></span>',
    ]

    if gmp_implied is not None:
        gmp_pct = _pct_left(gmp_implied, lo, hi)
        delta = abs(gmp_implied - median)
        direction = (
            FORECAST_DIRECTION_ABOVE
            if gmp_implied >= median
            else FORECAST_DIRECTION_BELOW
        )
        gmp_aria = FORECAST_GMP_ARIA_TEMPLATE.format(
            gmp=_fmt1(gmp_implied), delta=_fmt1(delta), direction=direction
        )
        # Native title= provenance: the ₹ basis of the display-layer conversion,
        # routed through the ONE rupee formatter. Kept OFF the visible % chrome.
        title_attr = ""
        if gmp_premium is not None and issue_price is not None:
            basis = FORECAST_GMP_BASIS_TITLE_TEMPLATE.format(
                premium=format_inr(gmp_premium), issue_price=format_inr(issue_price)
            )
            title_attr = f' title="{_html.escape(basis, quote=True)}"'
        markers.append(
            f'<span class="drhp-forecast-gmp-stem" style="left:{gmp_pct}%;"></span>'
        )
        markers.append(
            f'<span class="drhp-forecast-gmp" role="img" '
            f'aria-label="{_html.escape(gmp_aria, quote=True)}"'
            f'{title_attr} style="left:{gmp_pct}%;"></span>'
        )

    median_annotation = FORECAST_MEDIAN_ANNOTATION_TEMPLATE.format(median=_fmt1(median))

    return (
        f'<div class="drhp-forecast-plot" role="img" '
        f'aria-label="{_html.escape(band_aria, quote=True)}">'
        f'<div class="drhp-forecast-axis">{"".join(markers)}</div>'
        f'<div class="drhp-forecast-scale">'
        f'<span>{_fmt1(lo)}%</span><span>{_fmt1(hi)}%</span>'
        f'</div>'
        f'<div class="drhp-forecast-scale">'
        f'<span class="drhp-forecast-median-label">'
        f'{_html.escape(median_annotation)}</span>'
        f'<span class="drhp-forecast-zero-label">'
        f'{_html.escape(FORECAST_ZERO_LABEL)}</span>'
        f'</div>'
        f'</div>'
    )


def _caption_html(record: "ForecastRecord") -> str:
    """The plain-language interval caption (Body) — the section's real headline."""
    interval = record.interval
    assert interval is not None
    text = FORECAST_INTERVAL_CAPTION_TEMPLATE.format(
        low=_fmt1(interval.low_pct),
        high=_fmt1(interval.high_pct),
        width=_fmt1(interval.width_pts),
    )
    return f'<div class="drhp-forecast-caption">{_html.escape(text)}</div>'


def _gap_html(record: "ForecastRecord", gmp_implied: float | None) -> str:
    """The GMP-vs-model gap line (labeled delta) or the honest no-GMP note."""
    interval = record.interval
    assert interval is not None
    if gmp_implied is None:
        return (
            f'<div class="drhp-forecast-gap">'
            f'{_html.escape(FORECAST_NO_GMP_NOTE)}</div>'
        )
    median = interval.median_pct
    delta = abs(gmp_implied - median)
    direction = (
        FORECAST_DIRECTION_ABOVE if gmp_implied >= median else FORECAST_DIRECTION_BELOW
    )
    text = FORECAST_GMP_GAP_TEMPLATE.format(
        gmp=_fmt1(gmp_implied), delta=_fmt1(delta), direction=direction
    )
    return f'<div class="drhp-forecast-gap">{_html.escape(text)}</div>'


def _rmse_table_html(per_year_rmse: dict[str, float]) -> str:
    """A real <table> (Year / RMSE, th scope=col) — always visible, SR-navigable.

    A genuinely-absent year renders the em-dash with aria-label='Not available'
    (never a fabricated number, never a hidden row — FCAST-04).
    """
    header = (
        f'<tr>'
        f'<th scope="col">{_html.escape(FORECAST_RMSE_TH_YEAR)}</th>'
        f'<th scope="col">{_html.escape(FORECAST_RMSE_TH_RMSE)}</th>'
        f'</tr>'
    )
    rows = []
    for year in sorted(per_year_rmse):
        value = per_year_rmse.get(year)
        if value is None:
            cell = (
                f'<td aria-label="{_html.escape(FORECAST_METRIC_NA_ARIA, quote=True)}">'
                f'{_html.escape(FORECAST_METRIC_NA)}</td>'
            )
        else:
            cell = f"<td>{_fmt1(value)}</td>"
        rows.append(f"<tr><td>{_html.escape(str(year))}</td>{cell}</tr>")
    return (
        f'<div class="drhp-forecast-rmse-wrap">'
        f'<div class="drhp-forecast-rmse-caption">'
        f'{_html.escape(FORECAST_RMSE_TABLE_CAPTION)}</div>'
        f'<table class="drhp-forecast-rmse">'
        f'<thead>{header}</thead><tbody>{"".join(rows)}</tbody>'
        f'</table></div>'
    )


def _tested_strip_html(record: "ForecastRecord") -> str:
    """The always-visible 'How this was tested' honesty strip (D-3, FCAST-04).

    Three-up stats (empirical 80% coverage · MAE · walk-forward window/N), the
    per-year RMSE table, and the coverage honesty note (P17). No metric is
    coloured good/bad — neutral mono numbers only.
    """
    m = record.metrics
    coverage = _fmt1(m.coverage_empirical * 100.0)
    mae = _fmt1(m.mae_pts)
    window = f"{_html.escape(str(m.backtest_window))} · n = {m.n}"

    stat_row = (
        f'<div class="drhp-forecast-stat-row">'
        f'<div class="drhp-forecast-stat">'
        f'<div class="drhp-forecast-stat-value">{coverage}%</div>'
        f'<div class="drhp-forecast-stat-label">'
        f'{_html.escape(FORECAST_COVERAGE_STAT_LABEL)}</div></div>'
        f'<div class="drhp-forecast-stat">'
        f'<div class="drhp-forecast-stat-value">{mae} points</div>'
        f'<div class="drhp-forecast-stat-label">'
        f'{_html.escape(FORECAST_MAE_STAT_LABEL)}</div></div>'
        f'<div class="drhp-forecast-stat">'
        f'<div class="drhp-forecast-stat-value">{window}</div>'
        f'<div class="drhp-forecast-stat-label">'
        f'{_html.escape(FORECAST_BACKTEST_STAT_LABEL)}</div></div>'
        f'</div>'
    )
    return (
        f'<div class="drhp-forecast-tested">'
        f'<div class="drhp-forecast-tested-eyebrow">'
        f'{_html.escape(FORECAST_TESTED_EYEBROW)}</div>'
        f'{stat_row}'
        f'{_rmse_table_html(m.per_year_rmse)}'
        f'<div class="drhp-forecast-note">'
        f'{_html.escape(FORECAST_COVERAGE_HONESTY_NOTE)}</div>'
        f'</div>'
    )


def _cardlink_html() -> str:
    """The 'Full model card →' link — accent-as-text, 44×44 tap target (FCAST-05)."""
    return (
        f'<a class="drhp-forecast-cardlink" href="{_MODEL_CARD_HREF}">'
        f'{_html.escape(FORECAST_MODEL_CARD_LINK)}</a>'
    )


def _heading_html() -> str:
    """The locked serif block heading (L5-4) inside the semantic wrapper."""
    return (
        f'<div class="drhp-forecast-block">'
        f'<h2 class="drhp-snapshot-block-heading">'
        f'{_html.escape(FORECAST_BLOCK_HEADING)}</h2></div>'
    )


# ===========================================================================
# Streamlit render entry points (thin wrappers over the pure builders)
# ===========================================================================


def render_forecast_block(
    record: "ForecastRecord",
    gmp_record: "GmpRecord | None",
    issue_price: float | None,
) -> None:
    """Render the cache-only forecast section for a PRESENT record.

    Fans out three record-driven states: covered + GMP (full render), covered +
    no-GMP (band renders, marker + gap line omitted, honest no-gap note), and
    abstain (honest note, NO band). The not-covered (no record) and error states
    are rendered by render_forecast_not_covered / render_forecast_error, which the
    page wiring dispatches. Wrapped in ONE st.container(border=True) (never a split
    div); the plot is ONE self-contained st.markdown.
    """
    with st.container(border=True, key="drhpcard-forecast"):
        st.markdown(_heading_html(), unsafe_allow_html=True)

        if record.is_abstain:
            # Honest abstain note — no band, no fabricated interval or GMP.
            st.markdown(
                f'<div class="drhp-not-disclosed">'
                f'{_html.escape(FORECAST_EMPTY_ABSTAIN)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(render_per_answer_footer(), unsafe_allow_html=True)
            return

        # Covered — the calibrated GMP-free framing sub-line.
        st.caption(FORECAST_FRAMING_SUBLINE)

        gmp_premium, gmp_implied = _resolve_gmp_implied(gmp_record, issue_price)

        # The plot — ONE self-contained st.markdown (band + median + 0% + GMP).
        st.markdown(
            _plot_html(record, gmp_implied, gmp_premium, issue_price),
            unsafe_allow_html=True,
        )
        # The plain-language caption (the real headline — words, not a number).
        st.markdown(_caption_html(record), unsafe_allow_html=True)
        # The GMP-vs-model gap line, or the honest no-GMP note.
        st.markdown(_gap_html(record, gmp_implied), unsafe_allow_html=True)
        # The always-visible honesty-metrics strip (coverage / MAE / RMSE).
        st.markdown(_tested_strip_html(record), unsafe_allow_html=True)
        # The model-card link + the inherited per-block disclaimer.
        st.markdown(_cardlink_html(), unsafe_allow_html=True)
        st.markdown(render_per_answer_footer(), unsafe_allow_html=True)


def render_forecast_not_covered() -> None:
    """Render the honest not-covered empty state (no forecast record on disk).

    Block heading + the `.drhp-not-disclosed` not-covered note — no band, no
    fabricated interval or metrics. Used for the FileNotFoundError / precomputing
    state (the render's honest 'no calibrated forecast available yet').
    """
    with st.container(border=True, key="drhpcard-forecast-empty"):
        st.markdown(_heading_html(), unsafe_allow_html=True)
        st.markdown(
            f'<div class="drhp-not-disclosed">'
            f'{_html.escape(FORECAST_EMPTY_NOT_COVERED)}</div>',
            unsafe_allow_html=True,
        )


def render_forecast_error() -> None:
    """Render the inherited amber `.drhp-refusal` banner (NOT red) on a cache error.

    A non-FileNotFoundError read failure — the rest of the page renders regardless
    (T-05-07-ERR). role=alert aria-live=polite for the honest infra note.
    """
    st.markdown(
        f'<div class="drhp-refusal" role="alert" aria-live="polite">'
        f'<p class="drhp-refusal-body">{_html.escape(FORECAST_ERROR_STATE)}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
