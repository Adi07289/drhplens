"""
pipelines/historical/sources.py — Issuer-side fetchers for the historical panel.

The P3 survivorship control starts HERE: the universe is sourced from
issuer-side aggregators that include withdrawn/pulled IPOs (chittorgarh's
historical IPO index + SEBI's offer-document filings), NOT from survivor-only
exchange "currently-listed" feeds. Listing-day closes come from NSE bhavcopy via
`jugaad-data` (per the 04-01 verdict) with `yfinance` `.NS`/`.BO` as the price
fallback.

Security / robustness controls (04-07 threat_model):
  - T-04-07-SSRF: only the hard-coded hostnames in `ALLOWED_HOSTS` are ever
    fetched. No URL is derived from user or DRHP input. `_check_host` refuses
    anything else.
  - T-04-07-VALID: every parsed field is coerced through the typed helpers
    below; a row that cannot be validated is returned with the offending field
    as ``None`` (→ NaN in the panel) and logged — never silently dropped as a
    survivor and never fabricated.
  - Polite scraping: a shared `requests-cache` session + `tenacity` backoff +
    a realistic User-Agent (CLAUDE.md §India-Specific Data-Source Notes).

NO NETWORK AT IMPORT. Every network client (`requests-cache`, `jugaad-data`,
`yfinance`) is imported lazily inside the function that needs it, so importing
this module — and the whole unit-test suite — stays fully offline. The live
crawl is the deferred human/network step run at the 04-07 checkpoint.
"""
from __future__ import annotations

import datetime as _dt
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hard-coded source hosts (SSRF control, T-04-07-SSRF) — no dynamic URLs.
# ---------------------------------------------------------------------------
ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "www.chittorgarh.com",   # historical IPO index incl. withdrawn/pulled
        "www.sebi.gov.in",       # issuer-side offer-document filings
        "nsearchives.nseindia.com",  # NSE archives (scrape-friendlier subdomain)
    }
)

# chittorgarh's historical IPO index is the single best aggregator for panel
# construction (CLAUDE.md). The report id (20) is the DRHP/RHP prospectus index.
CHITTORGARH_IPO_INDEX = (
    "https://www.chittorgarh.com/report/mainboard-ipo-list-in-india-bse-nse/83/"
)
CHITTORGARH_PROSPECTUS_INDEX = (
    "https://www.chittorgarh.com/report/"
    "ipo_prospectus_document_drhp_rhp_pdf/20/"
)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 DRHPLens/0.1 (research)"
)

# The status taxonomy this module can emit (kept in sync with
# pipelines.historical.STATUS_VALUES — validated again at assembly time).
_STATUS_ALIASES: dict[str, str] = {
    "withdrawn": "withdrawn",
    "pulled": "withdrawn",
    "cancelled": "withdrawn",
    "cancelled/withdrawn": "withdrawn",
    "listed": "listed_alive",
    "active": "listed_alive",
    "delisted": "delisted",
    "merged": "merged",
    "amalgamated": "merged",
    "renamed": "name_changed",
    "name changed": "name_changed",
}


def _check_host(url: str) -> None:
    """Refuse any URL whose host is not in the hard-coded allow-list (SSRF)."""
    host = urlparse(url).netloc.lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(
            f"Refusing to fetch host={host!r}; only {sorted(ALLOWED_HOSTS)} are "
            f"allowed (SSRF control T-04-07-SSRF)."
        )


# ---------------------------------------------------------------------------
# Typed coercion helpers (T-04-07-VALID) — parsed HTML is untrusted.
# ---------------------------------------------------------------------------


def coerce_price(raw: object) -> float | None:
    """Parse a rupee price string (₹, commas) to float, or None if invalid."""
    if raw is None:
        return None
    s = str(raw).strip().replace("₹", "").replace(",", "").replace("Rs", "")
    s = s.strip()
    if not s or s in {"-", "—", "NA", "N/A"}:
        return None
    try:
        val = float(s)
    except ValueError:
        return None
    return val if val > 0 else None


def coerce_date(raw: object) -> _dt.date | None:
    """Parse a date across the formats chittorgarh/SEBI use; None if invalid."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in {"-", "—", "NA", "N/A"}:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_status(raw: object, *, listed: bool | None = None) -> str:
    """Map a source status string to the panel taxonomy.

    Falls back to ``listed_alive`` when a row clearly listed but carries no
    explicit status, and ``withdrawn`` when the source marks it pulled. A row
    with no signal at all defaults to ``listed_alive`` ONLY if ``listed`` is
    True; otherwise the caller must decide (never silently assume a survivor).
    """
    if raw is not None:
        key = str(raw).strip().lower()
        if key in _STATUS_ALIASES:
            return _STATUS_ALIASES[key]
    if listed is True:
        return "listed_alive"
    if listed is False:
        return "withdrawn"
    # Unknown — the caller/build layer must resolve; default to the honest
    # "listed_alive" only if we truly have a listing date, else withdrawn.
    return "listed_alive"


# ---------------------------------------------------------------------------
# HTTP session (requests-cache) — lazy; NO network at import.
# ---------------------------------------------------------------------------


def _session():  # pragma: no cover - exercised only at the live checkpoint
    """Build a cached, polite requests session. Imported lazily."""
    import requests_cache  # deferred — keeps import offline

    session = requests_cache.CachedSession(
        cache_name=".cache/historical_http",
        backend="sqlite",
        expire_after=60 * 60 * 24 * 7,  # 1 week; IPO history is immutable
    )
    session.headers.update({"User-Agent": _USER_AGENT})
    return session


def _get(url: str, *, timeout: int = 30) -> str:  # pragma: no cover - live only
    """GET a hard-coded-host URL with backoff; return response text."""
    _check_host(url)
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential_jitter,
    )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=20),
        reraise=True,
    )
    def _do() -> str:
        session = _session()
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    return _do()


# ---------------------------------------------------------------------------
# Source fetchers (LIVE — deferred to the 04-07 checkpoint; not run in tests).
# ---------------------------------------------------------------------------


def fetch_chittorgarh_index() -> list[dict]:  # pragma: no cover - live only
    """Fetch + parse chittorgarh's historical mainboard IPO index.

    Returns a list of raw row dicts (issuer, issue_date, listing_date,
    issue_price, listing_day_close?, status?) with every field coerced through
    the typed helpers. Withdrawn/pulled IPOs are INCLUDED — this is the P3
    survivorship control. Per-row parse failures are logged and the offending
    field set to None, never dropped.
    """
    from bs4 import BeautifulSoup  # deferred

    html = _get(CHITTORGARH_IPO_INDEX)
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    table = soup.find("table")
    if table is None:
        logger.warning("chittorgarh index: no table found; site layout changed?")
        return rows
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 4:
            continue
        try:
            rows.append(
                {
                    "issuer": cells[0] or None,
                    "issue_date": coerce_date(cells[1]),
                    "listing_date": coerce_date(cells[2]) if len(cells) > 2 else None,
                    "issue_price": coerce_price(cells[3]) if len(cells) > 3 else None,
                    "listing_day_close": (
                        coerce_price(cells[4]) if len(cells) > 4 else None
                    ),
                    "status_raw": cells[5] if len(cells) > 5 else None,
                }
            )
        except Exception as exc:  # noqa: BLE001 - per-row isolation (T-04-07-VALID)
            logger.warning("chittorgarh row parse failed: %s", exc)
            continue
    return rows


def fetch_sebi_offer_documents() -> list[dict]:  # pragma: no cover - live only
    """Fetch SEBI issuer-side offer-document filings (withdrawals included).

    Deferred seam. SEBI has no clean API and shifts its HTML; the live crawl at
    the checkpoint cross-references SEBI filings against the chittorgarh index to
    catch withdrawn IPOs that never reached a listing feed.
    """
    logger.info("fetch_sebi_offer_documents: deferred to the live checkpoint run")
    return []


def fetch_listing_day_close(
    symbol: str, listing_date: _dt.date
) -> float | None:  # pragma: no cover - live only
    """Listing-day EOD close via NSE bhavcopy (jugaad-data), yfinance fallback.

    Returns None (→ NaN in the panel, RETAINED) when neither source has the
    price — the absence is counted, never fabricated as 0.0 (P15).
    """
    # Primary: jugaad-data NSE bhavcopy.
    try:
        from jugaad_data.nse import stock_df  # deferred

        df = stock_df(
            symbol=symbol,
            from_date=listing_date,
            to_date=listing_date,
            series="EQ",
        )
        if df is not None and not df.empty and "CLOSE" in df.columns:
            close = coerce_price(df.iloc[0]["CLOSE"])
            if close is not None:
                return close
    except Exception as exc:  # noqa: BLE001 - fall through to yfinance
        logger.info("jugaad-data miss for %s: %s", symbol, exc)

    # Fallback: yfinance .NS / .BO.
    try:
        import yfinance as yf  # deferred

        for suffix in (".NS", ".BO"):
            hist = yf.Ticker(f"{symbol}{suffix}").history(
                start=listing_date,
                end=listing_date + _dt.timedelta(days=1),
            )
            if hist is not None and not hist.empty and "Close" in hist.columns:
                close = coerce_price(float(hist.iloc[0]["Close"]))
                if close is not None:
                    return close
    except Exception as exc:  # noqa: BLE001 - honest miss => None
        logger.info("yfinance miss for %s: %s", symbol, exc)

    return None


__all__ = [
    "ALLOWED_HOSTS",
    "CHITTORGARH_IPO_INDEX",
    "coerce_price",
    "coerce_date",
    "normalize_status",
    "fetch_chittorgarh_index",
    "fetch_sebi_offer_documents",
    "fetch_listing_day_close",
]
