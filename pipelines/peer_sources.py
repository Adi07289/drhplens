"""
pipelines/peer_sources.py — the honest per-cell peer-multiples fetcher (PEER-02).

The D4-05 source-priority ladder. For each (company, metric) cell, walk the
sources in priority order and record WHICH source supplied the value:

    1. screener.in  (primary — richest Indian fundamentals)  → flag "s"
    2. yfinance .NS/.BO  (Ticker.info fallback)               → flag "y"
    3. NSE/BSE  (jugaad-data / direct)                        → flag "n"
    4. no source has it → PeerCell() (value None) → renders "—"  (NEVER interpolated)

This is the honest-sourcing engine: a value missing from every source is None,
never invented or zeroed (P15 — a yfinance 0/None/NaN ratio is coerced to
missing; a real 0 ROE is vanishingly rare and treated as missing for ratios). A
negative/undefined P/E (a loss-making issuer) is preserved as the NM sentinel
(`PeerCell(not_meaningful=True, value=None)`), distinguishable from both a real
number and a missing cell. A negative ROE, by contrast, is a real value.

as-of dimension: this module fetches CURRENT-MARKET multiples (each cell's
`as_of="current"`). The IPO issuer's own as-of-DRHP-date row (source "d",
`as_of="drhp_date"`) is assembled from DRHP-derived data in pipelines/peers.py,
not here.

CODE-NOW-DEFER (04-03-PLAN.md objective): the live screener/yfinance/NSE fetch is
a DEFERRED human runbook step. Under `pytest tests/unit` every source fetcher is
monkeypatched — NO live HTTP happens. All fetching is lazy (import is
network-safe): no HTTP session is constructed and no network call is made at
module import time.

Security (T-04-03-SSRF, V5): only HARD-CODED source hostnames are ever fetched —
no URL is derived from user/DRHP input. The company name is used only as a
sanitised path segment against a hard-coded host, never as a host or a full URL.
Reuse the project stack (RESEARCH §Don't Hand-Roll): requests-cache (polite
caching), tenacity (backoff), beautifulsoup4+lxml (HTML parse), rapidfuzz
(name→ticker matching) — do not hand-roll any of these.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

from rapidfuzz import fuzz, process

from agent.peer_schema import PeerCell, PeerMetric, PeerSource

# The 4 peer-multiple metric keys, in the UI-SPEC R-2 fixed column order.
_METRIC_ORDER: tuple[str, ...] = ("pe", "pb", "ev_ebitda", "roe")

# Hard-coded source hosts (SSRF control T-04-03-SSRF) — never assembled from input.
_SCREENER_BASE = "https://www.screener.in"
_NSE_BASE = "https://www.nseindia.com"

# A realistic User-Agent so screener.in / NSE do not immediately block the scrape.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 DRHPLens/1.0 (portfolio-project)"
)

# Hand-curated peer-name → NSE ticker map for the catalogue's likely DRHP peers.
# rapidfuzz matches a scraped/DRHP-disclosed name against these keys (D4-05). This
# is deliberately a small, reviewed allow-list — an unknown name resolves to None
# (its yfinance rung is skipped honestly rather than guessing a wrong ticker).
_TICKER_MAP: dict[str, str] = {
    "Zomato Limited": "ZOMATO.NS",
    "Eternal Limited": "ETERNAL.NS",
    "FSN E-Commerce Ventures Limited": "NYKAA.NS",
    "Nykaa": "NYKAA.NS",
    "One97 Communications Limited": "PAYTM.NS",
    "Paytm": "PAYTM.NS",
    "Honasa Consumer Limited": "HONASA.NS",
    "Mamaearth": "HONASA.NS",
    "Ola Electric Mobility Limited": "OLAELEC.NS",
    "Hyundai Motor India Limited": "HYUNDAI.NS",
    "Life Insurance Corporation of India": "LICI.NS",
    "Maruti Suzuki India Limited": "MARUTI.NS",
    "Bajaj Finance Limited": "BAJFINANCE.NS",
    "Reliance Industries Limited": "RELIANCE.NS",
}

# rapidfuzz name→ticker match must clear this score (0-100) or resolve to None.
_TICKER_FUZZ_THRESHOLD = 82.0


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------


def _clean_ratio(v: object) -> float | None:
    """Coerce a raw ratio to float, treating 0 / None / NaN as MISSING (P15).

    A real 0.0 ratio is vanishingly rare for P/E, P/B, EV/EBITDA, ROE, so 0 is
    treated as missing rather than risk a yfinance 0.0 masquerading as a value.
    Negative values pass through (a negative ROE is real; a negative P/E is
    handled as NM downstream in _build_cell).
    """
    if isinstance(v, bool):  # bool is an int subclass — never a ratio
        return None
    if not isinstance(v, (int, float)):
        return None
    if v == 0:
        return None
    if isinstance(v, float) and math.isnan(v):  # NaN != NaN
        return None
    return float(v)


def _pct(v: float | None) -> float | None:
    """yfinance returnOnEquity is a FRACTION (0.0914 = 9.14%) → percent (×100)."""
    return None if v is None else round(v * 100.0, 4)


# ---------------------------------------------------------------------------
# Per-source fetchers — each returns {metric_key: float | None}
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _session():
    """Lazily build a cached, polite HTTP session (never at import time).

    requests-cache gives transparent on-disk caching so a batch precompute never
    re-hammers screener.in (P16). Constructed on first fetch, not at import, so
    `import pipelines.peer_sources` stays network- and filesystem-safe.
    """
    import requests_cache

    session = requests_cache.CachedSession(
        cache_name=".cache/peer_sources",
        backend="sqlite",
        expire_after=60 * 60 * 24,  # 1 day — fundamentals change slowly
    )
    session.headers.update({"User-Agent": _UA})
    return session


_SCREENER_LABELS: dict[str, tuple[str, ...]] = {
    "pe": ("stock p/e", "p/e", "price to earning"),
    "pb": ("price to book", "p/b", "book value"),
    "ev_ebitda": ("ev/ebitda", "ev / ebitda", "enterprise value"),
    "roe": ("roe", "return on equity"),
}


def screener_multiples(name: str) -> dict[str, float | None]:
    """Primary source: screener.in company-page ratios, per-cell (flag "s").

    DEFERRED live path (CODE-NOW-DEFER): monkeypatched under tests/unit. Fetches
    only the hard-coded screener.in host (SSRF control), parses the top-ratios
    block with beautifulsoup4+lxml, and coerces every value via _clean_ratio. Any
    failure (rate-limit, markup drift, missing ratio) degrades honestly to None
    for that cell — never a fabricated number (the ladder then falls through).
    """
    out: dict[str, float | None] = {k: None for k in _METRIC_ORDER}
    symbol = _screener_symbol(name)
    if not symbol:
        return out
    try:  # pragma: no cover — live network path, exercised only in the runbook
        from bs4 import BeautifulSoup
        from tenacity import retry, stop_after_attempt, wait_exponential_jitter

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=1, max=10),
            reraise=True,
        )
        def _fetch() -> str:
            # Host is hard-coded; only the sanitised symbol is a path segment.
            url = f"{_SCREENER_BASE}/company/{symbol}/"
            resp = _session().get(url, timeout=15)
            resp.raise_for_status()
            return resp.text

        soup = BeautifulSoup(_fetch(), "lxml")
        parsed = _parse_screener_ratios(soup)
        for key in _METRIC_ORDER:
            out[key] = _clean_ratio(parsed.get(key))
    except Exception:  # noqa: BLE001 — honest degradation to "—" for this source
        return {k: None for k in _METRIC_ORDER}
    return out


def _screener_symbol(name: str) -> str | None:
    """Map a DRHP peer name to its screener.in symbol via the ticker allow-list.

    Returns the bare symbol (e.g. "ZOMATO") for the hard-coded path segment, or
    None for an unknown name (no guessed URL — SSRF + honesty).
    """
    ticker = resolve_ticker(name)
    if ticker is None:
        return None
    return ticker.split(".")[0]


def _parse_screener_ratios(soup) -> dict[str, float | None]:  # pragma: no cover
    """Parse screener.in's top-ratios <li> block into {metric: float|None}.

    Best-effort label matching (markup drifts) — a label not found stays None.
    """
    parsed: dict[str, float | None] = {k: None for k in _METRIC_ORDER}
    for li in soup.select("#top-ratios li, ul#top-ratios li"):
        text = " ".join(li.get_text(" ", strip=True).lower().split())
        num = _first_number(text)
        if num is None:
            continue
        for key, labels in _SCREENER_LABELS.items():
            if parsed[key] is None and any(lbl in text for lbl in labels):
                parsed[key] = num
                break
    return parsed


def _first_number(text: str) -> float | None:  # pragma: no cover
    """Extract the first signed decimal number from a label string."""
    m = re.search(r"-?\d[\d,]*\.?\d*", text)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def yfinance_multiples(ticker: str | None) -> dict[str, float | None]:
    """Fallback source: yfinance Ticker.info multiples (flag "y").

    Reads the .info keys live-validated in 04-01: trailingPE→P/E, priceToBook→P/B,
    enterpriseToEbitda→EV/EBITDA, returnOnEquity→ROE. Every value is coerced via
    _clean_ratio (0/None/NaN → missing, P15). returnOnEquity is a FRACTION and is
    converted to percent (×100). A None ticker or a sparse .info yields all-None.
    Never asserts a field exists (Yahoo's Indian data is patchy — P15).
    """
    if not ticker:
        return {k: None for k in _METRIC_ORDER}
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info or {}
    except Exception:  # noqa: BLE001 — honest degradation for this source
        return {k: None for k in _METRIC_ORDER}
    return {
        "pe": _clean_ratio(info.get("trailingPE")),
        "pb": _clean_ratio(info.get("priceToBook")),
        "ev_ebitda": _clean_ratio(info.get("enterpriseToEbitda")),
        "roe": _pct(_clean_ratio(info.get("returnOnEquity"))),
    }


def nse_multiples(ticker: str | None) -> dict[str, float | None]:
    """Third rung: NSE/BSE (flag "n").

    NSE/BSE do not expose these fundamental ratios on a stable public endpoint, so
    this rung is an honest placeholder that returns all-None today (the ladder
    then leaves the cell as "—"). It exists so the source-priority contract is
    complete and the deferred jugaad-data/NSE integration has a seam to fill.
    Fetches only the hard-coded NSE host if ever implemented (SSRF control).
    """
    _ = (ticker, _NSE_BASE)  # host is hard-coded; no input-derived URL
    return {k: None for k in _METRIC_ORDER}


# ---------------------------------------------------------------------------
# name → ticker matching (rapidfuzz — RESEARCH §Don't Hand-Roll)
# ---------------------------------------------------------------------------


def resolve_ticker(name: str) -> str | None:
    """Fuzzy-match a DRHP/scraped peer name to an NSE ticker via the allow-list.

    Uses rapidfuzz (already a Phase-3 dep) against the hand-curated _TICKER_MAP.
    Returns the best-matching ticker at/above _TICKER_FUZZ_THRESHOLD, else None
    (an unknown name honestly resolves to no ticker rather than a wrong guess).
    """
    if not name or not name.strip():
        return None
    match = process.extractOne(
        name.strip(),
        list(_TICKER_MAP.keys()),
        scorer=fuzz.token_set_ratio,
        score_cutoff=_TICKER_FUZZ_THRESHOLD,
    )
    if match is None:
        return None
    return _TICKER_MAP[match[0]]


# ---------------------------------------------------------------------------
# resolve_multiples — the ladder orchestrator
# ---------------------------------------------------------------------------


def _build_cell(metric_key: str, value: float, source: PeerSource) -> PeerCell:
    """Build the winning current-market cell for one metric.

    A negative/undefined P/E (loss-making issuer) becomes the NM sentinel
    (value None, not_meaningful True) — the source is still recorded. Any other
    value (including a negative ROE) is stored as-is.
    """
    if metric_key == "pe" and value < 0:
        return PeerCell(source=source, as_of="current", not_meaningful=True)
    return PeerCell(value=float(value), source=source, as_of="current")


def _resolve_cell(metric_key: str, ladder: list[tuple[PeerSource, dict]]) -> PeerCell:
    """Return the first-available cell for a metric across the source ladder."""
    for source_flag, data in ladder:
        value = data.get(metric_key)
        if value is not None:
            return _build_cell(metric_key, value, source_flag)
    return PeerCell()  # missing from every source → "—" (never interpolated)


def resolve_multiples(
    name: str, *, ticker: str | None = None
) -> list[PeerMetric]:
    """Resolve all four current-market multiples for one company via the ladder.

    Fetches each source ONCE (screener.in → yfinance → NSE), then for each metric
    picks the first-available value and records its source flag (D4-05). Returns a
    list[PeerMetric] in the fixed R-2 column order; each PeerMetric.current is the
    winning cell (or PeerCell() when no source has it → "—").

    Precompute-time only (D3-17 / P16) — never called from load_peers or a page.
    """
    if ticker is None:
        ticker = resolve_ticker(name)

    ladder: list[tuple[PeerSource, dict]] = [
        ("s", screener_multiples(name)),
        ("y", yfinance_multiples(ticker)),
        ("n", nse_multiples(ticker)),
    ]
    return [
        PeerMetric(metric=key, current=_resolve_cell(key, ladder))
        for key in _METRIC_ORDER
    ]
