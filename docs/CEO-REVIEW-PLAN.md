# DRHPLens — CEO-Approved Roadmap Plan

## Context

DRHPLens is a Data Scientist portfolio project (user wants a DS role; secondary ML Engineer): an Indian-IPO DRHP-decoder web app that lets retail investors ask plain-English questions about an IPO and get an honest, cited, data-grounded answer fused with a calibrated listing-day forecast.

Through the GSD `/gsd-new-project` workflow we produced:
- `~/agentic-rag-app/.planning/PROJECT.md` (committed `a934878`)
- `~/agentic-rag-app/.planning/config.json` (committed `5161580`)
- `~/agentic-rag-app/.planning/research/{STACK,FEATURES,ARCHITECTURE,PITFALLS,SUMMARY}.md` (committed `62ae53e`)
- `~/agentic-rag-app/.planning/REQUIREMENTS.md` (committed `053d257`; traceability updated post-roadmap)
- `~/agentic-rag-app/.planning/ROADMAP.md` (written by roadmapper, **uncommitted** — gating on this CEO review)
- `~/agentic-rag-app/.planning/STATE.md` (written by roadmapper, **uncommitted**)

The user then invoked `/plan-ceo-review` in plan mode to get strategic sign-off before committing the roadmap and proceeding to `/gsd-plan-phase 1`. This plan captures the CEO-review outcome: approved sequencing strategy, mode, cherry-picks, and the actions needed to commit the roadmap and proceed.

## Approved Approach (Step 0C-bis)

**APPROACH A — Vertical MVP, 6 phases.** Ship a demoable cited-Q&A on one IPO in Phase 1; layer extractors, peers, forecaster, and polish across Phases 2-6. Every phase ships a demoable artifact.

Rejected alternatives (with reason): B Forecaster-first (no demo for months; "deep notebook no app" filtered out at resume screen); C 3-phase scope-cut (saved for time-pressure fallback only); D Hybrid forecaster-notebook-first (notebook→production refactor cost not worth it given user can use approach A's natural pull-forward).

## Approved Mode (Step 0F)

**SELECTIVE EXPANSION.** Baseline = the 6-phase research-derived roadmap. Each surfaced expansion was decided individually.

## Accepted Scope Additions

These move into the plan and need to be reflected in `.planning/ROADMAP.md` before commit:

| # | Item | Phase | Effort | Risk | Rationale |
|---|------|-------|--------|------|-----------|
| E1 | Pull "Show your work" methodology pane forward from Phase 6 to **Phase 3** | 3 | M (CC ~2-3 hr) | Low | Means the earliest demoable phase already shows DS rigor visibly; huge for mid-build recruiter visits |
| E2 | Recruiter landing page at `/methodology` summarizing model card + methodology + failure gallery + eval dashboard | 6 (with stub link from home from Phase 1) | S (CC ~30-60 min) | Low | One-link pitch surface; resume deep-links land directly on the rigor |
| E6 | Live browseable `/failures` page (not just the markdown file in `eval/`) | 6 | S (CC ~1-2 hr) | Low | Honesty-first product must SHOW failures, not just file them |

**Required ROADMAP.md edits before commit:**
- Phase 3: append E1 to phase deliverables; add a Phase 3 success criterion: "methodology pane expandable on any answer reveals retrieval query + chunks + sources + scores for that specific claim."
- Phase 1: add a cross-cutting note to "Cross-Cutting Invariants": "Agent traces carry `claim_id` references from day one (not bolted on at Phase 3) so methodology-pane data exists when E1 lands."
- Phase 6: append E2 (recruiter landing page) and E6 (live failure gallery) to phase deliverables and add corresponding success criteria.
- Phase 1: add a stub `/methodology` link to the home page so resume deep-links don't 404 between Phase 1 and Phase 6.

## Deferred to TODOS.md

These are tracked but not in this milestone:

| # | Item | Reason |
|---|------|--------|
| E5 | User-uploadable DRHP path | Med risk: parser may break in demos on arbitrary PDFs; SEBI surface expands; HF Spaces compute is finite. TODOS entry must include a threat-model note (PDF parser exploits, abusive upload sizes, rate-limiting, optional SEBI-archive URL whitelist) before pickup. |
| E7 | Per-IPO pre-listing-vs-actual retrospectives | Sensible deferral — data accumulates in eval pipeline anyway; pull in after the first 2-3 covered IPOs actually list. |
| E4 | Hindi mode | Major v2-trajectory feature; ship English-only v1 first (Indian English is widely accepted for finance); Hindi RAG-faithfulness eval is its own sub-project. |
| E3 | Compare two open IPOs side-by-side | Already tracked as v2 `MULTI-IPO-COMPARE-01` in REQUIREMENTS.md; no change. |

## Cut Entirely

None.

## NOT in Scope (recap from REQUIREMENTS.md "Out of Scope")

Verbatim from `.planning/REQUIREMENTS.md`:
- "Subscribe / Avoid" verdicts (SEBI RIA + undermines honesty-first positioning)
- Investment-advice-style language
- GMP-based forecasting / using GMP as a model feature (circular + compliance optics)
- Real-time / intraday trading signals
- Personalized portfolio integration in v1 (v2 territory)
- User accounts / login / personalization in v1
- Paid data feeds (free-only constraint)
- Ad-supported / sponsored-IPO content
- SME IPO coverage
- Allotment-probability predictor (lottery by rule)
- Auto-refreshing live ticker / push notifications
- Sentiment scraping from Twitter / Reddit / Telegram
- Generic-LLM "finance chat" mode
- Mobile-native app in v1
- US / foreign markets

## What Already Exists

Greenfield project, but external leverage already baked into the research stack (no rebuilding):
- Docling 2.95 (PDF parsing)
- LangGraph 1.2 (agent orchestration)
- LlamaIndex 0.14 (retrieval)
- Qdrant + bge-m3 + bge-reranker (vectors + rerank)
- XGBoost + MAPIE (forecast + conformal intervals)
- RAGAS 0.4 + DeepEval + Langfuse (eval + observability)
- jugaad-data + yfinance .NS + chittorgarh archive (Indian financial data)
- HF Spaces + Qdrant Cloud free + Gemini Flash / Groq (free-tier deployment)

## Dream State Delta

```
  CURRENT STATE          THIS PLAN                       12-MONTH IDEAL
  Empty repo +    -->    Public DRHPLens v1 with    -->  DRHPLens v2 SaaS
  planning docs          cited Q&A + extractors +        DRHP decoder +
                         calibrated forecaster +         Portfolio Red-Flag
                         eval dashboards +               Radar +
                         recruiter landing page +        12mo of tracked
                         live failure gallery            post-listing
                                                         calibration data
```

The plan moves cleanly toward the 12-month ideal. The storage-bus + reusable LangGraph agent engine is the bridge from v1 portfolio to v2 SaaS.

**Primary risk to ideal:** hiring outcome arrives before Phase 5 (the headline calibrated forecaster). Mitigation: the Phase 3 pull-forward of the methodology pane (E1) means even a mid-build demo at Phase 3 already shows DS rigor visibly. Forecaster-first (Approach B) was rejected for shipping reasons but partially counter-acted via E1.

## Final Roadmap (6 phases, vertical MVP)

Source of truth: `.planning/ROADMAP.md` (with the four edits listed in "Accepted Scope Additions" above applied).

| # | Phase | Goal (one-line) | REQs | Notes |
|---|-------|-----------------|------|-------|
| 1 | Foundation + MVP-A | One IPO, cited Q&A end-to-end, full compliance + citation infra, public URL on HF Spaces | INGEST-01/02/03, RAG-01/02/03, TRUST-01/02/03/04, UI-01/02, OPS-02 + `claim_id` traces invariant + `/methodology` stub link | Demoable at end |
| 2 | Multi-IPO catalogue + DRHP snapshot | Browse 5-10 IPOs; per-IPO snapshot (metadata, business, financials, risks, use of proceeds, promoter) all cited | SNAP-01..07, OPS-01 | Demoable |
| 3 | Structured signal extraction + methodology pane (E1) | Red-flag table with confidence scores + gold-set F1 + numeric-faithfulness ≥0.95 release gate + "Show your work" pane | EXTRACT-01/02/03, EVAL-03, **E1** | Demoable; methodology pane LIVE here |
| 4 | Historical dataset + peer + GMP | Peer multiples, read-only caveated GMP, Indian-context formatting; survivorship-corrected historical IPO dataset (SEBI-issuer-side, status column) | PEER-01/02, GMP-01/02, UI-04 | Demoable; one research spike (~1 day jugaad-data validation) |
| 5 | Calibrated listing-day forecaster | 80% prediction interval as headline visual, GMP-vs-model gap, walk-forward backtest, 4 baselines, model card committed | FCAST-01..05, GMP-03, UI-03 | Headline DS portfolio artifact; one research spike (~1 week feature engineering EDA) |
| 6 | Full eval harness + agentic polish + portfolio (incl. E2, E6) | RAGAS/DeepEval/Langfuse dashboards inline; methodology pane fully wired; recruiter landing page (E2); live failure gallery (E6); LangGraph agent with TTL+supervisor; SEBI legal-review checkpoint | EVAL-01/02/04/05, OPS-03, **E2**, **E6** | Portfolio-presentable; ship publicly |

## Roadmap-Stage Strategic Findings (Sections 1-11 sweep)

### Section 1 — Architecture
**Status: OK.** Architectural posture (LangGraph state-machine in the middle; deterministic batch pipelines at the edges; non-LLM cite-check node; storage-bus pattern; eval hooks instrumented from Phase 1) is sound per `research/ARCHITECTURE.md`.

**Architectural shift from accepted cherry-picks:** E1 (methodology pane in Phase 3) requires agent traces to carry `claim_id` references from Phase 1 day one, not Phase 6. Captured as a Phase 1 cross-cutting invariant edit above.

### Section 2 — Error & Rescue Map
**Status: Deferred to plan-eng-review at Phase 1 plan stage.** Roadmap-level mitigations already flagged in `research/PITFALLS.md`: P8 agent infinite loops → TTL + semantic dedup + supervisor + strict Pydantic tool schemas; P2 hallucinated numbers → two-stage structured extraction; P5 citation drift → non-LLM cite-check node before emit. Concrete exception-class table belongs in the per-phase plan, not the roadmap.

### Section 3 — Security & Threat Model
**Status: OK at roadmap level, with one TODOS.md entry to enrich.**
- SEBI compliance: addressed via TRUST-01/02/03/04 (disclaimer + banned-token scrubber + RA-guideline disclosure + cite-check node).
- Data privacy: no user accounts in v1, no PII, all sources public → minimal surface.
- Scraping ToS (screener.in): flagged in PITFALLS.md P16. Mitigation: aggressive caching, throttling, Plan-B source.
- **Action:** When E5 (user-uploadable DRHP) is picked up from TODOS.md later, its TODOS entry MUST include: PDF parser exploit threat model (PDF.js / Docling CVE history), upload size cap, rate limiting, optional SEBI-archive URL whitelist, abusive upload runbook.

### Section 4 — Data Flow & Interaction Edge Cases
**Status: N/A at roadmap stage.** Surface during Phase 1 plan-eng-review.

### Section 5 — Code Quality
**Status: N/A at roadmap stage.**

### Section 6 — Test Review
**Status: OK.** The eval harness IS the test plan for this product: faithfulness, recall@k, citation accuracy, numeric-faithfulness ≥0.95 release gate, per-field extractor F1, forecast coverage / MAE / PIT, walk-forward backtest with Diebold-Mariano significance test. Per-phase plan-eng-review will detail unit/integration tests.

### Section 7 — Performance
**Status: OK with two roadmap-level callouts.**
- HF Spaces free tier: 2 vCPU, 16 GB, `/tmp`-only writes. Vector DB must be Qdrant Cloud (not local). Already in STACK.md.
- Cold-start latency may hit ~30-60s after inactivity. Add a cron pinger (e.g., a free cron-job.org keep-alive) and/or use HF Spaces' `sleep_time` configuration. Note for Phase 1 plan.
- Qdrant Cloud free tier is 1 GB. Long DRHPs at section-aware chunking can fill that fast across 10 IPOs. Mitigation: dedupe identical chunks across DRHPs, only embed unique content, prune intermediate-only chunks. Phase 1 plan should size the index.

### Section 8 — Observability
**Status: OK.** Langfuse (EVAL-05) covers traces. E1's methodology pane brings observability into the UI. Sufficient for v1.

### Section 9 — Deployment
**Status: OK.** Public HF Spaces deploy from Phase 1 (OPS-02). Rollback = redeploy previous Space build. No DB migrations to manage (Qdrant collections versioned).

### Section 10 — Long-Term Trajectory
**Reversibility: 5/5.** Web app, free-tier, no DB schema, no user data in v1. Trivial to fork, mothball, or hand off.

The storage-bus pattern + reusable agent engine make the v2 Portfolio Red-Flag Radar SaaS a natural extension. Tech debt is bounded by the ≥35% non-LLM modeling discipline and the per-phase eval gates.

### Section 11 — Design & UX
**Status: UI scope detected.** Every phase has `UI hint: yes`.

**RECOMMENDATION:** Before `/gsd-plan-phase 1`, run `/gsd-ui-phase 1` (the GSD UI design contract step) to lock UI design for: cited Q&A view, citation chip behavior, disclaimer placement, banned-token rendering, and the empty/loading/error states. This is the standard GSD UI gate; the CEO review confirms it's warranted.

**Design-finding to lock:** UI-03 specifies uncertainty as a first-class visual element. Most finance products bury uncertainty in fine print. The lake-deep version is rendering the prediction interval as the headline visual (interval-as-shape, not point-with-asterisk) and using interval width as visible communication. Lock that pattern in the UI design phase before any code is written.

## Implementation Tasks

Synthesized from this review's findings. Each task derives from a specific decision or finding above. Run with Claude Code; checkbox as you ship.

- [ ] **T1 (P1, human: ~20min / CC: ~5min)** — ROADMAP.md — Apply the four accepted-scope edits (E1 to Phase 3, E2 + E6 to Phase 6, Phase 1 `claim_id` invariant, Phase 1 `/methodology` stub link)
  - Surfaced by: Accepted Scope Additions
  - Files: `~/agentic-rag-app/.planning/ROADMAP.md`
  - Verify: `grep -n "E1\|E2\|E6\|claim_id" .planning/ROADMAP.md` shows the additions

- [ ] **T2 (P1, human: ~5min / CC: ~1min)** — REQUIREMENTS.md — Add three new REQ-IDs for E1, E2, E6 with phase mapping; update Coverage count to 45
  - Surfaced by: Accepted Scope Additions
  - Files: `~/agentic-rag-app/.planning/REQUIREMENTS.md`
  - Verify: traceability table has METHOD-01 (E1, Phase 3), LAND-01 (E2, Phase 6), FAILGAL-01 (E6, Phase 6) and v1 total = 45

- [ ] **T3 (P1, human: ~10min / CC: ~2min)** — TODOS.md — Create the file with the four deferred items: E5 (with threat-model note), E7, E4, E3 (pointer to v2 REQ-ID)
  - Surfaced by: Deferred to TODOS.md
  - Files: `~/agentic-rag-app/TODOS.md` (new file)
  - Verify: file exists, contains 4 entries each with What/Why/Effort/Priority/Depends-on

- [ ] **T4 (P1, human: ~5min / CC: ~1min)** — Commit the roadmap and updated requirements together
  - Surfaced by: ROADMAP.md needs to be committed for `/gsd-plan-phase 1` to proceed
  - Files: `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, `TODOS.md`, generated `CLAUDE.md` from `gsd-sdk query generate-claude-md`
  - Verify: `git log --oneline` shows `docs: create roadmap (6 phases) + CEO-approved scope additions`

- [ ] **T5 (P1, human: ~10min / CC: ~2min)** — Phase 1 invariant — Add the `claim_id` trace invariant to ROADMAP.md cross-cutting invariants section
  - Surfaced by: Section 1 — Architecture (E1 dependency)
  - Files: `~/agentic-rag-app/.planning/ROADMAP.md`
  - Verify: cross-cutting invariants section contains "Agent traces carry `claim_id` references from Phase 1 day one"

- [ ] **T6 (P2, human: ~30min / CC: ~5min)** — Phase 1 plan stage — Capture the HF Spaces cold-start + Qdrant 1GB cap callouts in the Phase 1 PLAN.md when it's generated
  - Surfaced by: Section 7 — Performance
  - Files: `~/agentic-rag-app/.planning/phase-1/PLAN.md` (to be created by `/gsd-plan-phase 1`)
  - Verify: PLAN.md mentions cron-pinger and index-sizing strategy

- [ ] **T7 (P2, human: ~5min / CC: ~1min)** — Recommendation note — Document that `/gsd-ui-phase 1` should be run before `/gsd-plan-phase 1`
  - Surfaced by: Section 11 — Design & UX
  - Files: This plan file (already done) + mention in `~/agentic-rag-app/CLAUDE.md` when generated
  - Verify: CLAUDE.md mentions running `/gsd-ui-phase 1` as the suggested next step

_No new tasks from Sections 2, 4, 5, 6, 8, 9, 10._

## Verification

After ExitPlanMode + executing T1-T5:

1. **Roadmap committed:** `cd ~/agentic-rag-app && git log --oneline | grep -i 'roadmap'` shows the commit.
2. **Coverage:** `grep -c '^| [A-Z].*Phase' ~/agentic-rag-app/.planning/ROADMAP.md` matches the requirement count in REQUIREMENTS.md.
3. **TODOS.md exists:** `test -f ~/agentic-rag-app/TODOS.md && head -20 ~/agentic-rag-app/TODOS.md`.
4. **Phase 3 has E1:** `grep -A 20 "Phase 3:" ~/agentic-rag-app/.planning/ROADMAP.md | grep -i "methodology\|show your work"`.
5. **Phase 6 has E2 + E6:** `grep -A 30 "Phase 6:" ~/agentic-rag-app/.planning/ROADMAP.md | grep -i "landing\|failures"`.
6. **Phase 1 invariant added:** `grep "claim_id" ~/agentic-rag-app/.planning/ROADMAP.md`.
7. **CLAUDE.md generated:** `test -f ~/agentic-rag-app/CLAUDE.md && grep -q "DRHPLens" ~/agentic-rag-app/CLAUDE.md`.
8. **End-to-end:** running `/gsd-progress` shows "Phase 1 ready to plan" and the next suggested command is `/gsd-ui-phase 1` (or `/gsd-plan-phase 1` if UI-phase is skipped).

## NOT in Scope (this review)

- Code-stage architecture / error-rescue / data-flow review — premature without code; will run as `/plan-eng-review` at each phase's plan stage.
- Cross-AI peer review (`/gsd-review`) — optional, skippable for portfolio scope.
- Codex outside-voice plan challenge — would normally be offered here but plan-mode + the user's stated intent ("get the plan approved") suggests landing the plan now is higher value than a second-model pass on a roadmap that's already research-derived.

## Unresolved Decisions

None. Every AskUserQuestion fired in this review was answered.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | clean | mode: SELECTIVE_EXPANSION, 7 proposals, 3 accepted, 4 deferred, 0 cut, 0 critical gaps |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 0 | — | required at each phase's plan stage |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | recommended at Phase 1 via `/gsd-ui-phase 1` |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **UNRESOLVED:** 0
- **VERDICT:** CEO CLEARED — ready to commit roadmap and run `/gsd-ui-phase 1` then `/gsd-plan-phase 1`. Eng review required at each phase's plan stage (`/plan-eng-review` invoked by `/gsd-plan-phase`'s plan-checker gate).
