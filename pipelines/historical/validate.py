"""
pipelines/historical/validate.py — ~7% median MAAR sanity-check + divergence flag.

The DS-critical honesty control for the historical panel (P3). After the panel
is assembled, `sanity_check_median` compares the built dataset's MEDIAN
listing-day return against the published ~7% MAAR baseline and returns a
plain-text, `/methodology`-ready divergence note if the median falls materially
outside the sane band.

Baseline: Shah & Mehta (2015) — 113 NSE mainboard IPOs, 2010–2014,
Market-Adjusted Abnormal Return (MAAR) = **7.19%**. Broader 2003–2014 samples
show first-day averages nearer ~14% and the median clustering ~7–15% depending
on the window (04-RESEARCH.md §Pitfall 3, Assumption A4). The EXACT target
matters less than the divergence FLAG: a built median materially above the band
(e.g. > ~20%) is the classic survivorship-inflation signature — the universe is
probably dropping withdrawn/delisted IPOs instead of counting them as NaN.

The flag is a plain-text string (rendered verbatim on `/methodology`), NOT a UI
widget and NOT a red/green signal.
"""
from __future__ import annotations

import math

import pandas as pd

# Published baseline (Shah & Mehta 2015 MAAR). The divergence flag matters more
# than the exact number (A4) — this is the sanity anchor, not a hard target.
MAAR_BASELINE: float = 0.0719

# Sane band for a survivorship-corrected 2014-present mainboard universe.
#  - Upper 0.20 (20%): a median above this is the survivor-inflation warning
#    (04-RESEARCH.md §Pitfall 3 "Median listing return > ~20% (survivor inflation)").
#  - Lower -0.05 (-5%): a median below this is implausibly negative for the
#    period and suggests a sourcing/return-computation error.
BAND_UPPER: float = 0.20
BAND_LOWER: float = -0.05


def sanity_check_median(
    df: pd.DataFrame,
    *,
    baseline: float = MAAR_BASELINE,
    band_lower: float = BAND_LOWER,
    band_upper: float = BAND_UPPER,
) -> tuple[float, str | None]:
    """Median listing-day return + a divergence flag when it leaves the sane band.

    Computes the median over rows with a NON-NaN `listing_day_return` (the
    replace-with-NaN survivorship rows are excluded from the statistic but were
    NEVER dropped from the panel — their absence is what the band is guarding).

    Args:
        df: an assembled panel carrying a `listing_day_return` column.
        baseline: the ~7% MAAR anchor (default MAAR_BASELINE = 7.19%).
        band_lower / band_upper: the sane band; a median outside it fires the flag.

    Returns:
        ``(median, flag_text_or_None)``:
          - ``median`` — the median of non-NaN listing-day returns, or NaN if
            there are no scored rows.
          - ``flag_text`` — ``None`` when the median is in-band (quiet), else a
            plain-text `/methodology` divergence note.
    """
    if "listing_day_return" not in df.columns:
        raise ValueError("Panel has no 'listing_day_return' column to sanity-check.")

    scored = df["listing_day_return"].dropna()
    if scored.empty:
        # No scored rows at all — cannot sanity-check; surface it honestly.
        return (
            float("nan"),
            (
                "Median listing-day return sanity-check could not run: the panel "
                "has no rows with a computable listing-day return. This is itself "
                f"a survivorship/data-coverage warning — expected a median near the "
                f"~{baseline * 100:.2f}% MAAR baseline (Shah & Mehta 2015)."
            ),
        )

    median = float(scored.median())

    if median > band_upper:
        flag = (
            f"Sanity-check divergence: the built panel's median listing-day return "
            f"is {median * 100:.2f}% over {len(scored)} scored IPOs, materially ABOVE "
            f"the ~{baseline * 100:.2f}% MAAR baseline (Shah & Mehta 2015) and past the "
            f"{band_upper * 100:.0f}% survivor-inflation threshold. A median this high "
            f"is the classic survivorship-bias signature — the universe is likely "
            f"dropping withdrawn/delisted IPOs instead of retaining them as NaN. Treat "
            f"the panel as suspect until the status distribution (withdrawn/delisted "
            f"present?) and sourcing are re-checked."
        )
        return median, flag

    if median < band_lower:
        flag = (
            f"Sanity-check divergence: the built panel's median listing-day return "
            f"is {median * 100:.2f}% over {len(scored)} scored IPOs, materially BELOW "
            f"the ~{baseline * 100:.2f}% MAAR baseline (Shah & Mehta 2015) and under the "
            f"{band_lower * 100:.0f}% floor. An implausibly negative median for the "
            f"2014-present mainboard window suggests a return-computation or issue-price "
            f"sourcing error rather than a genuine market effect."
        )
        return median, flag

    return median, None


def band_text(baseline: float = MAAR_BASELINE) -> str:
    """The plain-text description of the sane band, for the /methodology page."""
    return (
        f"Median listing-day return is sanity-checked against the ~{baseline * 100:.2f}% "
        f"MAAR baseline (Shah & Mehta 2015, 113 NSE mainboard IPOs 2010–2014). A built "
        f"median outside [{BAND_LOWER * 100:.0f}%, {BAND_UPPER * 100:.0f}%] raises a "
        f"plain-text divergence flag; a median above 20% is read as survivorship "
        f"inflation (dropped withdrawn/delisted IPOs)."
    )


def _is_nan(x: float) -> bool:
    return isinstance(x, float) and math.isnan(x)


def panel_sanity_summary(
    df: pd.DataFrame,
    *,
    baseline: float = MAAR_BASELINE,
    band_lower: float = BAND_LOWER,
    band_upper: float = BAND_UPPER,
) -> dict:
    """A JSON-serialisable, `/methodology`-ready survivorship sanity summary (SC-5).

    Wraps ``sanity_check_median`` + ``band_text`` into the render-ready record the
    committed ``data/historical/panel_sanity.json`` is built from, so the page can
    surface the sanity RESULT without importing this (Phase-4) module at render
    (T-05-10-ISO). ``within_band`` is True only when a median exists AND no flag
    fired — the honest verdict, never a fabricated divergence.

    Returns a dict with ``median_return`` (fraction, or None when unscored),
    ``median_pct``, ``n_scored``, ``baseline_pct``, ``band_lower_pct`` /
    ``band_upper_pct``, ``within_band`` (bool), ``flag`` (the plain-text divergence
    note or None), and ``methodology`` (the ``band_text`` description).
    """
    median, flag = sanity_check_median(
        df, baseline=baseline, band_lower=band_lower, band_upper=band_upper
    )
    scored = 0
    if "listing_day_return" in df.columns:
        scored = int(df["listing_day_return"].dropna().shape[0])

    median_is_nan = _is_nan(median)
    within_band = (flag is None) and (not median_is_nan)
    return {
        "median_return": None if median_is_nan else round(median, 4),
        "median_pct": None if median_is_nan else round(median * 100, 2),
        "n_scored": scored,
        "baseline_pct": round(baseline * 100, 2),
        "band_lower_pct": round(band_lower * 100, 2),
        "band_upper_pct": round(band_upper * 100, 2),
        "within_band": within_band,
        "flag": flag,
        "methodology": band_text(baseline),
    }


__all__ = [
    "MAAR_BASELINE",
    "BAND_UPPER",
    "BAND_LOWER",
    "sanity_check_median",
    "band_text",
    "panel_sanity_summary",
]
