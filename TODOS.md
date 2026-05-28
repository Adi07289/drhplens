# TODOS — DRHPLens

Deferred items from the CEO review on 2026-05-28. Each entry: **What** / **Why** / **Pros** / **Cons** / **Context** / **Effort** / **Priority** / **Depends on**.

Plan-file source: `/Users/adityasharma/.claude/plans/mighty-noodling-pretzel.md` (CEO review run on greenfield roadmap before commit).

---

## E5 — User-uploadable DRHP path

- **What:** Allow users to upload any mainboard DRHP PDF for analysis, not just the curated catalogue.
- **Why:** Turns DRHPLens from a museum (curated IPOs only) into a tool (any IPO). Always-on demo value, broader real-world usefulness.
- **Pros:**
  - Live demo never goes stale between IPO subscription windows.
  - "Any IPO, any time" pitch lands harder with recruiters and users.
  - Natural bridge to the v2 SaaS direction.
- **Cons:**
  - Parser fragility on weird/old DRHP layouts can break live demos.
  - Compliance surface expands (any uploaded prospectus, including possibly-restricted content).
  - HF Spaces free-tier compute strained by on-demand indexing of long PDFs.
- **Context:** Considered as cherry-pick E5 in the CEO review on 2026-05-28; deferred because the curated 5-10 IPO MVP is enough for v1 demo polish and ships faster. v2 SaaS evolution (Portfolio Red-Flag Radar trajectory) naturally pulls this in.
- **Threat model required before pickup:**
  - PDF parser exploit class (Docling / Pillow / PyMuPDF CVE history)
  - Upload size cap (suggest 25 MB; typical DRHP is 5-12 MB)
  - Rate limiting per IP / session (suggest 5 uploads / day on the free tier)
  - Optional SEBI-archive URL whitelist (accept SEBI / BSE / NSE URLs only, not arbitrary uploads)
  - Abusive-upload runbook (DOS-via-large-upload, malformed PDFs, embedded JS, decompression bombs)
  - Storage policy (uploaded DRHPs purged after N days, never folded into the shared corpus)
- **Effort estimate:** M (human ~2 days; CC ~3-5 hrs) + ~half-day threat model
- **Priority:** P2 (v1.x or v2 candidate)
- **Depends on:** v1 ingestion pipeline (INGEST-01/02/03) production-ready; rate-limit middleware; threat-model approval

---

## E7 — Pre-listing vs actual retrospective pages

- **What:** Per-covered-IPO retrospective page showing the pre-listing model forecast next to the actual listing-day outcome ("we predicted [range] on T-1; actual was [X]") with a calibration delta.
- **Why:** Accumulates honest calibration evidence visibly over time; honesty-first signal that compounds with every covered IPO that lists.
- **Pros:**
  - Builds trust visibly across many IPOs.
  - Strong material for the model card and ongoing eval review.
  - Demonstrates calibration improving (or honestly not improving) on real IPOs.
- **Cons:**
  - Day-1 value is zero — no covered IPOs have listed yet.
  - The data accumulates naturally in the eval pipeline anyway, so the page is mostly a render layer over already-captured data.
- **Context:** Considered as cherry-pick E7 in the CEO review on 2026-05-28; deferred because the data isn't there yet. Pull in once 2-3 Phase 2 catalogue IPOs have actually listed.
- **Effort estimate:** S (human ~3 hrs; CC ~1-2 hrs)
- **Priority:** P2 (v1.x, post-first-listings)
- **Depends on:** Phase 2 IPO catalogue shipped; ≥2 catalogue IPOs have listed; their actual listing-day outcomes captured

---

## E4 — Hindi mode (UI + Q&A localization)

- **What:** Hindi UI + Hindi-language Q&A with an eval pass verifying RAG faithfulness holds in Hindi.
- **Why:** Indian retail = Hindi-first majority. Massive audience expansion plus multilingual eval is a real DS-portfolio differentiator.
- **Pros:**
  - Major audience expansion across Hindi-speaking retail.
  - Multilingual RAG eval is a strong, somewhat-rare DS signal.
  - Bridges to a v2 SaaS regional-language tier.
- **Cons:**
  - Hindi RAG-faithfulness eval is a sub-project on its own (needs gold set, glossary, reviewer).
  - Mediocre machine-translated UI degrades trust if quality is mixed.
  - Adds eval surface that competes with the Phase 5/6 forecasting/eval priorities.
- **Context:** Considered as cherry-pick E4 in the CEO review on 2026-05-28; deferred to v2 trajectory. v1 ships English-only (Indian English is widely accepted for finance topics).
- **Effort estimate:** M (human ~3-5 days; CC ~3-5 hrs UI + ~2-3 hrs eval setup)
- **Priority:** P3 (v2 SaaS feature)
- **Depends on:** v1 English version solid; Hindi RAG-faithfulness gold eval set hand-curated; machine-translation review pipeline

---

## E3 — Compare two open IPOs side by side

- **What:** When two IPOs are open simultaneously (frequent in India), surface them side by side with signal tables, peer multiples, forecast ranges, and the GMP-vs-model gap.
- **Why:** Captures the actual decision moment — Indian IPO windows often overlap 2-3 issues, and retail investors are deciding between them.
- **Pros:**
  - Highly useful at the decision moment for retail investors.
  - Demonstrates the agent's multi-IPO reasoning capability.
  - Natural v2 SaaS feature.
- **Cons:**
  - Only shines during multi-IPO windows.
  - Single-IPO surface needs to be solid before stacking comparisons on it.
  - Already tracked as v2 `MULTI-IPO-COMPARE-01` in REQUIREMENTS.md.
- **Context:** Considered as cherry-pick E3 in the CEO review on 2026-05-28; deferred. Already tracked as v2 requirement `MULTI-IPO-COMPARE-01` in `.planning/REQUIREMENTS.md`. This TODOS entry exists for traceability of the CEO-review decision.
- **Effort estimate:** M (human ~3 days; CC ~2-4 hrs)
- **Priority:** P3 (v2 SaaS feature, already in REQUIREMENTS.md v2)
- **Depends on:** v1 single-IPO surface solid (Phases 1-6 complete); historical IPO dataset robust enough to handle simultaneous-IPO queries

---

*Created: 2026-05-28 from CEO review (`/plan-ceo-review`).*
*Plan file: `/Users/adityasharma/.claude/plans/mighty-noodling-pretzel.md`.*
