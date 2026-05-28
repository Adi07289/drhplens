---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
last_updated: "2026-05-28T07:33:30.123Z"
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# STATE: DRHPLens

**Last Updated:** 2026-05-28

## Project Reference

**Core Value:** Cut a 400-page Indian IPO prospectus into an honest, cited answer that fuses what the document actually says with how comparable IPOs have actually behaved — so a retail investor can make an informed decision instead of subscribing on hype.

**Project Mode:** MVP (vertical-slice progression)

**Audience:** Indian retail investors (mobile-first); secondary audience is the DS-recruiter reviewing the portfolio piece.

**Current Focus:** Phase 1 — Foundation + MVP-A (Cited Q&A on One IPO).

## Current Position

**Phase:** 1 of 6 — Foundation + MVP-A
**Plan:** Not yet planned (run `/gsd-plan-phase 1`)
**Status:** Roadmap complete; awaiting first-phase planning.
**Progress:** [          ] 0% (0 of 6 phases complete)

## Phase Map

| Phase | Name | Status |
|-------|------|--------|
| 1 | Foundation + MVP-A (Cited Q&A on One IPO) | Not started |
| 2 | Multi-IPO Catalogue + DRHP Snapshot Surface | Not started |
| 3 | Structured Signal Extraction (Red-Flag Table) | Not started |
| 4 | Historical IPO Dataset + Peer Comparator + GMP Display | Not started |
| 5 | Calibrated Listing-Day Forecaster | Not started |
| 6 | Full Eval Harness + Agentic Polish + Portfolio Surface | Not started |

## Performance Metrics

(Populated as phases complete.)

- Phases completed: 0 / 6
- v1 requirements satisfied: 0 / 42
- Numeric faithfulness (release gate >=0.95): not yet measured
- Citation accuracy (release gate >=0.95): not yet measured
- Forecast empirical coverage (target 80%): not yet measured

## Accumulated Context

### Key Decisions (from PROJECT.md)

- India-focused (not US) — personal credibility + underserved market + differentiation
- IPO/DRHP decoder as v1 (vs earnings analyst) — most distinctive RAG showcase
- Honesty-first framing — cited, calibrated, not-advice (compliance + differentiator)
- Hybrid agentic architecture — RAG + NLP extraction + peer-comparison + historical-IPO forecasting
- v2 evolution toward Portfolio Red-Flag Radar SaaS

### Key Decisions (from research)

- Stack locked: LangGraph + LlamaIndex + Docling + Qdrant + BAAI/bge-m3 + XGBoost + MAPIE + RAGAS/DeepEval/Langfuse + Streamlit on HF Spaces
- Frontend: Streamlit for Phases 1-5; explicit re-evaluation gate at Phase 5 exit before considering Next.js migration
- GMP: display read-only, computationally isolated from forecast model — gap between GMP and GMP-free model output is the honest signal
- Agent: bounded LangGraph state machine (not freeform ReAct); cite-check is a deterministic code node
- Storage is the integration bus — batch pipelines write, on-demand tools read

### Cross-Cutting Invariants (from PITFALLS.md)

- Compliance posture hardcoded from Phase 1 (disclaimer + banned-token scrubber + no-personalization)
- Span-level citations from day one (not page-level); non-LLM cite-check node validates before emit
- Numeric-faithfulness >=0.95 release gate from Phase 3 onward
- Survivorship-corrected universe (SEBI-issuer-side sourced + status column)
- All forecast features carry `available_at` timestamp; walk-forward CV only
- >=35-40% non-LLM modeling time budget (cut agent scope before cutting modeling scope)
- Four baselines reported alongside every model
- GMP display !== GMP feature

### Open TODOs

- Run `/gsd-plan-phase 1` to begin Phase 1 detailed planning
- Hand-pick the single "MVP-A" IPO for Phase 1 (recent mainboard listing with a clean DRHP)
- Curate the 5-10 IPO catalogue for Phase 2 ahead of Phase 1 exit
- Begin hand-labeling extraction gold set (20-30 DRHPs) during Phase 2 (concurrent prep for Phase 3)
- Begin EDA notebooks for forecaster feature set during Phase 4 (concurrent prep for Phase 5)
- Schedule SEBI legal-review checkpoint before Phase 6 public launch

### Open Blockers

None yet.

## Research Flags (from ROADMAP.md)

- **Phase 4 start:** `jugaad-data` endpoint validation spike (~1 day) + nightly integration test setup
- **Phase 5 start:** ~1 week of EDA notebooks on India-IPO feature engineering before committing to the feature set
- **Phase 6 start:** Brief exploration spike on DeepEval CI integration + Langfuse custom-score callbacks (~1-2 days)

## Session Continuity

### What I Was Doing

Initialized the project: PROJECT.md → REQUIREMENTS.md (42 v1 reqs across 11 categories) → four research dimension files (SUMMARY/STACK/FEATURES/ARCHITECTURE/PITFALLS) → ROADMAP.md (6 vertical-slice MVP phases, 100% requirement coverage).

### Where to Resume

Run `/gsd-plan-phase 1` to decompose Phase 1 (Foundation + MVP-A) into executable plans. Phase 1's deliverable is a publicly-deployed, mobile-responsive web app where a user can ask plain-English questions about one hand-loaded DRHP and receive cited answers — with full compliance posture and citation infrastructure locked in.

### Files of Record

- `.planning/PROJECT.md` — project context and constraints
- `.planning/REQUIREMENTS.md` — 42 v1 requirements with phase mappings
- `.planning/ROADMAP.md` — 6-phase vertical-slice roadmap
- `.planning/research/SUMMARY.md` — research synthesis (start here)
- `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md` — dimension files
- `.planning/config.json` — granularity=standard, parallelization=true, model_profile=quality

---
*State initialized: 2026-05-28*
