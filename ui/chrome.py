"""
ui/chrome.py — premium "SaaS chrome" for DRHPLens: the sticky glassmorphic nav,
the landing hero (with the ambient "focus glow" signature), the trust/stats band,
the how-it-works strip, section headers, and the structured site footer.

All functions return HTML strings rendered via st.markdown(..., unsafe_allow_html=
True). The one and only stylesheet (app/static/drhplens.css) styles every class
here (.drhp-nav / .drhp-hero2 / .drhp-band / .drhp-hiw / .drhp-site-footer …).

Honesty note: the trust-band figures are deliberately TRUE (IPOs catalogued,
typical DRHP length, "every answer cited", "zero buy/sell calls") — the band must
never overstate coverage (only Swiggy is fully decoded today).
"""
from __future__ import annotations

# ── Sticky glassmorphic nav ──────────────────────────────────────────────────

def render_nav() -> str:
    """Fixed top nav: lens brand mark + minimal links + primary CTA."""
    return (
        '<div class="drhp-nav"><div class="drhp-nav-inner">'
        '<a class="drhp-brand" href="/" target="_self">'
        '<span class="drhp-lens"></span>DRHP<span class="accent">Lens</span></a>'
        '<div class="drhp-nav-links">'
        '<a href="/how_it_works" target="_self">How it works</a>'
        '<a href="/methodology" target="_self">Methodology</a>'
        '<a class="drhp-btn drhp-btn-primary" href="/" target="_self">Browse IPOs&nbsp;&rarr;</a>'
        '</div></div></div>'
    )


# ── Landing hero + ambient glow signature ────────────────────────────────────

def render_landing_hero() -> str:
    """Big serif hero with a gradient key-word and the ambient indigo focus glow."""
    return (
        '<div class="drhp-hero2">'
        '<div class="drhp-glow drhp-glow-a"></div>'
        '<div class="drhp-glow drhp-glow-b"></div>'
        '<div class="drhp-hero-eyebrow">Indian mainboard IPOs · informational only</div>'
        '<h1 class="drhp-hero-title">Read the IPO,<br>not the <span class="grad">hype</span>.</h1>'
        '<p class="drhp-hero-sub">DRHPLens reads the 400-page prospectus for you and answers in '
        'plain English — every figure cited back to the exact DRHP page, with historical context. '
        'No buy/sell calls, ever.</p>'
        '<div class="drhp-hero-cta">'
        '<a class="drhp-btn drhp-btn-primary" href="#drhp-catalogue">Browse IPOs&nbsp;&rarr;</a>'
        '<a class="drhp-btn drhp-btn-ghost" href="/methodology" target="_self">See the methodology</a>'
        '</div>'
        '<div class="drhp-hero-trust">Every claim cited<span class="dot">·</span>'
        'Uncertainty shown, not hidden<span class="dot">·</span>SEBI-safe by design</div>'
        '</div>'
    )


# ── Trust / stats band (honest figures) ──────────────────────────────────────

def render_trust_band(ipo_count: int) -> str:
    """A Stripe-style stats band. Figures are TRUE and never overstate coverage."""
    return (
        '<div class="drhp-band">'
        f'<div class="drhp-stat"><div class="drhp-stat-n">{ipo_count}</div>'
        '<div class="drhp-stat-l">IPOs catalogued</div></div>'
        '<div class="drhp-stat"><div class="drhp-stat-n">~450</div>'
        '<div class="drhp-stat-l">Pages in a typical DRHP</div></div>'
        '<div class="drhp-stat"><div class="drhp-stat-n"><em>100%</em></div>'
        '<div class="drhp-stat-l">Of answers cited to source</div></div>'
        '<div class="drhp-stat"><div class="drhp-stat-n">0</div>'
        '<div class="drhp-stat-l">Buy / sell / subscribe calls</div></div>'
        '</div>'
    )


# ── How it works ─────────────────────────────────────────────────────────────

_IC_READ = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M6 2h8l5 5v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/>'
    '<path d="M14 2v5h5M8 13h8M8 17h5"/></svg>'
)
_IC_CITE = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>'
    '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>'
)
_IC_CTX = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5 20V11M12 20V5M19 20v-6M3 20h18"/></svg>'
)


def render_how_it_works() -> str:
    """Three-value feature strip — the SaaS 'why bother' rhythm."""
    return (
        '<div id="drhp-how" class="drhp-sec-head">'
        '<div class="drhp-sec-k">How it works</div>'
        '<div class="drhp-sec-h">From 400 pages to an honest answer</div></div>'
        '<div class="drhp-hiw">'
        f'<div class="drhp-hiw-card"><div class="drhp-hiw-ic">{_IC_READ}</div>'
        '<h3>Reads the whole DRHP</h3><p>Layout-aware parsing of the full 300–500 page '
        'prospectus — risks, financials, promoter background, related-party deals.</p></div>'
        f'<div class="drhp-hiw-card"><div class="drhp-hiw-ic">{_IC_CITE}</div>'
        '<h3>Cites every figure</h3><p>Each number and claim links to the exact DRHP page it '
        'came from, so you can verify it yourself in one click.</p></div>'
        f'<div class="drhp-hiw-card"><div class="drhp-hiw-ic">{_IC_CTX}</div>'
        '<h3>Puts it in context</h3><p>Peer multiples against listed comparables and how similar '
        'Indian IPOs actually behaved — not marketing gloss.</p></div>'
        '</div>'
    )


# ── Section header ───────────────────────────────────────────────────────────

def render_section_head(kicker: str, title: str, anchor: str = "") -> str:
    """A centered kicker + serif title, e.g. ('The catalogue', 'Recent Indian IPOs')."""
    id_attr = f' id="{anchor}"' if anchor else ""
    return (
        f'<div{id_attr} class="drhp-sec-head">'
        f'<div class="drhp-sec-k">{kicker}</div>'
        f'<div class="drhp-sec-h">{title}</div></div>'
    )


# ── Structured site footer ───────────────────────────────────────────────────

def render_site_footer() -> str:
    """Multi-column footer with the compliance disclaimer in the legal row."""
    return (
        '<div class="drhp-site-footer"><div class="drhp-ft-grid">'
        '<div><a class="drhp-brand" href="/" target="_self">'
        '<span class="drhp-lens"></span>DRHP<span class="accent">Lens</span></a>'
        '<p class="drhp-ft-tag">An honest, cited lens on Indian IPO prospectuses. '
        'Informational and educational only — not investment advice.</p></div>'
        '<div class="drhp-ft-col"><h5>Product</h5>'
        '<a href="/" target="_self">Browse IPOs</a>'
        '<a href="/methodology" target="_self">Methodology</a>'
        '<a href="/how_it_works" target="_self">How it works</a></div>'
        '<div class="drhp-ft-col"><h5>Project</h5>'
        '<a href="https://github.com/REPLACE-ME/drhplens" target="_blank">GitHub</a>'
        '<a href="/methodology" target="_self">Model card</a>'
        '<a href="/methodology" target="_self">Failure gallery</a></div>'
        '</div>'
        '<div class="drhp-ft-legal">'
        '<span>© 2026 DRHPLens · Built on free, public data (SEBI · NSE · BSE · screener.in).</span>'
        '<span>Not a SEBI-registered investment adviser. Decisions are yours.</span>'
        '</div></div>'
    )
