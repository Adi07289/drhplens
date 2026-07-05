# Phase 4: Historical IPO Dataset + Peer Comparator + GMP Display - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

On an IPO page, a retail user sees three new user-facing surfaces plus one backend
foundation:

1. **Peer-multiples comparison table** — the DRHP's own "Comparison with Listed
   Peers" set (anchored/cited to its DRHP section), with P/E, P/B, EV/EBITDA, ROE
   sourced from market data, shown alongside the IPO's own DRHP-derived metrics.
2. **Read-only GMP display** — a clearly-caveated grey-market-premium value from
   public aggregators, computationally isolated from any model feature pipeline.
3. **Indian-context formatting + glossary** — lakh/crore + ₹ everywhere, with
   hoverable glossary tooltips on Indian-IPO vocabulary.
4. **Historical IPO dataset (backend, not yet user-visible)** — a survivorship-
   corrected ~800–1000 mainboard-IPO dataset (2014–present) with an explicit
   `status` column, SEBI-issuer-side sourced, sanity-checked against the ~7%
   median listing-day baseline. Foundation for Phase 5.

**Out of scope (later phases):** the forecaster itself (Phase 5); GMP-vs-model gap
signal (Phase 5, GMP-03); RAGAS/DeepEval eval dashboards + inline metric surfacing
(Phase 6). Cross-IPO peer comparison across multiple IPOs (v2).
</domain>

<decisions>
## Implementation Decisions

### GMP display (GMP-01, GMP-02)
- **D4-01:** GMP is sourced from **2–3 public aggregators and their spread/
  disagreement is shown explicitly**. The divergence IS the honesty signal — it
  visibly demonstrates GMP is unofficial and unreliable, rather than presenting a
  single authoritative-looking number. (Scraping surface acknowledged — P16.)
- **D4-02:** GMP is **de-emphasized**: rendered low on the page, collapsed behind
  a **"What is GMP? Why we don't trust it"** disclosure, with a persistent short
  caveat about provenance/reliability. No red/green, never framed as a signal (P21).
- **D4-03:** **GMP-02 isolation is a hard invariant.** The GMP value is
  display-only and computationally isolated — it MUST NOT enter any model/feature
  pipeline. Enforced by a module boundary (read-only scrape → cache → render);
  Phase 5 owns the leakage-audit test that pins it. Downstream planner must keep
  GMP out of anything the forecaster can import.

### Peer comparison (PEER-01, PEER-02)
- **D4-04:** The peer **SET** is anchored to the DRHP's own "Comparison with Listed
  Peers" section (PEER-01), citing the DRHP source (reuse the Phase 1/2 citation-
  chip / source-anchor pattern). Never a self-selected peer set when the DRHP
  provides one.
- **D4-05:** Peer **MULTIPLES** (P/E, P/B, EV/EBITDA, ROE): when a DRHP-named peer
  is missing a multiple from the primary source, **backfill from an alternate
  source and flag provenance PER CELL** (which source each value came from).
  Completeness with honest sourcing — never a silent gap, never a fabricated
  number. Source-priority order is a research item (candidates: screener.in →
  yfinance `.NS`/`.BO` → NSE/BSE → IR page), respecting P15 (yfinance quality) and
  P16 (screener ToS/rate limits).
- **D4-06:** When the DRHP discloses **NO** listed-peer comparison, render an
  **honest empty-state** ("This DRHP disclosed no listed-peer comparison") — never
  fabricate a peer set. Mirrors the Phase 3 not-disclosed honesty pattern (D3-03).
  A labeled sector-peer fallback was considered and **deferred** (not the default).

### Indian formatting & glossary (UI-04)
- **D4-07:** All rupee amounts render with **₹ + Indian digit grouping (1,23,456)
  and auto-scaled lakh↔crore by magnitude** (e.g. ₹12.5 lakh, ₹1,247 crore), with
  `tabular-nums` for alignment. Extends the Phase 2 issue-size lakh/crore to
  app-wide, as a single shared formatting utility.
- **D4-08:** Glossary tooltips cover the **core Indian-IPO vocabulary**: RPT, QIB,
  NII, RII (UI-04) **plus** GMP, OFS, DRHP, anchor investor — the terms a retail
  user actually hits on these pages. (Financial-ratio definitions P/E, P/B,
  EV/EBITDA, ROE considered; deferred unless trivial to add in the peer table.)

### Honesty invariant (carried forward)
- **D4-09:** **No red/green coding, no badges** anywhere in the peer table or GMP
  display (D2-07 carries forward). A "cheap vs expensive" peer multiple or a "high"
  GMP is shown via factual numbers only — never a color-coded verdict.

### Claude's Discretion
- **Peer multiples live-vs-cached** — the user deferred this. Research to propose:
  fetch-on-load vs precompute into a cached record (like snapshots/redflag), and
  current market multiples vs point-in-time-of-DRHP. Bias: the project's cache-first
  pattern + P16 rate limits favor precompute-into-cache, scraping at precompute
  time not request time; reconcile with the goal's word "live."
- **Number-format edge cases** (negatives, missing → em-dash, sub-lakh amounts) —
  Claude's discretion following the Phase 2/3 rendering conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 4: Historical IPO Dataset + Peer Comparator + GMP Display" — goal, 5 success criteria, requirements (PEER-01, PEER-02, GMP-01, GMP-02, UI-04), pitfalls owned (P3 survivorship, P15 yfinance quality, P16 screener ToS, P14 brittle ingestion), and the `jugaad-data` validation-spike research flag.
- `.planning/REQUIREMENTS.md` — full text of PEER-01, PEER-02, GMP-01, GMP-02, UI-04.
- `.planning/PROJECT.md` — free/public-data-only constraint, SEBI RIA "informational/educational, not advice" compliance framing, honesty-first product framing.

### Data sources & stack (India-specific)
- `CLAUDE.md` (repo root) §"India-Specific Data-Source Notes" — screener.in, yfinance `.NS`/`.BO`, jugaad-data, chittorgarh, NSE/BSE caveats; §"What NOT to Use" (nsepy is dead — use jugaad-data); §"Supporting Libraries" (yfinance, jugaad-data, requests-cache, beautifulsoup4).

### Carried-forward decisions & patterns
- `.planning/phases/02-multi-ipo-catalogue-drhp-snapshot-surface/02-CONTEXT.md` — D2-07 (honesty invariant: no red/green, no badges), catalogue/`drhp_id`-FK pattern, Phase 2 issue-size lakh/crore (extend here), UI-04 explicitly deferred to Phase 4.
- `.planning/phases/03-structured-signal-extraction-red-flag-table/03-CONTEXT.md` — D3-03 (not-disclosed honesty pattern — mirrored for the no-peers empty-state); D3-17 (cheap/cached, no live-per-request calls) informing the peer/GMP cache-first bias.

### Deferred-ingest coupling
- `data/swiggy_drhp/INGEST_LATER.md` / `data/INGEST_ALL_LATER.md` (if present) — the live Qdrant ingest is deferred; the historical dataset build + peer/GMP scraping are separable from DRHP-RAG ingest, but note the coupling for anything that needs a DRHP's peer *section* parsed.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data/catalogue_loader.py` — `load_catalogue()` + `is_known_drhp_id()` allow-list; the peer/GMP pages must reuse the same `drhp_id` allow-list guard before any cache read (T-02-V5).
- `data/catalogue.json` — the 8 curated IPOs; peer/GMP records key off the same `drhp_id`.
- `pipelines/snapshot.py`, `pipelines/redflag.py` — the **precompute → write `data/<kind>/<drhp_id>.json` → `load_*()`** cache pattern to MIRROR for new peer + GMP cached records (e.g. `data/peers/`, `data/gmp/`).
- `ui/chip.py`, `ui/expander.py` — citation chips + source expanders; reuse to anchor the DRHP peer SET back to its DRHP section (PEER-01).
- `ui/snapshot_blocks.py`, `pages/02_snapshot.py` — block renderers + the locked snapshot-page IA; the peer table + GMP block slot in here. **Note the Phase 3 lesson:** wrap card containers with `st.container(border=True)`, never a split `<div>` across two `st.markdown` calls (that renders an empty white bar).
- `ui/copy.py` + `compliance.scrubber` — all new user-facing copy (glossary text, GMP caveats, empty-states) lands in `ui/copy.py` under the import-time banned-token scrubber assertion.
- `app/static/drhplens.css` — the SINGLE CSS source; new peer-table / GMP / tooltip classes go here (monochrome, no new color, no red/green).

### Established Patterns
- `drhp_id` FK threads every surface; cache-first render (no live LLM/scrape on page render — scraping happens at precompute time).
- Honesty-first invariant (no red/green, no badges) is load-bearing across the app.
- Indian issue-size lakh/crore already exists (Phase 2) — generalize into one shared `format_inr` utility rather than re-implementing per surface.

### Integration Points
- New peer + GMP blocks insert into `pages/02_snapshot.py` in the locked IA order.
- New cached-record kinds under `data/` mirror `data/snapshots/` and `data/redflag/`.
- The historical dataset is a committed repo artifact (CSV/parquet under `data/`), consumed later by Phase 5 — not wired into the Streamlit page in this phase.

</code_context>

<specifics>
## Specific Ideas

- GMP disclosure copy should carry a genuine "why we don't trust it" explanation
  (unofficial, unregulated, manipulable, no provenance guarantee) — not a boilerplate
  disclaimer. The spread across aggregators should be the visual proof of that claim.
- The peer-table provenance flags should be lightweight (a small per-cell source
  marker + a legend), not a heavy footnote apparatus.

</specifics>

<deferred>
## Deferred Ideas

- **Peer multiples live-vs-cached + point-in-time-vs-current** — deferred to
  research/planning (see Claude's Discretion).
- **Historical dataset internals** — return-target definition (listing-day close),
  `status` taxonomy (withdrawn / listed_alive / delisted / merged / name_changed),
  SEBI-issuer-side sourcing, replace-with-NaN survivorship handling, ~7% median
  sanity-check + methodology-page divergence flag. P3 territory; researcher/planner
  to specify. In-scope for the phase, just not user-decided here.
- **Tooltip interaction (hover desktop vs tap mobile) + tooltip mechanism** — the
  UI-SPEC's job (this phase has a UI gate; run `/gsd-ui-phase 4`).
- **`jugaad-data` endpoint-validation spike** at phase start (ROADMAP research flag)
  before committing it as the primary NSE source; add a nightly integration test.
- **Labeled sector-peer fallback** when the DRHP names no peers — considered,
  deferred; honest empty-state is the default (D4-06). Revisit only if users need it.
- **Financial-ratio glossary tooltips** (P/E, P/B, EV/EBITDA, ROE) — considered in
  UI-04 scope; add only if it doesn't clutter the peer table.

</deferred>

---

*Phase: 4-Historical IPO Dataset + Peer Comparator + GMP Display*
*Context gathered: 2026-07-06*
