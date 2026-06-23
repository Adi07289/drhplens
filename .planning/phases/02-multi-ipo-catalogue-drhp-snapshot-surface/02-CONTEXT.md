# Phase 2: Multi-IPO Catalogue + DRHP Snapshot Surface - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

A retail user can browse a catalogue of recent Indian mainboard IPOs, pick any one, and see a per-IPO **snapshot page** that surfaces the core DRHP signals — metadata, plain-English business summary, key financials, prioritized risks, use-of-proceeds, promoter section — each field citing its DRHP source. Builds directly on Phase 1's ingestion + citation + LangGraph infrastructure, extending the single-IPO assumption to many via the `drhp_id` FK that Phase 1 already threads everywhere.

**In scope:** Multi-IPO catalogue browser (list/grid of IPO cards → snapshot page); per-IPO snapshot with 6 field blocks (metadata, business summary, financials, risks, use-of-proceeds, promoter), all DRHP-cited; ingestion extended from 1 IPO to ~8; offline snapshot pre-computation; reuse of Phase 1 citation chips + disclaimer surfaces + agent.

**Out of scope (later phases):** Red-flag extraction table (Phase 3); methodology pane (Phase 3, METHOD-01); peer comparison (Phase 4); GMP display (Phase 4); forecaster (Phase 5); full Indian-context formatting UI-04 (Phase 4 — but issue-size lakh/crore already used). Cross-IPO comparison (v2). Q&A chat is already shipped in Phase 1 — Phase 2 adds the snapshot surface alongside it.

</domain>

<decisions>
## Implementation Decisions

### IPO Catalogue (locked via discuss)
- **D2-01:** Curate ~8 recent recognizable mainboard IPOs: **Swiggy** (already ingested, Phase 1), plus a verified subset of **Hyundai Motor India, Ola Electric, Zomato, Nykaa, Paytm, LIC, Mamaearth**. Planner/executor MUST verify each has a publicly downloadable DRHP on SEBI/BSE/NSE before committing it to the catalogue; substitute a comparable recognizable IPO if a DRHP is unavailable. Mix of winners (Zomato, Hyundai) and disappointments (Paytm, LIC, Ola) deliberately chosen so the honest-analysis angle lands.
- **D2-02:** Each catalogue IPO requires: DRHP PDF + SHA-256 pin (same pattern as Swiggy), offline ingestion into the same Qdrant collection (drhp_id discriminator), and offline snapshot pre-computation.

### Snapshot Computation (Claude's discretion → locked)
- **D2-03:** Snapshot fields are **pre-computed offline** at ingestion time (matches Phase 1's offline-ingest pattern; avoids HF Spaces cold-start cost of computing 6 LLM extractions per page view). Each snapshot field is computed once, cached to a relational/JSON store keyed by drhp_id, and rendered on demand. Re-uses the Phase 1 `GroundedAnswer`/`Claim` schema so every snapshot field carries `claim_id` citations.
- **D2-04:** Snapshot extraction reuses the Phase 1 retrieval + generate + cite_check pipeline (not a new LLM path). Each field block is a targeted query against that IPO's chunks ("summarize the business model", "extract the use of proceeds", etc.), run through the same grounding + cite-check guarantees. The banned-token scrubber applies to all snapshot copy.

### Snapshot Field Blocks (SNAP-02..07)
- **D2-05:** Six cited field blocks per IPO: (1) metadata header — price band, lot size, dates, issue size, fresh-issue vs OFS split, lead managers (SNAP-02); (2) plain-English business-model summary (SNAP-03); (3) key financials snapshot — 3-5 yr revenue/profit/margins/debt/ROE/ROCE (SNAP-04); (4) prioritized risk-factors summary, each cluster citing original DRHP risk text (SNAP-05); (5) use-of-proceeds breakdown with OFS-vs-fresh % visually foregrounded (SNAP-06); (6) promoter/management section — names, pre/post holdings, pledging, prior matters (SNAP-07).
- **D2-06:** The **OFS-vs-fresh-issue split is visually foregrounded** in use-of-proceeds (matches Indian retail's primary "promoter cash-out vs growth capital" mental model — promoter cashing out = signal). Per ROADMAP success criterion 5.

### Catalogue + Snapshot UI
- **D2-07:** Catalogue = browseable grid/list of IPO cards (issuer name, sector, listing date, issue size) → click → snapshot page. Reuse Phase 1's design system (slate-indigo accent, 4-size type scale, citation chips, disclaimer surfaces). No green/red coding (a "successful" vs "disappointing" IPO is shown via factual data, never red/green badges — honesty-first invariant carries forward).
- **D2-08:** Snapshot page renders the Q&A chat (Phase 1) alongside or below the 6 field blocks — same IPO context. The user can read the snapshot AND ask follow-up questions about the same DRHP.

### Claude's Discretion (planner resolves)
- Exact catalogue IPO final list (after DRHP-availability verification)
- Snapshot field block layout (cards vs accordion vs sections) — defer to UI-SPEC
- Relational store choice for cached snapshots (SQLite vs JSON files committed to repo) — SQLite preferred for query, JSON acceptable for simplicity
- Whether the catalogue metadata is hand-curated JSON or scraped (hand-curated is fine for ~8 IPOs in v1)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing Phase 2.**

### Project context
- `.planning/PROJECT.md` — core value, constraints, audience
- `.planning/REQUIREMENTS.md` — Phase 2 covers SNAP-01..07 + OPS-01
- `.planning/ROADMAP.md` — Phase 2 goal + 5 success criteria + pitfalls owned (P14 brittle DRHP ingestion, P13 embedding mismatch on Indian-English)
- `.planning/STATE.md` — accumulated context + Phase 1 outcomes

### Phase 1 foundations (REUSE — do not rebuild)
- `agent/schemas.py` — GroundedAnswer / Claim / RetrievedChunkRef contract (snapshot fields reuse this; do NOT rename fields — Phase 3 METHOD-01 depends on it)
- `agent/graph.py` + `agent/nodes/*.py` — the retrieval + generate + cite_check pipeline snapshot extraction reuses
- `storage/vector.py` — Qdrant client; `drhp_id` discriminator already supports multi-IPO
- `pipelines/ingest_swiggy.py` — the ingestion pattern to generalize from 1 IPO to N (rename/generalize to `pipelines/ingest.py` taking a drhp_id + PDF path)
- `compliance/scrubber.py` + `compliance/disclaimer_text.py` — banned-token + disclaimer surfaces (apply to all snapshot copy)
- `ui/chip.py` + `ui/expander.py` + `ui/disclaimer.py` — citation rendering (reuse for snapshot field citations)
- `app.py` + `pages/01_methodology.py` — Streamlit multipage pattern (add catalogue + snapshot pages)
- `.planning/phases/01-foundation-mvp-a-cited-q-a-on-one-ipo/01-UI-SPEC.md` — Phase 1 design system (extend, don't restyle)
- `.planning/phases/01-foundation-mvp-a-cited-q-a-on-one-ipo/01-RESEARCH.md` — Docling parsing recipe + chunking strategy (reuse for new IPOs)
- `.planning/phases/01-foundation-mvp-a-cited-q-a-on-one-ipo/01-PHASE-CLOSE.md` — what Phase 1 actually delivered
- `.planning/research/PITFALLS.md` — P13, P14 (Phase 2 owned)
- `TODOS.md` — E5 user-upload note (Phase 2 ingestion generalization should keep E5 unblocked)
- `HANDOFF.md` — full project state

### External
- SEBI / BSE / NSE DRHP archives — source for the ~8 catalogue DRHPs
- Docling docs — parser (note: Phase 1 used PyMuPDF fallback on Python 3.13; Python 3.11 now enables real Docling)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (Phase 1 — REUSE heavily)
- **Ingestion pipeline** (`pipelines/ingest_swiggy.py`) → generalize to `pipelines/ingest.py(drhp_id, pdf_path)`. The parser + chunker + embedder + upsert all already work; just parameterize the drhp_id.
- **Citation infrastructure** (`agent/schemas.py`, `ui/chip.py`, `ui/expander.py`) → snapshot field blocks render exactly like Q&A answers: cited prose with `[1]` chips.
- **The agent** (`agent/graph.py`) → snapshot extraction = 6 targeted queries through the same grounded pipeline. No new LLM path.
- **Disclaimer + scrubber** → apply unchanged to all snapshot copy.
- **Design system** (Phase 1 UI-SPEC) → catalogue + snapshot pages inherit the palette, type scale, spacing, citation chip CSS.

### Established Patterns (carry forward)
- `drhp_id` FK everywhere — already multi-IPO ready (Phase 1 designed for this per TODOS E5).
- Offline pre-compute (ingest + now snapshot) vs on-demand (Q&A) — the storage-bus split.
- Walking-skeleton-first: ship a 2-IPO catalogue + 1 snapshot page early, then add IPOs + field blocks.
- Atomic per-task commits; pytest unit tests flip from stub to green per wave.

### Integration Points
- New catalogue page + snapshot page added to the Streamlit multipage app (`pages/`).
- Snapshot cache store (new) read by the snapshot page, written by the offline pipeline.
- Same Qdrant collection, new drhp_ids.

</code_context>

<specifics>
## Specific Ideas

- Catalogue cards show factual data only (issuer, sector, listing date, issue size) — no performance badges, no green/red.
- OFS-vs-fresh % gets a foregrounded visual (e.g., a labeled split bar) — the "is the promoter cashing out?" signal.
- Snapshot page co-locates the Phase 1 Q&A chat so the user can drill in after reading the summary.
- Each catalogue IPO is a deliberate mix: clear winners (Zomato, Hyundai) + notable disappointments (Paytm, LIC, Ola) — makes the honest-analysis value visible.

</specifics>

<deferred>
## Deferred Ideas

- Cross-IPO side-by-side comparison — v2 (MULTI-IPO-COMPARE-01 / E3 in TODOS).
- Red-flag extraction table — Phase 3 (EXTRACT-01..03).
- Peer multiples / GMP — Phase 4.
- Full Indian-context formatting (lakh/crore everywhere, RPT/QIB/NII/RII tooltips) — Phase 4 (UI-04); Phase 2 only does issue-size lakh/crore.
- Automated DRHP ingestion from SEBI feeds — v2 (AUTO-INGEST-01).
- User-uploadable DRHP — v2 (E5); Phase 2's ingestion generalization keeps this unblocked.

</deferred>

---

*Phase: 2-Multi-IPO Catalogue + DRHP Snapshot Surface*
*Context gathered: 2026-05-28*
