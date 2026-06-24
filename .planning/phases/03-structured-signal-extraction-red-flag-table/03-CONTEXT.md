# Phase 3: Structured Signal Extraction (Red-Flag Table) - Context

**Gathered:** 2026-06-25
**Status:** Ready for planning

<domain>
## Phase Boundary

A retail user opening any covered IPO sees a **structured red-flag signal table** — RPT % of revenue, OFS vs fresh-issue %, promoter pledge %, customer concentration, auditor history, debt trajectory, going-concern mentions — each field carrying a **visible extractor-confidence score**. The extractors are evaluated against a **hand-labeled gold set** (per-field F1, committed to the repo), a **numeric-faithfulness eval track** enforces a **≥0.95 release gate** that physically refuses deploy below threshold, risk extraction is **bucketed by IDF specificity** (issuer-specific foregrounded over boilerplate), and a **"show your work" methodology pane** (METHOD-01) is wired onto Q&A answers and the red-flag table.

Builds directly on shipped Phase 1/2 infrastructure: the `GroundedAnswer`/`Claim`/`claim_id` citation contract, the offline pre-compute → cache-by-`drhp_id` pattern, the non-LLM `cite_check` node, citation chips, the banned-token scrubber, and the existing eval scaffold (`scripts/run_eval.py`, `tests/eval/gold/`, `eval/reports/`).

**In scope:** 7-field red-flag extraction table per IPO (EXTRACT-01); per-field confidence scoring + UI (EXTRACT-02); hand-labeled extraction gold set + per-field F1, committed (EXTRACT-03); numeric-faithfulness eval track + ≥0.95 deploy gate (EVAL-03); IDF issuer-specific vs boilerplate risk bucketing (P12 mitigation); methodology pane on Q&A + red-flag surfaces (METHOD-01).

**Out of scope (later phases):** peer multiples comparison + GMP display (Phase 4); historical IPO dataset + forecaster (Phase 5); full eval harness, RAGAS faithfulness ≥0.95 general gate, failure gallery, agentic polish, portfolio surface (Phase 6); cross-IPO comparison (v2). Live multi-IPO ingest remains a Phase 2 carry-over dependency (see `data/INGEST_ALL_LATER.md`) — Phase 3 right-sizes the gold set to whatever is actually ingested rather than forcing full ingest here.

</domain>

<decisions>
## Implementation Decisions

### Confidence Scoring (EXTRACT-02)
- **D3-01:** Confidence is **derived by a source-grounding rubric** (deterministic, no extra LLM cost): **high** = value stated verbatim in the cited DRHP span; **medium** = stated but needs light parsing/aggregation; **low** = inferred across sections. Anchors confidence to the existing `claim_id`/citation contract, and is defensible in an interview.
- **D3-02:** UI shows **high/med/low label up front + the numeric score revealed on expand** (in the methodology pane). No color judgment — the carried-forward "no green/red coding" invariant applies to confidence too.
- **D3-03:** When a field is **not disclosed** in the DRHP (customer concentration, promoter pledge, etc. are frequently absent), render an explicit **"Not disclosed in DRHP"** by reusing the existing `RefusalResponse` path. Absence is itself an honest signal a retail user should see — never a hidden row, never conflated with low-confidence extraction.
- **D3-04:** The F1 eval **reports accuracy/F1 split by confidence bucket** (high/med/low) — a confidence-reliability check. Confidence becomes a *measured* claim, not decoration; directly counters evaluation theater (P10).

### Gold Set + F1 Design (EXTRACT-03)
- **D3-05:** Gold set is **right-sized to the ingested DRHP set with honest n** (label the catalogue IPOs as they go live), reporting per-field F1 with the true n and **documenting 20-30 as the committed target**. Honesty-first; does not fake the ROADMAP number, and unblocks Phase 3 without waiting on full Phase 2 ingest. (Coupling note: F1 requires the extractor to *run* on each labeled DRHP, which requires that DRHP be ingested.)
- **D3-06:** **All 7 red-flag fields are labeled** (RPT %, OFS/fresh %, promoter pledge %, customer concentration, auditor history, debt trajectory, going-concern). The whole table's credibility rests on it, and the numeric + categorical mix makes a richer F1 story.
- **D3-07:** **Per-field-type match rules** define F1: numeric fields match **within a tolerance** (e.g. ± disclosed rounding); boolean fields (going-concern) match **exactly**; list/set fields (customer concentration, auditor history) score by **set overlap** (precision/recall on items). Most defensible; eval on issuer-specific/value-correct matches avoids the P12 boilerplate-recall trap.
- **D3-08:** A **written labeling protocol/rubric is committed alongside the labels** (field definitions, where in the DRHP to look, edge-case rules, single-labeler note). Cheap, and exactly what a DS reviewer looks for.
- **D3-09:** Gold-set labels live at **`eval/gold/extraction_labels.jsonl`** (per ROADMAP success criterion 3); the labeling rubric is committed next to it.

### Numeric-Faithfulness Gate (EVAL-03)
- **D3-10:** A numeric-faithfulness **failure** = a number emitted that **traces to no cited DRHP span** (per-number source-grounding). Implemented by **extending the existing non-LLM `cite_check` node to numerics** — deterministic, no LLM-judge variance, fully defensible as a hard gate.
- **D3-11:** The eval set is a **hand-curated ~50 numeric-only questions** across the ingested IPOs, each with a gold numeric answer + source page. Deterministic ground truth; strongest portfolio artifact.
- **D3-12:** The **≥0.95 gate is enforced by a pre-deploy script / `make release`-style target** that runs the numeric eval against live services, **refuses to proceed and writes the report if <0.95**. Fits the solo HF-Spaces git-push deploy model without CI secrets/API cost. Add a **tiny offline CI smoke test** on a fixture so the gate logic itself is unit-tested.
- **D3-13:** The gate covers **all numeric-emitting surfaces** — Q&A answers + snapshot numeric fields + red-flag table numbers — since any of them can hallucinate a number.

### IDF Risk Bucketing (P12 mitigation, reinforces EXTRACT-01)
- **D3-14:** Issuer-specific vs boilerplate is computed via **in-corpus IDF over the ingested DRHP risk sections (n≈8, documented as small) PLUS a hand-curated boilerplate-phrase list as a deterministic floor**. Honest about small-n, robust now, sharpens automatically as the catalogue grows.
- **D3-15:** Display is a **single ranked risk list ordered by IDF specificity, each item showing a neutral specificity indicator** (issuer-specific foregrounded by rank). Satisfies ROADMAP success criterion 5 ("issuer-specific risks foregrounded") while keeping more transparency than a hard collapsed bucket; respects no-red/green.

### Methodology Pane (METHOD-01, CEO cherry-pick E1)
- **D3-16:** The "show your work" pane is wired on **Q&A answers + the red-flag table** (the Phase 3 headline surfaces); reuse on snapshot fields if cheap. Delivers "visible from Phase 3's first demoable surface" without over-building across already-shipped Phase 2 surfaces.
- **D3-17:** Pane content is sourced **cheaply, not via live per-expand LLM calls**: query / retrieved chunks + scores / prompt / sources shown **per claim from cached `claim_id` data**; faithfulness/citation **eval scores shown from the latest committed eval report at answer/field level** (not recomputed on each expansion). Fast, cheap, honest.

### Claude's Discretion (planner resolves)
- Exact red-flag table layout (cards vs table vs accordion) — defer to UI-SPEC; must honor no-red/green + confidence label placement (D3-02).
- Whether extraction reuses the Phase 2 snapshot LLM path (targeted query → grounded + cite_check pipeline) or a dedicated structured-extraction prompt path — strong default: reuse the grounded pipeline so every field carries `claim_id` citations (consistent with D2-04).
- Exact numeric tolerance per field, IDF threshold for "issuer-specific", and the boilerplate-phrase floor list contents — tune empirically, document the procedure.
- Where the ingest-for-gold-set step runs (extend `pipelines/ingest.py` loop vs a standalone eval-prep script).
- `make release` / pre-deploy script's exact name, location, and report-writing format.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing Phase 3.**

### Project context
- `.planning/PROJECT.md` — core value, constraints, audience, DS-depth requirement
- `.planning/REQUIREMENTS.md` — Phase 3 covers EXTRACT-01, EXTRACT-02, EXTRACT-03, EVAL-03, METHOD-01
- `.planning/ROADMAP.md` — Phase 3 goal + 6 success criteria + pitfalls owned (P2, P12, P10)
- `.planning/STATE.md` — accumulated context, cross-cutting invariants, Phase 1/2 outcomes

### Cross-cutting invariants (MUST respect)
- `.planning/research/PITFALLS.md` — **P2** (hallucinated numbers → two-stage structured extraction + numeric faithfulness ≥0.95), **P12** §"Risk-Factor Boilerplate Inflates Extraction Metrics" (IDF weighting + issuer-specific/boilerplate split + eval on specific-only), **P10** (evaluation theater → every metric needs an interpretation paragraph + failure gallery)
- `.planning/research/SUMMARY.md` — research synthesis (stack + architecture decisions)

### Phase 1/2 foundations (REUSE — do not rebuild or rename)
- `agent/schemas.py` — `GroundedAnswer` / `Claim` / `RetrievedChunkRef` / `RefusalResponse` contract. Red-flag fields + methodology pane depend on the **locked `claim_id` shape** (`^c_[a-z0-9]{6,16}$`, SKELETON §B). Do NOT rename fields.
- `agent/snapshot_schema.py` — `SnapshotRecord` cache pattern (per-`drhp_id` JSON; field = `GroundedAnswer` | `RefusalResponse`). Red-flag table follows the same offline-precompute → cache shape.
- `agent/graph.py` + `agent/nodes/*.py` — retrieval → rerank → generate → **`cite_check`** → emit pipeline. Extension point for D3-10 (numeric grounding lives in/next to `cite_check.py`).
- `agent/nodes/cite_check.py` — the non-LLM cite-check node; extend to per-number source-grounding (D3-10).
- `pipelines/snapshot.py` + `pipelines/snapshot_queries.py` — offline per-IPO field computation pattern to mirror for red-flag extraction.
- `pipelines/ingest.py` — parameterized `(drhp_id, pdf_path)` ingest; gold-set-for-F1 needs DRHPs ingested through this.
- `data/catalogue.json` + `data/catalogue_loader.py` — the ~8 covered IPOs + allow-list; the in-corpus IDF corpus and gold-set scope derive from here.
- `compliance/scrubber.py` + `compliance/banned_tokens.py` + `compliance/disclaimer_text.py` — banned-token scrubber applies to all red-flag/methodology copy.
- `ui/chip.py` + `ui/expander.py` + `ui/snapshot_blocks.py` + `ui/snapshot_chat.py` — citation + expandable rendering to reuse for the red-flag table and methodology pane.
- `pages/01_methodology.py` + `pages/02_snapshot.py` — Streamlit multipage surfaces the pane/table attach to.
- `scripts/run_eval.py` — existing eval harness (citation accuracy + coverage + RAGAS faithfulness + recall@5; live Qdrant + Gemini). The numeric-faithfulness track + ≥0.95 gate extend this; `eval/reports/` is the report sink.
- `tests/eval/gold/` + `tests/eval/gold_set.jsonl` — existing gold-set pattern to follow for `eval/gold/extraction_labels.jsonl` and the 50-query numeric set.
- `.planning/phases/01-foundation-mvp-a-cited-q-a-on-one-ipo/01-CONTEXT.md` — citation/refusal/disclaimer decisions (D-01..D-09) carried forward
- `.planning/phases/02-multi-ipo-catalogue-drhp-snapshot-surface/02-CONTEXT.md` — snapshot precompute/cache + no-red/green + OFS-vs-fresh foregrounding decisions

### Data dependencies
- `data/INGEST_ALL_LATER.md` — deferred live multi-IPO ingest; gold-set n is bounded by what this unblocks (D3-05)
- `eval/gold/extraction_labels.jsonl` — **to be created** (ROADMAP success criterion 3): committed hand-labels + labeling rubric

### External
- SEBI / BSE / NSE DRHP archives — source for labeling the 7 fields per IPO

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Grounded pipeline** (`agent/graph.py` + nodes): red-flag extraction = targeted queries through the existing retrieval → generate → cite_check path, so every field carries `claim_id` citations (mirrors Phase 2 D2-04). No new LLM path needed.
- **`cite_check.py`**: the natural home to extend for D3-10 per-number source-grounding — it already validates claims against retrieved evidence; numbers become a stricter sub-check.
- **`SnapshotRecord` / snapshot precompute** (`agent/snapshot_schema.py`, `pipelines/snapshot.py`): offline-compute → cache-by-`drhp_id` pattern to mirror for the red-flag table.
- **`RefusalResponse`**: directly powers D3-03 "Not disclosed in DRHP".
- **Eval scaffold** (`scripts/run_eval.py`, `tests/eval/gold/`, `eval/reports/`): numeric-faithfulness track and per-field F1 extend this rather than starting fresh.
- **Citation/expander UI** (`ui/chip.py`, `ui/expander.py`): the methodology pane and confidence-on-expand reuse these.

### Established Patterns (carry forward)
- Offline pre-compute (ingest/snapshot) vs on-demand (Q&A) — red-flag extraction is offline pre-compute, cached per `drhp_id`.
- `claim_id` everywhere — METHOD-01 pane reads cached per-claim traces; never break the locked id pattern.
- No green/red coding / no performance badges — applies to confidence labels AND the red-flag table.
- Non-LLM cite-check validates before emit — numeric faithfulness is a deterministic extension of this.
- Atomic per-task commits; pytest stubs flip stub→green per wave.

### Integration Points
- New red-flag extraction step in the offline pipeline (extends `pipelines/`), cached to a per-`drhp_id` store like snapshots.
- Numeric-grounding extension inside/next to `agent/nodes/cite_check.py`.
- Methodology pane component attaches to Q&A answers (existing chat surface) and the new red-flag table.
- Pre-deploy `make release` gate wraps `scripts/run_eval.py`'s numeric track; writes to `eval/reports/`.
- Gold set + 50-query numeric set committed under `eval/gold/`.

</code_context>

<specifics>
## Specific Ideas

- Confidence rubric is **deterministic and source-anchored** (verbatim → high), not model self-report — this is a deliberate DS-rigor choice the user wants visible.
- Gold-set **n is reported honestly** (don't pad to 20-30); 20-30 is a documented target, not a faked claim.
- The numeric gate must **actually refuse deploy** (`make release` exits non-zero <0.95), not just print a number — enforcement over discipline.
- Methodology pane eval scores come from the **latest committed report**, not a live per-expand LLM call — keeps the demo fast and cheap.
- Risk list is a **single ranked list with a neutral specificity indicator**, foregrounding issuer-specific risks by rank (user preferred this over a hard collapsed boilerplate bucket).

</specifics>

<deferred>
## Deferred Ideas

- Expanding the gold set / IDF corpus to the full 20-30 DRHPs — bounded by live multi-IPO ingest (`data/INGEST_ALL_LATER.md`); grows as the catalogue goes live.
- General RAGAS faithfulness ≥0.95 gate, failure gallery, and full eval dashboards — Phase 6 (EVAL-01, FAILGAL-01).
- Peer multiples / GMP display — Phase 4.
- Cross-IPO red-flag comparison — v2.
- Live per-claim eval recomputation in the methodology pane — possible Phase 6 enhancement; v1 uses cached report scores (D3-17).

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-Structured Signal Extraction (Red-Flag Table)*
*Context gathered: 2026-06-25*
