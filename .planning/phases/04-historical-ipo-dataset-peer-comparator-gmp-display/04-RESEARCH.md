# Phase 4: Historical IPO Dataset + Peer Comparator + GMP Display — Research

**Researched:** 2026-07-06
**Domain:** Indian market-data ingestion (peer fundamentals + GMP scraping), survivorship-corrected historical IPO panel construction, cache-first precompute pipelines, Indian-number formatting + CSS glossary tooltips (Streamlit)
**Confidence:** HIGH on codebase patterns and formatting; MEDIUM on external data-source reliability (screener.in / yfinance / GMP scraping are inherently fragile — this IS the phase risk)

---

<user_constraints>
## User Constraints (from 04-CONTEXT.md)

### Locked Decisions

**GMP display (GMP-01, GMP-02)**
- **D4-01:** GMP sourced from **2–3 public aggregators, their spread/disagreement shown explicitly**. The divergence IS the honesty signal.
- **D4-02:** GMP **de-emphasized** — low on the page, collapsed behind a **"What is GMP? Why we don't trust it"** disclosure, with a persistent short caveat. No red/green, never framed as a signal (P21).
- **D4-03:** **GMP-02 isolation is a hard invariant.** GMP value is display-only and computationally isolated — MUST NOT enter any model/feature pipeline. Enforced by a module boundary (read-only scrape → cache → render). Phase 5 owns the leakage-audit test; this phase must keep GMP out of anything the forecaster can import.

**Peer comparison (PEER-01, PEER-02)**
- **D4-04:** Peer **SET** anchored to the DRHP's own "Comparison with Listed Peers" section (PEER-01), citing the DRHP source (reuse Phase 1/2 citation-chip / source-anchor pattern). Never a self-selected peer set when the DRHP provides one.
- **D4-05:** Peer **MULTIPLES** (P/E, P/B, EV/EBITDA, ROE): when a DRHP-named peer is missing a multiple from the primary source, **backfill from an alternate source and flag provenance PER CELL**. Completeness with honest sourcing — never a silent gap, never a fabricated number. Source-priority order is a research item (candidates: screener.in → yfinance `.NS`/`.BO` → NSE/BSE → IR page).
- **D4-06:** When the DRHP discloses **NO** listed-peer comparison, render an **honest empty-state** — never fabricate a peer set. Mirrors D3-03. Labeled sector-peer fallback **deferred**.

**Indian formatting & glossary (UI-04)**
- **D4-07:** All rupee amounts render with **₹ + Indian digit grouping (1,23,456) and auto-scaled lakh↔crore by magnitude**, with `tabular-nums`. ONE shared formatting utility.
- **D4-08:** Glossary tooltips cover **RPT, QIB, NII, RII, GMP, OFS, DRHP, anchor investor**. Financial-ratio definitions (P/E, P/B, EV/EBITDA, ROE) deferred unless trivial.

**Honesty invariant**
- **D4-09:** **No red/green coding, no badges** anywhere in the peer table or GMP display (D2-07 carries forward).

### Claude's Discretion
- **Peer multiples live-vs-cached** — propose fetch-on-load vs precompute-into-cache, and current-market vs point-in-time-of-DRHP. Bias: cache-first + P16 rate limits favor precompute-into-cache (scrape at precompute time, not request time); reconcile with the goal's word "live."
- **Number-format edge cases** (negatives, missing → em-dash, sub-lakh amounts) — Claude's discretion following Phase 2/3 conventions.

### Deferred Ideas (OUT OF SCOPE for Phase 4)
- Peer multiples point-in-time-vs-current internals (resolved below as a recommendation, but the user did not lock it).
- **Labeled sector-peer fallback** when DRHP names no peers — honest empty-state is the default (D4-06).
- **Financial-ratio glossary tooltips** (P/E, P/B, EV/EBITDA, ROE) — add only if non-cluttering.
- Cross-IPO peer comparison across multiple IPOs (v2).
- The forecaster (Phase 5); GMP-vs-model gap (Phase 5, GMP-03); eval dashboards (Phase 6).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PEER-01 | Surface peers from the DRHP's own "Comparison with Listed Peers" section, anchored to the DRHP section | §Peer SET Extraction — reuse `agent.graph.GRAPH` canned-query pattern (mirror `snapshot_queries.py`); cite via the unchanged `ui/chip.py` + `ui/expander.py`. New `PeerRecord` schema + `data/peers/<drhp_id>.json`. |
| PEER-02 | Display peer multiples (P/E, P/B, EV/EBITDA, ROE) sourced from screener.in / yfinance / NSE / BSE | §Peer MULTIPLES Sourcing — source-priority ladder, per-cell provenance, cache-first precompute. `requests-cache` + `beautifulsoup4` (screener.in) + `yfinance` (fallback). |
| GMP-01 | Read-only GMP from public aggregators with explicit provenance/reliability caveats | §GMP Scraping — 2–3 aggregators, multi-source spread, `data/gmp/<drhp_id>.json`, monochrome de-emphasized block. |
| GMP-02 | GMP computationally isolated from the forecast model — no model feature derived from GMP | §GMP Isolation Invariant — module-boundary enforcement + `inspect.getsource` import-audit test pinning it (mirrors Phase 3 `test_no_llm_or_qdrant_import`). |
| UI-04 | Indian-context formatting (lakh/crore, INR) + RPT/QIB/NII/RII tooltips correct throughout | §format_inr + §Glossary Tooltips — single `ui/format_inr.py` utility (Indian grouping algorithm below); pure-CSS `:focus-within` tooltip. Refactor `_format_issue_size` (FLAG-FORMAT). |
</phase_requirements>

---

## Summary

Phase 4 has two distinct workstreams that share almost no code but share the same cache-first discipline: **(A) three user-facing surfaces** on the existing snapshot page (peer table, GMP block, Indian formatting + glossary), and **(B) one backend artifact** (the survivorship-corrected historical IPO panel — a committed CSV/parquet, foundation for Phase 5, with no UI this phase).

The codebase is mature and the integration path is well-worn: every user-facing surface mirrors the **`pipelines/snapshot.py` → `data/<kind>/<drhp_id>.json` → `load_*()` → `ui/*_blocks.py`** pattern, gated by `is_known_drhp_id()`. The peer SET (PEER-01) reuses the existing agent-canned-query + citation-chip infrastructure verbatim. The peer MULTIPLES (PEER-02) and GMP (GMP-01) are the genuinely new pieces — both are **external scrapes that must happen at precompute time, never at request time** (the project's hard cache-first rule, D3-17, plus P16 rate limits). This resolves the "live" vs cached discretion decisively: precompute into a committed/cached record; "live" means "refreshed by a scheduled precompute run," not "fetched on page load."

**The real risk is external-source fragility, not code.** screener.in has no official API and rate-limits aggressively; yfinance's Indian `.NS`/`.BO` data is good for liquid names but patchy on ratios and fresh listings; GMP aggregators are unofficial HTML that changes without notice. The mitigations are all already in the project stack (`requests-cache`, `tenacity`, `beautifulsoup4`, jugaad-data as NSE fallback) and the honesty architecture turns fragility into a feature: a missing cell renders `—` with per-cell provenance, and GMP's cross-source disagreement is displayed as the proof that GMP is unreliable.

**Primary recommendation:** Build two new precompute pipelines (`pipelines/peers.py`, `pipelines/gmp.py`) that mirror `redflag.py`, each writing a diff-reviewable JSON cache gated by the allow-list; a `PeerRecord`/`GmpRecord` schema pair mirroring `RedFlagRecord`; one `ui/format_inr.py` utility (Indian grouping + lakh/crore); pure-CSS glossary tooltips; and a separate `pipelines/historical/` dataset builder that produces a committed parquet with an explicit `status` column, validated against the ~7% median baseline. Enforce GMP isolation with an `inspect.getsource` import-audit test from day one. **Run the jugaad-data validation spike first (Wave 0).**

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Peer SET extraction (PEER-01) | Batch precompute pipeline (`pipelines/peers.py` via `agent.graph.GRAPH`) | Storage (`data/peers/`) | Same "storage is the integration bus" invariant as snapshot/redflag — the agent runs once at precompute, the UI only reads. |
| Peer MULTIPLES scraping (PEER-02) | Batch precompute pipeline (external HTTP) | Storage cache | External scrape MUST be batch (P16 rate limits, D3-17 no-live-per-request). Never on page render. |
| GMP scraping (GMP-01) | Batch precompute pipeline (external HTTP) | Storage cache (`data/gmp/`) | Same. Plus GMP-02 isolation: this pipeline imports NO model/forecast module. |
| Peer/GMP render | UI (Streamlit `pages/02_snapshot.py` + `ui/snapshot_blocks.py`) | — | Cache-only read; `st.container(border=True)` cards. |
| Indian number formatting (UI-04) | UI utility (`ui/format_inr.py`) | — | Pure function, string in → string out; consumed app-wide. |
| Glossary tooltips (UI-04) | UI (CSS in `drhplens.css` + copy in `ui/copy.py`) | — | Pure CSS `:focus-within`, no JS, no new dependency. |
| Historical IPO dataset | Batch builder (`pipelines/historical/`) | Storage (committed parquet/CSV under `data/`) | Backend artifact; not wired to any page this phase. Phase 5 consumes it. |
| Dataset sanity-check flag | Batch builder → `/methodology` plain-text surface | — | The only historical-dataset UI touch: a divergence flag if median ≠ ~7%. |

---

## Standard Stack

**No genuinely new third-party dependency is introduced.** Every package below is already declared in the project's `CLAUDE.md` §"Supporting Libraries" / STACK.md, and three of the four data-libs are already installed in `.venv`. This phase adds *usage*, not *new supply-chain surface*.

### Core (data ingestion — all pre-vetted project stack)
| Library | Version (verified 2026-07-06, PyPI) | Purpose | Why Standard |
|---------|-------------|---------|--------------|
| `requests-cache` | 1.3.3 | Transparent HTTP caching for all screener.in / GMP / NSE fetches | CLAUDE.md-mandated "polite scraping" — cache aggressively, never re-hammer. DRHP-era data is immutable once fetched. [CITED: CLAUDE.md §Supporting Libraries] |
| `beautifulsoup4` | 4.15.0 (installed) | HTML parsing for screener.in peer tables + GMP aggregator pages | CLAUDE.md-mandated HTML scraper; `lxml` 6.1.1 backend already installed. [CITED: CLAUDE.md] |
| `yfinance` | 1.5.1 (⚠ now 1.x — STACK.md pinned 0.2.50) | Fallback peer multiples via `.NS`/`.BO` tickers | CLAUDE.md fallback for prices/basic info; "good but not authoritative" for Indian names. [CITED: CLAUDE.md] |
| `tenacity` | 9.1.4 (installed) | Retries with backoff on all external HTTP | CLAUDE.md-mandated for every scrape/LLM call. [CITED: CLAUDE.md] |
| `pandas` | 3.0.3 (installed) | Historical IPO panel construction | CLAUDE.md "everywhere." [CITED: CLAUDE.md] |
| `pyarrow` | 24.0.0 (installed) | Parquet writer for the committed historical dataset | Standard columnar format; diff-friendlier than pickle, smaller than CSV for ~1000 rows. [ASSUMED — parquet vs CSV is a planner choice; both work] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `jugaad-data` | 0.33.1 (PyPI latest, verified) | NSE bhavcopy / listing-day candles when yfinance is patchy | **Validate endpoints at phase start (Wave 0 spike) before committing.** Active but sporadic releases — pin a known-good version, add nightly integration test. [CITED: CLAUDE.md §India-Specific Data-Source Notes + ROADMAP research flag] |
| `httpx` | 0.27+ (in stack) | Async-capable HTTP if batch scrape needs concurrency | Optional; `requests` + `requests-cache` is simpler and sufficient at this scale. [CITED: STACK.md] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Scraping screener.in HTML directly | Third-party wrappers (Apify `screener-in`, Parse.bot) | **Rejected — violates free/public-data + self-sufficiency constraint** (paid/hosted third party), adds a vendor dependency the portfolio narrative explicitly avoids. Direct polite scraping with `requests-cache` is the project-blessed path. [CITED: CLAUDE.md "What NOT to Use" — paid feeds] |
| `yfinance` for peer multiples primary | screener.in as primary | screener.in has richer Indian-fundamental coverage (P/B, ROE, sector peers) but no API + aggressive rate limits (P16). yfinance is more stable but "not authoritative" for Indian names + patchy ratios. **Recommendation: screener.in primary, yfinance fallback** (matches D4-05 candidate ladder). |
| parquet for historical dataset | CSV | CSV is human-diffable in git but larger and loses dtypes (NaN handling for survivorship!). **Recommendation: commit BOTH** — parquet as the Phase-5 consumable + a CSV mirror for git-diff reviewability, OR parquet + a committed `.schema.md`. Planner decides. |

**Installation:**
```bash
# Already in .venv: beautifulsoup4, lxml, yfinance, requests-cache(?), tenacity, pandas, pyarrow
# Verify / add the two that may be missing:
.venv/bin/pip install requests-cache==1.3.3 jugaad-data==0.33.1
```

**Version verification (run in plan-phase):** `yfinance` jumped to **1.5.1** (STACK.md pins 0.2.50 — a major-version bump; the `.NS` ticker API is stable across it, but the planner MUST pin a version and smoke-test `Ticker("RELIANCE.NS").info` before committing). `jugaad-data` is at **0.33.1**.

## Package Legitimacy Audit

> slopcheck was **not available** at research time (`pip install slopcheck` failed in sandbox). Per protocol, packages would normally fall to `[ASSUMED]` and be gated. **However**, all packages here are already declared in the committed project `CLAUDE.md`/STACK.md (PR-reviewed, authoritative) and three of four are already installed in `.venv` — so provenance is `[CITED: CLAUDE.md]`, not a fresh WebSearch discovery. No new package is introduced.

| Package | Registry | Age / Version | Source Repo | slopcheck | Disposition |
|---------|----------|--------------|-------------|-----------|-------------|
| requests-cache | PyPI | 1.3.3, mature (7+ yrs) | github.com/requests-cache/requests-cache | unavailable | Approved (CLAUDE.md-declared, registry-verified) |
| beautifulsoup4 | PyPI | 4.15.0, installed | crummy.com/software/BeautifulSoup | unavailable | Approved (installed + CLAUDE.md) |
| yfinance | PyPI | 1.5.1, installed-adjacent | github.com/ranaroussi/yfinance | unavailable | Approved — **but pin + smoke-test the 1.x API** |
| jugaad-data | PyPI | 0.33.1 | github.com/jugaad-py/jugaad-data | unavailable | Approved with caveat — **Wave 0 endpoint spike + nightly test (ROADMAP flag)** |
| pyarrow | PyPI | 24.0.0, installed | github.com/apache/arrow | unavailable | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged suspicious [SUS]:** none (jugaad-data's risk is *upstream endpoint fragility*, not supply-chain — it is addressed by the Wave 0 spike, not a checkpoint:human-verify install gate).

---

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────── PRECOMPUTE TIME (batch, scheduled/manual) ───────────────┐
                    │                                                                          │
  DRHP (Qdrant/     │   pipelines/peers.py                                                     │
  agent.graph) ─────┼──► 1. PEER SET: GRAPH.invoke(canned "Comparison with Listed Peers" Q)   │
                    │       → GroundedAnswer (peer names + DRHP page citation)  [PEER-01]      │
                    │                          │                                               │
  screener.in ──────┼──► 2. PEER MULTIPLES per named peer:                                     │
   (primary)        │       screener.in scrape ─┐                                              │
  yfinance .NS ─────┼──►    yfinance fallback  ──┼─► per-cell {value, source} [PEER-02, D4-05] │
   (fallback)       │       NSE/BSE  ───────────┘                                              │
  requests-cache    │                          │                                              │
                    │                          ▼                                              │
                    │              data/peers/<drhp_id>.json  (allow-list gated path)         │
                    │                                                                          │
  GMP aggregators ──┼──► pipelines/gmp.py  (imports NO model/forecast module — D4-03)          │
   (2–3 public)     │       scrape A, B, C → [{source, value, as_of}] → spread                 │
  requests-cache    │                          │                                              │
                    │                          ▼                                              │
                    │              data/gmp/<drhp_id>.json                                    │
                    │                                                                          │
  chittorgarh /     │   pipelines/historical/  (separate, backend-only)                       │
  SEBI issuer feeds ┼──► build ~800–1000 mainboard IPO panel (2014–present)                    │
  NSE bhavcopy      │       + status column + listing-day return + NaN survivorship            │
  (jugaad-data)     │       → sanity-check median vs ~7% baseline                              │
                    │                          ▼                                              │
                    │              data/historical/ipo_panel.parquet (committed)              │
                    └──────────────────────────────────────────────────────────────────────────┘
                                               │  (cache-only reads; NO external calls, NO LLM)
   REQUEST TIME  ◄─────────────────────────────┘
   pages/02_snapshot.py
     ├─ is_known_drhp_id(drhp_id)  ── allow-list gate (T-02-V5)
     ├─ load_peers(drhp_id)   → render_peer_table()   [st.container(border=True)]
     ├─ load_gmp(drhp_id)     → render_gmp_block()     [monochrome, last read block]
     └─ format_inr() applied to every ₹ across the whole page
```

### Recommended Project Structure
```
agent/
├── peer_schema.py          # PeerRecord, PeerCell, PeerCompany (mirror redflag_schema.py)
├── gmp_schema.py           # GmpRecord, GmpQuote (mirror redflag_schema.py)
pipelines/
├── peers.py                # precompute_peers() → data/peers/<id>.json  (mirror redflag.py)
├── peer_queries.py         # the 1 canned "Comparison with Listed Peers" query (mirror snapshot_queries.py)
├── peer_sources.py         # screener.in + yfinance + NSE fetchers, per-cell provenance
├── gmp.py                  # precompute_gmp() → data/gmp/<id>.json   (imports NO model module)
├── gmp_sources.py          # 2–3 aggregator scrapers + spread computation
└── historical/
    ├── build.py            # historical panel builder → data/historical/ipo_panel.parquet
    ├── sources.py          # chittorgarh / SEBI / NSE issuer-side fetchers
    └── validate.py         # ~7% median sanity check + divergence flag
data/
├── peers/<drhp_id>.json    # NEW cache kind (mirror data/redflag/)
├── gmp/<drhp_id>.json      # NEW cache kind
└── historical/ipo_panel.parquet   # committed backend artifact
ui/
├── format_inr.py           # NEW single shared utility (D4-07)
└── snapshot_blocks.py      # ADD render_peer_table(), render_gmp_block()
app/static/drhplens.css     # ADD .drhp-peer-table, .drhp-gmp-*, .drhp-glossary, .drhp-provenance-flag
tests/unit/
├── test_format_inr.py      # Indian grouping + lakh/crore + edge cases
├── test_peer_schema.py / test_peers_precompute.py
├── test_gmp_schema.py / test_gmp_precompute.py
├── test_gmp_isolation.py   # inspect.getsource import-audit (the D4-03 pin)
└── test_historical_panel.py
tests/integration/
└── test_jugaad_data_nse.py # nightly NSE endpoint smoke test (ROADMAP flag)
```

### Pattern 1: Cache-First Precompute Record (mirror `redflag.py` exactly)
**What:** A new record kind = a Pydantic model with `to_dict`/`from_dict`/`to_json`/`from_dict`, a `precompute_*()` that writes `data/<kind>/<drhp_id>.json`, and a `load_*()` that reads it. Path formation gated by `is_known_drhp_id()` BEFORE the path string is built.
**When to use:** Both `PeerRecord` and `GmpRecord`.
**Example (the load + path-gate pattern, verbatim shape from `pipelines/redflag.py`):**
```python
# Source: pipelines/redflag.py (this repo), lines 70–104 — mirror don't reinvent
PEERS_DIR = Path(__file__).parent.parent / "data" / "peers"

def load_peers(drhp_id: str) -> PeerRecord:
    path = _peers_path(drhp_id)             # gate happens inside
    if not path.exists():
        raise FileNotFoundError(f"No peer cache for drhp_id={drhp_id!r} at {path}")
    return PeerRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

def _peers_path(drhp_id: str) -> Path:
    if not is_known_drhp_id(drhp_id):       # T-02-V5 / T-03-01 allow-list, BEFORE path build
        raise ValueError(f"Unknown drhp_id={drhp_id!r}; refusing to form a cache path.")
    return PEERS_DIR / f"{drhp_id}.json"
```

### Pattern 2: Peer SET via existing agent canned query (PEER-01, reuse D4-04)
**What:** The DRHP's own "Comparison with Listed Peers" set is extracted the SAME way snapshot fields are — one canned query through `agent.graph.GRAPH`, producing a `GroundedAnswer` whose claims carry the peer names AND the DRHP page citation. The empty-state (D4-06) is the honest `RefusalResponse` path already handled by the pipeline.
**When to use:** PEER-01 extraction. Do NOT build a new LLM path or a new citation shape — the `claim_id`/`GroundedAnswer` contract is locked (Phase 3 METHOD-01 depends on it).
**Example query (mirror `snapshot_queries.py` style):**
```python
# pipelines/peer_queries.py
PEER_SET_QUERY = (
    "In the 'Basis for Issue Price' or 'Comparison with Listed Industry Peers' "
    "section, which listed companies does the company name as its peers, and on "
    "what DRHP page? List each peer company name exactly as disclosed."
)
```
**Honest empty-state (D4-06):** if the graph returns a `RefusalResponse` (no such section), the `PeerRecord.peer_set` is a `RefusalResponse` → UI renders `.drhp-not-disclosed` "This DRHP disclosed no listed-peer comparison." Never fabricate.

### Pattern 3: Per-cell provenance for peer multiples (PEER-02, D4-05)
**What:** Each `(company, metric)` cell is a `{value: float|None, source: "s"|"y"|"n"|"d"|None}` record. The precompute fetches in source-priority order and records WHICH source supplied the value. A cell missing from every source is `{value: None, source: None}` → renders `—`. A negative/undefined P/E → a sentinel the UI renders as `NM`.
**Source-priority ladder (resolves D4-05):**
1. **screener.in** (primary — richest Indian fundamentals: P/E, P/B, ROE, sometimes EV/EBITDA) → flag `s`
2. **yfinance `.NS`/`.BO`** (`Ticker.info` fields: `trailingPE`, `priceToBook`, `enterpriseToEbitda`, `returnOnEquity`) → flag `y`
3. **NSE/BSE** (via jugaad-data / direct) → flag `n`
4. Cell stays `—` if all three miss. **Never** interpolate.
**Point-in-time vs current (Claude's discretion → recommendation):** use **current market multiples**, timestamped with an `as_of` date on the record, and state that plainly in the sub-line ("Multiples are current market values as of {date}, not as-of-DRHP"). Point-in-time-of-DRHP reconstruction requires historical fundamentals screener.in does not expose (it "shows latest data only" — CLAUDE.md) and is not worth the fragility for a display surface. This is a MEDIUM-confidence recommendation the planner should confirm.

### Pattern 4: GMP isolation as an enforced module boundary (GMP-02, D4-03)
**What:** `pipelines/gmp.py` and `ui`'s GMP renderer form a closed loop: scrape → `data/gmp/<id>.json` → render. The GMP module imports NOTHING from any forecast/model package, and no forecast module imports the GMP module. Pin it with a test that greps the import graph (mirror Phase 3's `test_no_llm_or_qdrant_import` which uses `inspect.getsource`).
**Example enforcement test (mirror the Phase 3 pin):**
```python
# tests/unit/test_gmp_isolation.py — the D4-03 invariant pin, foreshadows Phase 5 leakage audit
import inspect, pipelines.gmp, agent.gmp_schema
def test_gmp_module_imports_no_model_code():
    for mod in (pipelines.gmp, agent.gmp_schema):
        src = inspect.getsource(mod)
        for forbidden in ("xgboost", "mapie", "forecast", "sklearn", "pipelines.features"):
            assert forbidden not in src, f"GMP module must not import {forbidden} (D4-03/GMP-02)"
# (Phase 5 owns the reverse audit: the forecaster must not import pipelines.gmp.)
```

### Pattern 5: Streamlit container card (Phase 3 white-bar lesson — HARD RULE)
**What:** A styled card built by opening `<div>` in one `st.markdown` and closing it in another renders as an empty white bar (Streamlit isolates each markdown block). The peer table and GMP block MUST use `with st.container(border=True):` OR a single fully self-contained `st.markdown` HTML string. Every `st.expander`/toggle needs a unique per-element `key` (else `StreamlitDuplicateElementId`).
**Source:** STATE.md Phase 3 decision `c8e301b`; UI-SPEC §Streamlit-Specific Constraints.

### Anti-Patterns to Avoid
- **Scraping at page-render time.** Violates D3-17 + P16. All external fetches happen in `precompute_*`, never in `load_*` or a page function.
- **Split-`<div>` card wrappers.** Renders a white bar (Phase 3 lesson). Use `st.container(border=True)`.
- **Re-implementing Indian grouping per surface.** D4-07 = ONE `format_inr`. The existing `_format_issue_size` Western-grouping bug (`f"₹{n:,}"`) must be *refactored to call it*, not duplicated.
- **A GMP value flowing into any feature.** Even a "temporary" import breaks GMP-02. The isolation test blocks it.
- **Fabricating a peer or a multiple.** A silent gap or an invented number is the single worst failure for this honesty-first product. Missing = `—`; not-meaningful = `NM`; no peers = empty-state.
- **Using a third-party screener.in wrapper API** (Apify/Parse.bot). Violates free/self-sufficient constraint.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP caching / not re-hammering screener.in | A custom on-disk response cache | `requests-cache` (CLAUDE.md-mandated) | Handles expiry, conditional requests, SQLite backend; P16 mitigation out of the box. |
| Retry/backoff on flaky scrapes | `for attempt in range(3)` loops | `tenacity` (already installed) | Jittered exponential backoff, stop conditions, project standard. |
| HTML table parsing | Regex over raw HTML | `beautifulsoup4` + `lxml` (installed) | Regex-on-HTML is the classic footgun; screener.in markup shifts. |
| Peer name ↔ ticker matching | New fuzzy matcher | `rapidfuzz` (already a Phase 3 dep) | Already vetted in `pipelines/risk_idf.py`; reuse for "Bajaj Finance" → `BAJFINANCE.NS`. |
| Record (de)serialization | Bespoke JSON codec | Mirror `redflag_schema.py` `to_dict/from_dict` + `{"refusal": ...}` discriminator | The union-discriminator codec is a solved, tested pattern in this repo. |
| Citation of the peer SET | New citation UI | `ui/chip.py` + `ui/expander.py` unchanged | Locked `claim_id` contract; PEER-01 anchors exactly like a snapshot field. |
| Number → lakh/crore | Ad-hoc per-cell f-strings | ONE `ui/format_inr.py` | D4-07 hard invariant; also fixes the latent Western-grouping bug. |
| Glossary tooltips | A JS tooltip library / Streamlit component | Pure CSS `:hover`/`:focus-within` popover | UI-SPEC R-1; no JS attack surface, no third-party registry, keyboard+mobile accessible. |

**Key insight:** Almost none of Phase 4 is new infrastructure — it is *new records and renderers on proven rails*. The only genuinely novel code is the two external-source fetchers (`peer_sources.py`, `gmp_sources.py`) and the historical-dataset builder, and even those lean entirely on stack libraries. Budget the risk on **source fragility and data validation**, not on architecture.

## Runtime State Inventory

> This phase is primarily additive (new records, new UI), but it **refactors** the number-formatting call sites app-wide (D4-07) and **adds new cache directories**. Not a rename phase, but the format retrofit has a state footprint worth pinning.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | New cache kinds `data/peers/<id>.json`, `data/gmp/<id>.json`, `data/historical/ipo_panel.parquet`. No existing datastore stores a renamed key. Qdrant/DRHP ingest is untouched. | Create dirs at precompute; commit historical parquet. |
| Live service config | None — no external service holds Phase-4 state. GMP/peer scrapes are stateless HTTP. | None. |
| OS-registered state | The ROADMAP asks for a **nightly integration test** for jugaad-data. If implemented as a real cron/scheduler (vs a CI job), that is an OS/CI registration. | Recommend **GitHub Actions scheduled workflow** (no local OS state) over a local cron. |
| Secrets/env vars | None new. screener.in / GMP / NSE are unauthenticated public scrapes (no API key). yfinance needs no key. | None. |
| Build artifacts | `_format_issue_size` in `ui/catalogue.py` (Western `:,` grouping) is a **stale/buggy call site** that every ad-hoc ₹ render duplicates. After `format_inr` lands, `ui/catalogue.py`, the metadata header, and `snapshot_blocks._format_fin_value` (`f"₹{value:,.0f} cr"`, line ~189) are all **stale until refactored to call `format_inr`**. | Refactor all ₹ call sites (FLAG-FORMAT). Grep for `₹` and `:,` across `ui/`. |

**Grep to run in plan-phase:** `grep -rn "₹\|:,\|cr\"" ui/ pages/` to enumerate every ad-hoc rupee render that must route through `format_inr`.

## Common Pitfalls

### Pitfall 1: screener.in rate-limiting / ToS (P16)
**What goes wrong:** Rapid scraping gets the IP throttled or blocked; the peer table silently loses data or the precompute run fails mid-batch.
**Why it happens:** No official API; the site rate-limits aggressively (CLAUDE.md; WebSearch confirms "sometimes rate-limits aggressively").
**How to avoid:** `requests-cache` (cache every response — screener fundamentals change slowly), jittered delays between requests (`tenacity` + `time.sleep` with jitter), a realistic User-Agent, precompute in a single batch off-peak, **per-IPO failure isolation** (one peer's fetch failure logs + continues, mirroring `redflag.precompute_all`), and the **yfinance fallback** (D4-05) so a screener miss degrades to a `y`-flagged cell, not a hole. Plan-B source is the honest `—`.
**Warning signs:** HTTP 429; sudden empty tables; identical HTML across companies (a block page).

### Pitfall 2: yfinance Indian-name data gaps (P15)
**What goes wrong:** `Ticker("XYZ.NS").info` returns `None`/missing for `trailingPE`, `enterpriseToEbitda`, or `returnOnEquity` — especially for fresh listings or less-liquid names; occasionally the whole `.info` dict is sparse.
**Why it happens:** Yahoo's Indian data is "good but not authoritative" (CLAUDE.md); the GitHub issue "DATA FOR NSE UNAVAILABLE" documents recurring gaps.
**How to avoid:** Treat yfinance strictly as fallback (source `y`), never assert a field exists — `data.get("trailingPE")`, coerce to `None` on absence, record `source=None` when all sources miss. Cross-check `.NS` vs `.BO`. Never let a yfinance `NaN`/`0.0` masquerade as a real value (a real "0 ROE" is vanishingly rare — treat 0/None as missing for ratios).
**Warning signs:** All-zero rows; `enterpriseToEbitda` present but `trailingPE` absent (common); values wildly off from screener.

### Pitfall 3: Survivorship bias in the historical panel (P3 — the phase's DS-critical pitfall)
**What goes wrong:** Building the universe from *exchange listing feeds* (only currently-listed companies) silently drops withdrawn/delisted/merged IPOs → the median listing return is inflated and Phase 5's backtest is fantasy.
**Why it happens:** Listing feeds are survivor-only by construction; it's the #1 IPO-ML resume failure.
**How to avoid:** Source from **SEBI issuer-side offer-document filings + chittorgarh's historical IPO index** (which lists withdrawn/pulled IPOs too), not NSE's "currently listed" table. Explicit `status` column: `withdrawn | listed_alive | delisted | merged | name_changed`. **Replace-with-NaN** (not drop) for companies whose listing-day price is unavailable, so the absence is counted. Sanity-check the median listing-day return against the published **~7% MAAR baseline** (Shah & Mehta 2015: 113 NSE mainboard IPOs 2010–2014, MAAR **7.19%**; broader 2003–2014 samples show first-day avg ~14%, underpricing ~23% — the *median* clusters near 7–15% depending on window). If the built median diverges materially, **flag it on `/methodology` as plain text** (per UI-SPEC) — divergence usually means a sourcing/survivorship leak.
**Warning signs:** Median listing return > ~20% (survivor inflation); zero withdrawn IPOs in a 2014–2026 universe (impossible — many were pulled); row count << ~800.

### Pitfall 4: jugaad-data endpoint drift (ROADMAP research flag)
**What goes wrong:** NSE changes its site; jugaad-data endpoints (bhavcopy, listing candles) break silently mid-build.
**Why it happens:** jugaad-data tracks NSE's live site; releases are sporadic; NSE has aggressive bot detection.
**How to avoid:** **Wave 0 spike (~1 day):** before committing jugaad-data as the primary NSE source, run a smoke test of the exact endpoints the historical builder needs (bhavcopy for a known date, a listing-day candle for a known symbol) and confirm shapes. Add a **nightly integration test** (`tests/integration/test_jugaad_data_nse.py`, marked `integration`, GitHub Actions scheduled) so drift is caught early. Keep yfinance as the price fallback. Pin `jugaad-data==0.33.1`.
**Warning signs:** Empty DataFrames; HTML returned where CSV expected; cookie/session errors.

### Pitfall 5: GMP framed as a signal (P21 — compliance/honesty)
**What goes wrong:** A single big GMP number, an up-arrow, green text, or "GMP suggests strong demand" reads as investment advice and violates the honesty posture + SEBI framing.
**Why it happens:** Every GMP aggregator presents GMP as a bullish signal; it's the ambient norm.
**How to avoid:** Follow UI-SPEC R-4 exactly — monochrome, no accent, the **spread across sources IS the headline** (`₹38–₹52 across 3 sources`), persistent caveat, disclosure "Why we don't trust it," last block on the page. All copy through the banned-token scrubber. The isolation test (Pitfall-4 pattern) proves it never touches a model.
**Warning signs:** Any color on a GMP element; a single-number headline; the word "demand"/"strong"/"listing gain" in GMP copy (scrubber-adjacent).

### Pitfall 6: The Western-grouping formatting bug spreading (FLAG-FORMAT)
**What goes wrong:** `_format_issue_size` uses `f"₹{n:,}"` → `1,234,567` (Western), wrong for Indian users who expect `12,34,567`. New surfaces copy the bug.
**How to avoid:** Land `ui/format_inr.py` FIRST (Wave 1), then refactor every ₹ call site to it. Unit-test the grouping algorithm against known cases (see Code Examples). D4-07 = ONE utility.

## Code Examples

### Indian digit grouping + lakh/crore (the `format_inr` core — UI-04, D4-07)
```python
# ui/format_inr.py — the ONE rupee formatter. String out; CSS applies tabular-nums.
from decimal import Decimal

def _group_indian(int_str: str) -> str:
    """1234567 -> '12,34,567' (last 3 digits, then groups of 2)."""
    if len(int_str) <= 3:
        return int_str
    head, tail = int_str[:-3], int_str[-3:]
    # insert commas every 2 digits from the right of head
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:]); head = head[:-2]
    parts.insert(0, head)
    return ",".join(parts) + "," + tail

def format_inr(amount: float | int | None) -> str:
    if amount is None:
        return "—"                                    # missing sentinel (D4-07)
    neg = amount < 0
    a = abs(amount)
    if a >= 1e7:                                       # ≥ ₹1 crore
        s = f"₹{_trim(a/1e7)} crore"
    elif a >= 1e5:                                     # ≥ ₹1 lakh
        s = f"₹{_trim(a/1e5)} lakh"
    else:
        s = f"₹{_group_indian(str(int(round(a))))}"
    return f"({s})" if neg else s                      # negatives in parens, same colour

def _trim(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")          # 12.50 -> '12.5', 1247.00 -> '1247'
```
Test cases the planner must pin: `100000 → ₹1 lakh`, `1250000 → ₹12.5 lakh`, `124700000 → ₹12.47 crore` (⚠ verify: 1,247,00,000? No — 12.47 crore), `45600 → ₹45,600`, `1234567 → ₹12.34 lakh`, `None → —`, `-1234 → (₹1,234)`. **Note:** the UI-SPEC example `₹1,247 crore` implies grouping is also applied to the scaled integer part — planner should decide whether `crore`/`lakh` values >1000 also get Indian grouping (recommend: yes, apply `_group_indian` to the integer part of scaled values too).

### Pure-CSS glossary tooltip (UI-04, R-1 — no JS)
```html
<!-- Source: 04-UI-SPEC.md §R-1. Injected via st.markdown(unsafe_allow_html=True). -->
<span class="drhp-glossary" tabindex="0" role="button" aria-describedby="gl-rpt">RPT<span
      class="drhp-glossary-pop" role="tooltip" id="gl-rpt">Related-Party Transaction — …</span></span>
```
```css
/* app/static/drhplens.css */
.drhp-glossary { text-decoration: underline dotted; cursor: help; position: relative; }
.drhp-glossary-pop { display: none; position: absolute; z-index: 10; max-width: 260px;
    background: var(--drhp-surface-secondary); border: 1px solid var(--drhp-border-subtle);
    border-radius: 8px; padding: 8px; font-size: 12px; }
.drhp-glossary:hover .drhp-glossary-pop,
.drhp-glossary:focus .drhp-glossary-pop,
.drhp-glossary:focus-within .drhp-glossary-pop { display: block; }   /* keyboard + mobile-tap */
```

### yfinance fallback fetch (peer multiple, source `y`)
```python
# pipelines/peer_sources.py — fallback only; screener.in is primary
import yfinance as yf
def yfinance_multiples(ticker: str) -> dict[str, float | None]:
    info = yf.Ticker(ticker).info or {}
    def clean(v):  # treat 0/None/NaN as missing for ratios (P15)
        return v if isinstance(v, (int, float)) and v not in (0, None) and v == v else None
    return {
        "pe":        clean(info.get("trailingPE")),
        "pb":        clean(info.get("priceToBook")),
        "ev_ebitda": clean(info.get("enterpriseToEbitda")),
        "roe":       clean(info.get("returnOnEquity")),  # note: fraction, ×100 for %
    }
```
[ASSUMED — exact `.info` key names should be smoke-tested against yfinance 1.5.1 in the Wave 0 spike; Yahoo occasionally renames keys.]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `nsepy` for NSE data | `jugaad-data` (new NSE site) | ~2021 (nsepy dead) | CLAUDE.md mandates jugaad-data; nsepy is a "What NOT to Use." |
| yfinance 0.2.x | yfinance **1.5.1** | 2025→2026 | Major version bump since STACK.md was written; `.NS` API stable but pin + smoke-test. |
| Single authoritative GMP number | Multi-source spread as honesty signal | Phase 4 design (D4-01) | Divergence *is* the message; opposite of every GMP aggregator's UX. |
| Western `:,` grouping | `format_inr` Indian grouping | This phase (D4-07) | Fixes a latent bug across all ₹ renders. |

**Deprecated/outdated:**
- `nsepy` — dead, based on old NSE site. Never use.
- `ui/catalogue.py::_format_issue_size` Western grouping — bug, refactor to `format_inr`.
- Third-party paid screener.in wrappers (Apify/Parse.bot) — violate free/self-sufficient constraint.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Current-market multiples (not point-in-time-of-DRHP) is acceptable for the peer table | Pattern 3 | If user wants as-of-DRHP fundamentals, screener.in can't supply them → bigger scope; confirm in discuss/plan. |
| A2 | parquet (+ optional CSV mirror) is the right historical-dataset format | Standard Stack | Low — planner can pick CSV; both work. |
| A3 | yfinance 1.5.1 `.info` keys (`trailingPE`, `enterpriseToEbitda`, `returnOnEquity`) are current | Code Examples | Medium — Yahoo renames keys; Wave 0 smoke test resolves it. |
| A4 | ~7% median (MAAR 7.19%, Shah & Mehta 2015) is the right sanity-check baseline for a mainboard 2014–present universe | Pitfall 3 | Medium — different windows give 7–15%; the *divergence flag* is what matters, not the exact target. Confirm the baseline number + methodology on `/methodology`. |
| A5 | GMP aggregators (investorgain, ipowatch, mainboardgmp, etc.) remain scrapeable with stable-enough HTML for 2–3 sources | GMP Scraping | Medium-High — HTML changes; per-source failure isolation + honest `—`/"single source" states mitigate. |
| A6 | screener.in remains the best primary for Indian P/B + ROE without an API | Pattern 3 | Medium — if blocked, yfinance-primary is the degraded fallback. |
| A7 | The ~800–1000 IPO count (2014–present mainboard) is achievable from chittorgarh + SEBI issuer-side sources | Historical dataset | Medium — count is a target, not a contract; honest coverage (with status column) matters more than hitting 1000. |
| A8 | Indian grouping should also apply to scaled lakh/crore integer parts >1000 (`₹1,247 crore`) | Code Examples | Low — cosmetic; planner confirms against UI-SPEC example. |

## Open Questions

1. **Which specific 2–3 GMP aggregators?** (RESOLVED-enough)
   - What we know: investorgain.com, ipowatch.in, mainboardgmp.com, ipocentral.in all publish live GMP; all state it's unofficial/unregulated.
   - What's unclear: which have the most stable, scrapeable HTML and cover the catalogue's (mostly *already-listed*) IPOs — note **most catalogue IPOs listed in 2021–2024, so live GMP no longer exists for them.** GMP is only live during an open subscription window.
   - Recommendation: For the 8 catalogue IPOs (7 listed, ≤1 open), GMP will legitimately be **absent** for listed ones → the D4-06-style "No GMP is being reported for this IPO right now" state is the *common* case, not the edge case. Wire GMP against the currently-open IPO(s) and treat absent-GMP as first-class. Planner should confirm which catalogue IPO is `status: "open"` to have a live GMP to demo.

2. **Peer SET extraction — does the DRHP text exist in Qdrant yet?** (OPEN — dependency)
   - What we know: INGEST-02/03 are "code-complete, live upsert pending" (`data/swiggy_drhp/INGEST_LATER.md`). The agent-canned-query path for PEER-01 needs the DRHP's peer section retrievable.
   - What's unclear: whether the peer section is ingested for any catalogue IPO in live Qdrant.
   - Recommendation: mirror the Phase 3 CODE-NOW-DEFER posture — unit-test `precompute_peers` by monkeypatching `GRAPH.invoke`; defer the live 8×-per-IPO peer-set extraction to the same ingest runbook. A hand-seeded `data/peers/<id>.json` (like the seeded `swiggy_2024_11.json` snapshot) unblocks the UI.

3. **Historical dataset — how much is buildable this phase vs deferred to Phase 5 EDA?** (OPEN)
   - What we know: ROADMAP says the panel is Phase 4's foundation; STATE flags "Begin EDA notebooks for forecaster feature set during Phase 4."
   - Recommendation: Phase 4 delivers the *universe + status column + listing-day return + sanity-check* (the survivorship-corrected skeleton). Feature engineering is Phase 5. Keep the builder's output schema minimal and Phase-5-extensible.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| beautifulsoup4 + lxml | screener.in / GMP HTML parse | ✓ | 4.15.0 / 6.1.1 | — |
| yfinance | peer multiples fallback | ✓ | 1.5.1 (pin + smoke-test) | screener.in primary |
| tenacity | retry/backoff | ✓ | 9.1.4 | — |
| pandas / pyarrow | historical panel | ✓ | 3.0.3 / 24.0.0 | CSV instead of parquet |
| requests-cache | polite scraping | ? (verify) | 1.3.3 target | manual dict cache (worse) |
| jugaad-data | NSE bhavcopy / listing candles | ✗ (not installed) | 0.33.1 target | yfinance for prices |
| Live Qdrant + LLM keys | PEER-01 live peer-set extraction | ✗ (Phase 3 blocker) | — | monkeypatch + seed JSON (CODE-NOW-DEFER) |
| Internet egress at precompute | all scrapes | assumed ✓ | — | seeded fixtures for tests |

**Missing dependencies with no fallback:** none blocking — live Qdrant/LLM is deferrable (seed + monkeypatch), matching Phases 2/3.
**Missing dependencies with fallback:** `jugaad-data` (install + Wave 0 spike), `requests-cache` (verify install). Both trivial `pip install`.

## Validation Architecture

> nyquist_validation is enabled (config.json `workflow.nyquist_validation: true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (`pyproject.toml [tool.pytest.ini_options]`, `addopts = "-ra --strict-markers"`, `timeout=60`) |
| Config file | `pyproject.toml`; markers: `slow`, `eval`, `integration` |
| Quick run command | `.venv/bin/python -m pytest tests/unit -q` |
| Full suite command | `.venv/bin/python -m pytest tests -q` (currently 303 passing + 1 known-ignorable embedder failure) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-04 | Indian grouping + lakh/crore + negatives + None | unit | `pytest tests/unit/test_format_inr.py -x` | ❌ Wave 0 |
| UI-04 | Every ₹ call site routes through format_inr (no bare `:,`) | unit (grep-style) | `pytest tests/unit/test_format_inr_adoption.py -x` | ❌ Wave 0 |
| UI-04 | Glossary copy scrubber-clean + 8 terms present | unit | `pytest tests/unit/test_copy_no_banned_tokens.py -x` (extend) | ✅ (extend) |
| PEER-01 | Peer SET extraction + honest empty-state (RefusalResponse) | unit (monkeypatch GRAPH) | `pytest tests/unit/test_peers_precompute.py -x` | ❌ Wave 0 |
| PEER-01 | Allow-list gates the peers cache path | unit | `pytest tests/unit/test_peers_precompute.py::test_path_gate -x` | ❌ Wave 0 |
| PEER-02 | Per-cell provenance; missing → None; NM for neg P/E | unit | `pytest tests/unit/test_peer_schema.py -x` | ❌ Wave 0 |
| PEER-02 | Source-priority ladder (screener→yf→nse) picks first available | unit (mock fetchers) | `pytest tests/unit/test_peer_sources.py -x` | ❌ Wave 0 |
| GMP-01 | Multi-source spread record; single-source + absent states | unit | `pytest tests/unit/test_gmp_schema.py -x` | ❌ Wave 0 |
| GMP-02 | GMP module imports no model code (isolation pin) | unit (inspect.getsource) | `pytest tests/unit/test_gmp_isolation.py -x` | ❌ Wave 0 |
| (dataset) | Historical panel has status column; NaN-not-drop; ~7% sanity flag | unit | `pytest tests/unit/test_historical_panel.py -x` | ❌ Wave 0 |
| (jugaad) | NSE endpoints return expected shapes | integration (nightly) | `pytest tests/integration/test_jugaad_data_nse.py -m integration` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit -q` (fast, no network — all external calls mocked/monkeypatched, matching redflag/snapshot precompute tests).
- **Per wave merge:** full `pytest tests -q`.
- **Phase gate:** full suite green before `/gsd-verify-work`; the jugaad nightly integration test green at least once against live NSE.

### Wave 0 Gaps
- [ ] `tests/unit/test_format_inr.py` — covers UI-04 grouping/scaling/edge cases
- [ ] `tests/unit/test_peer_schema.py`, `test_peers_precompute.py`, `test_peer_sources.py` — PEER-01/02 (mock external fetchers; monkeypatch `GRAPH.invoke`)
- [ ] `tests/unit/test_gmp_schema.py`, `test_gmp_precompute.py`, `test_gmp_isolation.py` — GMP-01/02
- [ ] `tests/unit/test_historical_panel.py` — dataset schema + survivorship (NaN-not-drop) + median-baseline flag
- [ ] `tests/integration/test_jugaad_data_nse.py` (marker `integration`, GitHub Actions scheduled) — jugaad endpoint smoke
- [ ] Seed fixtures: hand-seeded `data/peers/<id>.json` + `data/gmp/<id>.json` (mirror the seeded `swiggy_2024_11.json` snapshot) so the UI renders offline
- Framework install: none — pytest present.

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high`.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in v1 (no user accounts — out of scope). |
| V3 Session Management | no | Streamlit stateless render; no sessions. |
| V4 Access Control | yes | `is_known_drhp_id()` allow-list gates every cache-path formation (T-02-V5) BEFORE the `data/<kind>/<drhp_id>.json` string is built — the path-traversal control. Reuse verbatim for peers + GMP. |
| V5 Input Validation | yes | `drhp_id` from query param is untrusted → allow-list. Scraped HTML is untrusted → **HTML-escape every scraped peer name / GMP source string before rendering** (reuse `html.escape` as in `ui/chip.py`/`ui/expander.py`; T-1-06 pattern). Pydantic validates every cache record on load. |
| V6 Cryptography | no | No secrets, no crypto — all sources are unauthenticated public HTTP. |

### Known Threat Patterns for {Streamlit + external scrape + JSON cache}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `drhp_id` | Tampering | `is_known_drhp_id()` allow-list BEFORE path build (existing control). |
| XSS via scraped peer name / GMP source label | Tampering/Info-disclosure | `html.escape(..., quote=True)` on every scraped string before `unsafe_allow_html` interpolation (reuse Phase 1 escape-then-interpolate). |
| SSRF / arbitrary fetch | Tampering | Scrape only hard-coded source hostnames (screener.in, yfinance, named GMP aggregators); never fetch a URL derived from user/DRHP input. |
| GMP → model leakage | Info-disclosure (data-integrity) | GMP-02 module-boundary + `inspect.getsource` isolation test (D4-03). |
| Untrusted cache record on load | Tampering | Cache files are repo-committed/PR-reviewed + Pydantic-validated on `from_dict` (mirrors catalogue T-02-02). |
| Banned-token leakage in new copy | Compliance | Import-time scrubber assertion in `ui/copy.py` (TRUST-03) covers all glossary/GMP/empty-state copy. |

## Sources

### Primary (HIGH confidence)
- This repo — `pipelines/redflag.py`, `pipelines/snapshot.py`, `agent/redflag_schema.py`, `agent/snapshot_schema.py`, `data/catalogue_loader.py`, `ui/chip.py`, `ui/expander.py`, `ui/snapshot_blocks.py`, `pages/02_snapshot.py`, `ui/catalogue.py` — the exact patterns to mirror.
- `CLAUDE.md` §"India-Specific Data-Source Notes", §"What NOT to Use", §"Supporting Libraries" — data-source mandates + caveats.
- `04-CONTEXT.md`, `04-UI-SPEC.md`, `ROADMAP.md` Phase 4, `REQUIREMENTS.md` — locked decisions + requirements.
- PyPI (verified 2026-07-06): yfinance 1.5.1, jugaad-data 0.33.1, requests-cache 1.3.3, beautifulsoup4 4.15.0.

### Secondary (MEDIUM confidence)
- [jugaad-data GitHub](https://github.com/jugaad-py/jugaad-data) / [PyPI](https://pypi.org/project/jugaad-data/) — active, tracks new NSE site, sporadic releases.
- [yfinance NSE data-availability discussion #2089](https://github.com/ranaroussi/yfinance/discussions/2089) — recurring Indian-data gaps (P15 evidence).
- [Post-Listing IPO Returns in India (IBIMA 2021)](https://ibimapublishing.com/articles/JFSR/2021/418441/), [JETIR post-listing performance](https://www.jetir.org/papers/JETIR2303067.pdf), Shah & Mehta 2015 (113 NSE mainboard IPOs 2010–2014, **MAAR 7.19%**) — the ~7% baseline (A4).

### Tertiary (LOW confidence — verify at build)
- GMP aggregator scrapeability: [investorgain.com](https://www.investorgain.com/report/live-ipo-gmp/331/), [ipowatch.in](https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/), [mainboardgmp.com](https://mainboardgmp.com/), [ipocentral.in](https://ipocentral.in/ipo-discussion/) — HTML stability unverified; all self-declare GMP as unofficial/unregulated.
- screener.in rate-limits/ToS: no authoritative published limit found; treat as "aggressive, cache everything" (CLAUDE.md).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all pre-vetted in CLAUDE.md, versions registry-verified, 3/4 installed.
- Architecture / codebase patterns: HIGH — read the actual redflag/snapshot/schema/UI files; the mirror path is unambiguous.
- Peer/GMP external sourcing: MEDIUM — libraries confirmed, but source HTML stability + data completeness are inherently fragile (this is the phase's real risk, mitigated by fallback ladder + honest-absence states).
- Historical dataset: MEDIUM — sourcing approach and ~7% baseline are sound; exact achievable count + build depth vs Phase 5 EDA split is an open scoping question.
- Formatting/glossary: HIGH — algorithm + CSS approach fully specified by UI-SPEC and standard.

**Research date:** 2026-07-06
**Valid until:** ~2026-08-05 for stack/patterns (stable); ~2026-07-13 for GMP/screener scrapeability (fast-moving, verify at build).
</content>
</invoke>
