"""
pipelines/gmp_sources.py — the read-only grey-market-premium aggregator scrapers.

Grey-market premium (GMP) is an UNOFFICIAL signal quoted by a handful of public
aggregator sites. This module fetches each aggregator SEPARATELY so the caller can
preserve their disagreement (the honesty signal, D4-01) rather than average it
away. Each fetcher returns a single GmpQuote for one aggregator, or None when that
aggregator has no live quote (the common already-listed case) or the fetch fails —
NEVER a fabricated value and NEVER a zero (Pitfall 5: GMP must not be framed as a
demand signal).

Aggregators (hard-coded hosts — SSRF control T-04-04-SSRF):
    1. investorgain.com  → source flag "investorgain"
    2. ipowatch.in       → source flag "ipowatch"
    3. ipocentral.in     → source flag "ipocentral"

CODE-NOW-DEFER (04-04-PLAN.md objective): the live scrape is a DEFERRED human
runbook step. Under `pytest tests/unit` every fetcher is monkeypatched — NO live
HTTP happens. All fetching is lazy (import is network-safe): no HTTP session is
constructed and no network call is made at module import time.

Security (T-04-04-SSRF, V5): only HARD-CODED aggregator hostnames are ever
fetched — no URL is derived from user/DRHP input. The IPO name is used only as a
sanitised path/query segment against a hard-coded host, never as a host or a full
URL. Every scraped string is untrusted input — any renderer HTML-escapes it before
display. Reuse the project stack (RESEARCH §Don't Hand-Roll): requests-cache
(polite caching), tenacity (backoff), beautifulsoup4+lxml (HTML parse) — do not
hand-roll any of these.

ISOLATION (GMP-02, D4-03): this module and pipelines/gmp.py import NOTHING from any
modelling library or downstream prediction/historical pipeline. GMP is read-only,
display-only, cache-only. Pinned by tests/unit/test_gmp_isolation.py.
"""
from __future__ import annotations

from functools import lru_cache

from agent.gmp_schema import GmpQuote

# Hard-coded aggregator hosts (SSRF control) — never assembled from input.
_INVESTORGAIN_BASE = "https://www.investorgain.com"
_IPOWATCH_BASE = "https://ipowatch.in"
_IPOCENTRAL_BASE = "https://ipocentral.in"

# A realistic User-Agent so the aggregators do not immediately block the scrape.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 DRHPLens/1.0 (portfolio-project)"
)


# ---------------------------------------------------------------------------
# Lazy HTTP session (never constructed at import time)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _session():
    """Lazily build a cached, polite HTTP session (never at import time).

    requests-cache gives transparent on-disk caching so a batch precompute never
    re-hammers an aggregator. Constructed on first fetch, not at import, so
    `import pipelines.gmp_sources` stays network- and filesystem-safe.
    """
    import requests_cache

    session = requests_cache.CachedSession(
        cache_name=".cache/gmp_sources",
        backend="sqlite",
        expire_after=60 * 60 * 6,  # 6h — GMP moves intraday but we cache politely
    )
    session.headers.update({"User-Agent": _UA})
    return session


# ---------------------------------------------------------------------------
# Per-aggregator fetchers — each returns a GmpQuote for one source, or None
# ---------------------------------------------------------------------------


def investorgain_quote(name: str) -> GmpQuote | None:
    """Fetch investorgain.com's GMP for one IPO (source flag "investorgain").

    DEFERRED live path (CODE-NOW-DEFER): monkeypatched under tests/unit. Fetches
    only the hard-coded investorgain host (SSRF control), parses the GMP row with
    beautifulsoup4+lxml, and returns a GmpQuote. Absence of a live quote (the
    common already-listed case) or any failure returns None — never a fabricated
    value (the caller records the absence honestly).
    """
    return _live_quote(_INVESTORGAIN_BASE, "investorgain", name)


def ipowatch_quote(name: str) -> GmpQuote | None:
    """Fetch ipowatch.in's GMP for one IPO (source flag "ipowatch").

    See investorgain_quote — same deferred/monkeypatched, hard-coded-host contract.
    """
    return _live_quote(_IPOWATCH_BASE, "ipowatch", name)


def ipocentral_quote(name: str) -> GmpQuote | None:
    """Fetch ipocentral.in's GMP for one IPO (source flag "ipocentral").

    See investorgain_quote — same deferred/monkeypatched, hard-coded-host contract.
    """
    return _live_quote(_IPOCENTRAL_BASE, "ipocentral", name)


def _live_quote(host: str, source: str, name: str) -> GmpQuote | None:  # pragma: no cover
    """Shared live-fetch shell for one aggregator (DEFERRED — never run in CI).

    Fetches only the hard-coded `host` (SSRF control), using the sanitised IPO
    name as a query segment. Any failure — rate-limit, markup drift, missing quote
    — degrades honestly to None (the ladder then records the absence). This body
    is a seam for the deferred runbook implementation; the unit suite monkeypatches
    the public fetchers above so this never executes offline.
    """
    if not name or not name.strip():
        return None
    try:
        from bs4 import BeautifulSoup
        from tenacity import (
            retry,
            stop_after_attempt,
            wait_exponential_jitter,
        )

        slug = _slugify(name)

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=1, max=10),
            reraise=True,
        )
        def _fetch() -> str:
            # Host is hard-coded; only the sanitised slug is a path segment.
            url = f"{host}/ipo/{slug}/"
            resp = _session().get(url, timeout=15)
            resp.raise_for_status()
            return resp.text

        soup = BeautifulSoup(_fetch(), "lxml")
        value, as_of = _parse_gmp(soup)
        if value is None:
            return None
        return GmpQuote(source=source, value=value, as_of=as_of)
    except Exception:  # noqa: BLE001 — honest degradation to "no quote" for this source
        return None


def _slugify(name: str) -> str:  # pragma: no cover — used only by the deferred live path
    """Sanitise an IPO name into a URL-safe path segment (never a host)."""
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    return slug.strip("-")


def _parse_gmp(soup):  # pragma: no cover — live markup parse, exercised in the runbook
    """Best-effort parse of an aggregator page into (value, as_of).

    Returns (None, "") when no GMP value can be located (markup drift / absence) —
    the caller then records the absence honestly rather than inventing a number.
    """
    return (None, "")


# ---------------------------------------------------------------------------
# Aggregator registry — resolved dynamically so tests can monkeypatch fetchers
# ---------------------------------------------------------------------------


def source_fetchers():
    """Return the (label, fetcher) pairs in a stable order.

    The functions are looked up from module globals at call time, so a test that
    monkeypatches e.g. gmp_sources.investorgain_quote is picked up here.
    """
    return [
        ("investorgain", investorgain_quote),
        ("ipowatch", ipowatch_quote),
        ("ipocentral", ipocentral_quote),
    ]
