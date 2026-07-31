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
import json
import logging
from pathlib import Path
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
        "www.nseindia.com",      # D5-04: past-issues JSON (listed-core, Source A)
        "webnodejs.chittorgarh.com",  # 05-11: chittorgarh JSON API (withdrawn report 202)
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

# D5-04 two-source universe endpoints (all module CONSTANTS — never derived from
# any argument/user/DRHP input; the SSRF control depends on this).
#   Source A — listed core (issue price, listing date, symbol).
NSE_PAST_ISSUES_URL = "https://www.nseindia.com/api/public-past-issues"
NSE_HOME_URL = "https://www.nseindia.com/"  # cookie-priming page (bot-detection)
#   Source B — withdrawn/pulled overlay (the P3 survivorship control).
SEBI_PUBLIC_ISSUES_URL = "https://www.sebi.gov.in/filings/public-issues.html"
CHITTORGARH_WITHDRAWN_REPORT = (
    "https://www.chittorgarh.com/report/ipo-drhp-offer-document-withdrawn/202/"
)
# 05-11 (live-confirmed): the withdrawn HTML report migrated to a JS app
# (soup.find("table") -> None, the 04-07 blocker). Its data is served by the
# webnodejs JSON API; path = data-read/{report}/{page}/{size}/{fyEnd}/{FY}/0/0.
CHITTORGARH_WITHDRAWN_API = (
    "https://webnodejs.chittorgarh.com/cloud/report/data-read/202"
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
    # D5-04: SEBI / chittorgarh-withdrawn wording (Source B overlay) -> withdrawn.
    "withdrawn/lapsed": "withdrawn",
    "lapsed": "withdrawn",
    "offer document withdrawn": "withdrawn",
    "withdrawn offer document": "withdrawn",
    "draft withdrawn": "withdrawn",
    "returned": "withdrawn",
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
    # "%d-%b-%Y"/"%d-%B-%Y" cover the DD-Mon-YYYY shape both live sources use
    # (NSE past-issues "14-JUL-2026"; chittorgarh withdrawn "19-Aug-2024") —
    # confirmed at the 05-11 live pull. strptime %b/%B is case-insensitive.
    for fmt in (
        "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y",
        "%d-%b-%Y", "%d-%B-%Y",
    ):
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


def _get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
) -> str:  # pragma: no cover - live only
    """GET a hard-coded-host URL with backoff; return response text.

    `params` are query-string values (dates, page size) forwarded to the request.
    `headers` are merged over the session defaults (e.g. a `Referer`/`Accept` the
    chittorgarh JSON API expects). The fetched HOST always comes from the
    module-constant `url` and is still checked by `_check_host` (SSRF
    T-05-02-SSRF) — no host is ever derived from an argument.
    """
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
        resp = session.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    return _do()


# ---------------------------------------------------------------------------
# Raw-payload snapshot (A1 defensive posture) — save raw before parsing.
# ---------------------------------------------------------------------------
_RAW_SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "data" / "historical" / "raw"


def _save_raw(name: str, payload: object) -> None:  # pragma: no cover - live only
    """Persist a raw source payload alongside the parsed rows (Assumption A1).

    NSE/SEBI field names are unconfirmed until the first live pull, so snapshot the
    raw JSON/HTML (timestamped) before parsing — mirroring the existing "save raw
    HTML" habit. Best-effort: a snapshot failure never aborts a fetch. Never called
    under the offline unit suite.
    """
    try:
        _RAW_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%dT%H%M%SZ")
        path = _RAW_SNAPSHOT_DIR / f"{name}_{stamp}.raw"
        if isinstance(payload, (dict, list)):
            path.write_text(
                json.dumps(payload, indent=2, default=str), encoding="utf-8"
            )
        else:
            path.write_text(str(payload), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - raw snapshot is best-effort, never fatal
        logger.warning("raw snapshot for %s failed: %s", name, exc)


# ---------------------------------------------------------------------------
# Source fetchers (LIVE — deferred to the 04-07 checkpoint; not run in tests).
# ---------------------------------------------------------------------------


def fetch_chittorgarh_index() -> list[dict]:  # pragma: no cover - live only
    """DEMOTED (D5-04): optional enrichment / cross-check only — no longer primary.

    The chittorgarh HTML index migrated to a Next.js app, so `soup.find("table")`
    returns 0 rows (the 04-07 blocker). `build.py` no longer calls this as the
    primary listed-core path — Source A is now `fetch_nse_past_issues` (NSE
    `public-past-issues` JSON) and the P3 withdrawn overlay is `fetch_sebi_withdrawn`.
    This function is kept as an optional cross-check for a future JSON-API rewrite.

    Returns a list of raw row dicts (issuer, issue_date, listing_date,
    issue_price, listing_day_close?, status?) with every field coerced through
    the typed helpers. Per-row parse failures are logged and the offending
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


# ---------------------------------------------------------------------------
# Source A (D5-04) — listed core: NSE public-past-issues (issue price, listing
# date, symbol). Repoints the panel off the dead chittorgarh HTML scraper.
# ---------------------------------------------------------------------------


def fetch_nse_past_issues(
    from_date: _dt.date, to_date: _dt.date
) -> list[dict]:  # pragma: no cover - live only
    """Source A (D5-04): the LISTED-CORE universe from NSE ``public-past-issues``.

    Returns raw row dicts (issuer, issue_date, listing_date, issue_price,
    listing_day_close?, status_raw?) with every parsed field routed through the
    typed coercers. This is the repoint off the dead chittorgarh HTML scraper.

    Access: NSE blocks bare requests. The maintained ``nse`` library
    (BennyThadikaran/NseIndiaApi) primes cookies + handles bot-detection and is the
    PREFERRED path — but it is NOT installed here (gated behind the 05-11
    human-verify checkpoint, T-05-02-SC), so it is imported lazily and we fall back
    to a cookie-primed GET on the module-constant JSON endpoint via ``_get()`` (so
    ``_check_host`` still runs). The raw JSON is snapshotted before parsing (A1).
    ``from_date``/``to_date`` are passed as query params — no URL is derived from an
    argument (SSRF T-05-02-SSRF).
    """
    payload = _fetch_nse_past_issues_payload(from_date, to_date)
    _save_raw("nse_past_issues", payload)

    if isinstance(payload, dict):
        records = payload.get("data") or payload.get("rows") or []
    else:
        records = payload or []

    rows: list[dict] = []
    for rec in records:
        try:
            rows.append(_parse_nse_past_issue(rec))
        except Exception as exc:  # noqa: BLE001 - per-row isolation (T-05-02-VALID)
            logger.warning("NSE past-issue row parse failed: %s", exc)
            continue
    return rows


def _fetch_nse_past_issues_payload(
    from_date: _dt.date, to_date: _dt.date
) -> object:  # pragma: no cover - live only
    """Return the raw NSE past-issues payload: prefer the ``nse`` lib, else GET."""
    try:
        from nse import NSE  # deferred, optional — gated behind 05-11 (T-05-02-SC)
    except ImportError:
        # Hand-rolled fallback: prime NSE cookies on the home page, then hit the
        # constant JSON endpoint. BOTH hosts are module constants (SSRF-checked).
        _get(NSE_HOME_URL)  # cookie priming (www.nseindia.com is allow-listed)
        text = _get(
            NSE_PAST_ISSUES_URL,
            params={
                "from_date": from_date.strftime("%d-%m-%Y"),
                "to_date": to_date.strftime("%d-%m-%Y"),
            },
        )
        return json.loads(text)

    nse = NSE(download_folder="./.cache")
    try:
        return nse.listPastIPO(from_date=from_date, to_date=to_date)
    finally:
        try:
            nse.exit()
        except Exception:  # noqa: BLE001 - best-effort session cleanup
            pass


def _parse_nse_past_issue(rec: dict) -> dict:  # pragma: no cover - live only
    """Coerce one NSE ``public-past-issues`` record into a raw panel row.

    Field names CONFIRMED at the 05-11 live pull — the real keys are
    ``company``/``ipoStartDate``/``listingDate``/``issuePrice``/``symbol``
    (dates are DD-MON-YYYY, e.g. "14-JUL-2026"; ``issuePrice`` may be "-" for a
    not-yet-priced upcoming issue). Legacy guesses are kept as trailing fallbacks.
    ``symbol`` is threaded through so ``build._enrich_listing_closes`` can fetch the
    listing-day close (the target). A missing value coerces to None (→ NaN, never a
    fabricated survivor); this is the listed-core feed, so an unknown status
    defaults to ``listed``.
    """
    def pick(*keys: str) -> object:
        for key in keys:
            if key in rec and rec[key] not in (None, ""):
                return rec[key]
        return None

    issuer = pick("company", "companyName", "issuer")
    symbol = pick("symbol", "htmSym")
    return {
        "issuer": (str(issuer).strip() if issuer is not None else None),
        "symbol": (str(symbol).strip() if symbol is not None else None),
        "issue_date": coerce_date(pick("ipoStartDate", "issueStartDate", "issue_date")),
        "listing_date": coerce_date(pick("listingDate", "listing_date")),
        "issue_price": coerce_price(
            pick("issuePrice", "finalIssuePrice", "issue_price")
        ),
        "listing_day_close": coerce_price(pick("listingPrice", "listing_day_close")),
        "status_raw": pick("status", "series") or "listed",
    }


# ---------------------------------------------------------------------------
# Source B (D5-04) — withdrawn/pulled overlay (the P3 survivorship control):
# SEBI public-issues filings + chittorgarh withdrawn-offer-document report (202).
# ---------------------------------------------------------------------------


def fetch_sebi_withdrawn() -> list[dict]:  # pragma: no cover - live only
    """Source B (D5-04): the WITHDRAWN/PULLED overlay — the P3 survivorship control.

    Without this overlay the universe is survivor-only and FCAST-03/P3 fails. Merges
    SEBI's public-issues filings (issuer-side record of documents filed, incl. those
    that never listed) with chittorgarh's withdrawn-offer-document report (id 202).
    Every emitted row's ``status`` normalizes to ``withdrawn``. Fetches route through
    ``_get()`` (constant hosts, SSRF-checked); raw payloads are snapshotted (A1).
    Per-source failure isolation: one flaky source never empties the overlay.
    """
    rows: list[dict] = []
    # SEBI issuer-side filings (authoritative pre-2025 withdrawn source).
    try:
        rows.extend(fetch_sebi_offer_documents())
    except Exception as exc:  # noqa: BLE001 - per-source isolation
        logger.warning("SEBI public-issues filings fetch failed: %s", exc)
    # chittorgarh withdrawn report 202 (curated; newest slice from 2025-04 onward).
    try:
        rows.extend(_fetch_chittorgarh_withdrawn())
    except Exception as exc:  # noqa: BLE001 - per-source isolation
        logger.warning("chittorgarh withdrawn report fetch failed: %s", exc)
    # Force the overlay taxonomy: every row here is the withdrawn/pulled control.
    for row in rows:
        raw = row.get("status_raw")
        if raw is None or normalize_status(raw) != "withdrawn":
            row["status_raw"] = "withdrawn"
    return rows


def fetch_sebi_offer_documents() -> list[dict]:  # pragma: no cover - live only
    """Fetch SEBI issuer-side public-issues filings (withdrawals included).

    SEBI has no clean API and shifts its HTML; parse tolerantly and save the raw
    HTML alongside the parsed rows (A1). Feeds the P3 overlay via
    ``fetch_sebi_withdrawn``. Per-row parse failures are logged, never dropped.
    """
    from bs4 import BeautifulSoup  # deferred

    html = _get(SEBI_PUBLIC_ISSUES_URL)
    _save_raw("sebi_public_issues", html)
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    table = soup.find("table")
    if table is None:
        logger.warning("SEBI public-issues: no table found; site layout changed?")
        return rows
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 2:
            continue
        try:
            rows.append(
                {
                    "issuer": cells[0] or None,
                    "issue_date": coerce_date(cells[1]) if len(cells) > 1 else None,
                    "listing_date": None,
                    "issue_price": None,
                    "listing_day_close": None,
                    "status_raw": cells[-1] if len(cells) > 2 else "withdrawn",
                }
            )
        except Exception as exc:  # noqa: BLE001 - per-row isolation (T-05-02-VALID)
            logger.warning("SEBI row parse failed: %s", exc)
            continue
    return rows


def _recent_fy_end_years(back: int = 11) -> list[int]:
    """The END years of the last ``back`` Indian financial years (Apr–Mar).

    The FY ending in year ``E`` covers Apr(E-1)…Mar(E); chittorgarh's report path
    takes ``{E}/{E-1}-{EE}`` (e.g. 2026 / "2025-26"). Kept a pure date helper so
    it is unit-testable offline.
    """
    today = _dt.date.today()
    cur_end = today.year + 1 if today.month >= 4 else today.year
    return list(range(cur_end - back + 1, cur_end + 1))


def parse_chittorgarh_withdrawn_payload(payload: object) -> list[dict]:
    """Parse ONE chittorgarh webnodejs report-202 JSON payload into raw rows.

    Pure/offline (no network) so the JSON contract can be unit-tested. Each record
    carries ``Company`` as an HTML anchor (issuer text) and ``Offer Document Filed
    with SEBI`` as the DD-Mon-YYYY issue date. Every emitted row is ``withdrawn``.
    Per-row isolation: a malformed record is skipped, never fabricated.
    """
    from bs4 import BeautifulSoup  # deferred

    records = []
    if isinstance(payload, dict):
        records = payload.get("reportTableData") or []
    rows: list[dict] = []
    for rec in records:
        try:
            issuer = (
                BeautifulSoup(rec.get("Company") or "", "lxml").get_text(strip=True)
                or None
            )
            rows.append(
                {
                    "issuer": issuer,
                    "issue_date": coerce_date(rec.get("Offer Document Filed with SEBI")),
                    "listing_date": None,
                    "issue_price": None,
                    "listing_day_close": None,
                    "status_raw": "withdrawn",
                }
            )
        except Exception as exc:  # noqa: BLE001 - per-row isolation (T-05-02-VALID)
            logger.warning("chittorgarh withdrawn row parse failed: %s", exc)
            continue
    return rows


def _fetch_chittorgarh_withdrawn() -> list[dict]:  # pragma: no cover - live only
    """Withdrawn/pulled overlay from chittorgarh's webnodejs JSON API (report 202).

    The legacy HTML report migrated to a JS app (``soup.find("table")`` → None, the
    04-07 blocker); repointed to the JSON endpoint confirmed at the 05-11 live
    checkpoint. Iterates recent financial years and dedupes by (issuer, issue_date)
    — small per-FY counts, so a single page (size 50) covers each FY. Host is
    SSRF-checked via ``_get``; raw payloads are snapshotted (A1); per-FY failure
    isolation keeps one bad year from emptying the overlay.
    """
    headers = {
        "Referer": "https://www.chittorgarh.com/",
        "Accept": "application/json, text/plain, */*",
    }
    seen: set[tuple] = set()
    rows: list[dict] = []
    for end_year in _recent_fy_end_years():
        fy = f"{end_year - 1}-{str(end_year)[-2:]}"
        url = f"{CHITTORGARH_WITHDRAWN_API}/1/50/{end_year}/{fy}/0/0"
        try:
            payload = json.loads(_get(url, headers=headers))
        except Exception as exc:  # noqa: BLE001 - per-FY isolation
            logger.warning("chittorgarh withdrawn FY%s fetch failed: %s", fy, exc)
            continue
        _save_raw(f"chittorgarh_withdrawn_202_{fy}", payload)
        for row in parse_chittorgarh_withdrawn_payload(payload):
            key = ((row["issuer"] or "").strip().lower(), row["issue_date"])
            if row["issuer"] is None or key in seen:
                continue
            seen.add(key)
            rows.append(row)
    return rows


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


# ---------------------------------------------------------------------------
# Market-regime fetchers (D5-06b) — LIVE-DEFERRED seams (offline at import).
# ---------------------------------------------------------------------------
# These mirror ``fetch_listing_day_close`` exactly: a jugaad-data → yfinance → None
# fallback where every client is imported LAZILY inside the function, so importing
# this module (and the whole unit suite) stays fully offline — the real crawl is the
# deferred 05-11 checkpoint. Both are ``# pragma: no cover - live only``.
#
# The index identifiers below are module CONSTANTS — no URL/symbol is ever derived
# from an argument (SSRF T-05-08-SSRF); jugaad-data / yfinance manage their own hosts
# internally (same posture as ``fetch_listing_day_close``, no bare ``requests.get``).
#
# LEAKAGE (D5-08): callers snapshot NIFTY momentum / India-VIX as-of the pre-open
# (T0−1 EOD) day, so the regime features derived from these fetchers stay
# ``available_at <= T0`` — never a T0+ value. A miss returns ``None`` (→ NaN,
# RETAINED), never a fabricated level.
NIFTY_INDEX_SYMBOL = "NIFTY 50"       # jugaad-data index symbol (NIFTY momentum src)
INDIA_VIX_SYMBOL = "INDIA VIX"        # jugaad-data index symbol (India-VIX level)
NIFTY_YF_TICKER = "^NSEI"             # yfinance fallback ticker for NIFTY 50
INDIA_VIX_YF_TICKER = "^INDIAVIX"     # yfinance fallback ticker for India VIX


def fetch_nifty_history(
    end_date: _dt.date,
):  # pragma: no cover - live only
    """NIFTY 50 EOD close history up to ``end_date`` (jugaad-data → yfinance → None).

    Returns a DataFrame of NIFTY 50 daily closes for roughly the trailing ~13
    months ending at ``end_date`` (enough to compute 3M/6M momentum), or ``None``
    when neither source has data (→ the derived momentum features become NaN,
    RETAINED — never a fabricated return). Callers pass ``end_date = T0−1`` so the
    momentum snapshot is strictly pre-open (D5-08, ``available_at <= T0``).

    jugaad-data ``index_df`` is the primary source (per CLAUDE.md — the NIFTY
    momentum source), imported lazily; ``yfinance`` ``^NSEI`` is the fallback. No
    URL/symbol is derived from ``end_date`` (SSRF T-05-08-SSRF).
    """
    from_date = end_date - _dt.timedelta(days=400)  # > 6 months of trading history
    # Primary: jugaad-data NSE index history.
    try:
        from jugaad_data.nse import index_df  # deferred — keeps import offline

        df = index_df(
            symbol=NIFTY_INDEX_SYMBOL, from_date=from_date, to_date=end_date
        )
        if df is not None and not df.empty:
            return df
    except Exception as exc:  # noqa: BLE001 - fall through to yfinance
        logger.info("jugaad-data NIFTY history miss: %s", exc)

    # Fallback: yfinance ^NSEI.
    try:
        import yfinance as yf  # deferred

        hist = yf.Ticker(NIFTY_YF_TICKER).history(
            start=from_date, end=end_date + _dt.timedelta(days=1)
        )
        if hist is not None and not hist.empty:
            return hist
    except Exception as exc:  # noqa: BLE001 - honest miss => None
        logger.info("yfinance NIFTY history miss: %s", exc)

    return None


def fetch_india_vix(
    as_of: _dt.date,
) -> float | None:  # pragma: no cover - live only
    """India-VIX level as-of ``as_of`` (jugaad-data → yfinance → None).

    Returns the most-recent India-VIX close at or before ``as_of`` as a float, or
    ``None`` (→ NaN, RETAINED) when neither source has the level — never a
    fabricated value. Callers pass ``as_of = T0−1`` so the level is strictly
    pre-open (D5-08, ``available_at <= T0``).

    jugaad-data ``index_df`` is primary (lazy import), ``yfinance`` ``^INDIAVIX``
    the fallback; no symbol/URL is derived from ``as_of`` (SSRF T-05-08-SSRF).
    """
    from_date = as_of - _dt.timedelta(days=10)  # a short window to find the last close
    # Primary: jugaad-data NSE index history.
    try:
        from jugaad_data.nse import index_df  # deferred

        df = index_df(
            symbol=INDIA_VIX_SYMBOL, from_date=from_date, to_date=as_of
        )
        if df is not None and not df.empty and "CLOSE" in df.columns:
            close = coerce_price(df.iloc[-1]["CLOSE"])
            if close is not None:
                return close
    except Exception as exc:  # noqa: BLE001 - fall through to yfinance
        logger.info("jugaad-data India VIX miss: %s", exc)

    # Fallback: yfinance ^INDIAVIX.
    try:
        import yfinance as yf  # deferred

        hist = yf.Ticker(INDIA_VIX_YF_TICKER).history(
            start=from_date, end=as_of + _dt.timedelta(days=1)
        )
        if hist is not None and not hist.empty and "Close" in hist.columns:
            close = coerce_price(float(hist.iloc[-1]["Close"]))
            if close is not None:
                return close
    except Exception as exc:  # noqa: BLE001 - honest miss => None
        logger.info("yfinance India VIX miss: %s", exc)

    return None


__all__ = [
    "ALLOWED_HOSTS",
    "CHITTORGARH_IPO_INDEX",
    "NSE_PAST_ISSUES_URL",
    "SEBI_PUBLIC_ISSUES_URL",
    "CHITTORGARH_WITHDRAWN_REPORT",
    "CHITTORGARH_WITHDRAWN_API",
    "NIFTY_INDEX_SYMBOL",
    "INDIA_VIX_SYMBOL",
    "coerce_price",
    "coerce_date",
    "normalize_status",
    "parse_chittorgarh_withdrawn_payload",
    "fetch_nse_past_issues",
    "fetch_sebi_withdrawn",
    "fetch_chittorgarh_index",
    "fetch_sebi_offer_documents",
    "fetch_listing_day_close",
    "fetch_nifty_history",
    "fetch_india_vix",
]
