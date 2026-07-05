---
phase: 03-structured-signal-extraction-red-flag-table
plan: 06
subsystem: ui
tags: [methodology-pane, show-your-work, streamlit, scrubber, copy, monochrome-css, cached-only, no-llm, eval-report, METHOD-01]

# Dependency graph
requires:
  - phase: 03-structured-signal-extraction-red-flag-table
    plan: 01
    provides: RedFlagRecord/RedFlagField (confidence_tier/confidence_score), REDFLAG_FIELD_KEYS, tests/eval/conftest.py synthetic_redflag_record fixture
  - phase: 03-structured-signal-extraction-red-flag-table
    plan: 03
    provides: data/redflag/<id>.json cache shape the pane reads (offline)
  - phase: 01
    provides: ui/copy.py import-time scrubber assertion (TRUST-03 anchor), ui/expander.py render_citation_expanders/metadata_footer, app/static/drhplens.css single-source stylesheet, agent/schemas.py GroundedAnswer/Claim/RetrievedChunkRef
provides:
  - "ui/copy.py — Phase 3 scrubber-guarded copy: red-flag headings/sub-lines, the 7 field labels, Confidence:{tier} + rubric, numeric-gate-blocked copy, risk headings + specificity-counter, specificity words + band map, spec-meter aria, Show your work + 5 pane labels, eval provenance/not-available notes, empty/error states"
  - "app/static/drhplens.css — monochrome .drhp-redflag-table/.drhp-redflag-row/.drhp-confidence-label/.drhp-spec-meter*/.drhp-methodology-* classes (accent only for meter fill; no new color, no red/green)"
  - "ui/methodology_pane.py — render_methodology_pane(...): cached-only Show-your-work expander rendering the 5 methodology lines from cached GroundedAnswer + committed eval report; latest_eval_scores(dir) helper; numeric confidence surfaces only here; zero live LLM/Qdrant call"
affects: [03-07 red-flag rendering plan (wires copy + CSS + pane into the page), Phase 6 methodology page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cached-only render component: render_methodology_pane consumes only cached/committed data (no arg is a live client); pinned by an inspect.getsource substring gate (mirrors test_cite_check.test_no_llm_judge_fallback)"
    - "Reuse-not-reimplement citation rendering: the pane builds a chip_map over grounded_answer.claims and calls ui.expander.render_citation_expanders for the HTML-escaped metadata_footer (Sources cited line)"
    - "latest_eval_scores: ISO-date-prefixed eval/reports/*.md filenames sort lexically == chronologically; max(name) is the newest committed report; missing dir/no report -> None -> eval-not-available copy"
    - "Cross-directory fixture re-export: tests/unit/conftest.py imports synthetic_redflag_record from tests.eval.conftest to share one fixture body across tests/unit and tests/eval"

key-files:
  created:
    - ui/methodology_pane.py
    - tests/unit/conftest.py
  modified:
    - ui/copy.py
    - app/static/drhplens.css
    - tests/unit/test_methodology_pane.py

key-decisions:
  - "Numeric confidence_score (0.00-1.00) + rubric tier are rendered ONLY inside the pane (D3-02/L3-2) — never exported into any up-front-row helper"
  - "Chunk scores are read directly from the cached grounded_answer.claims[].sources[].score (the render_citation_expanders descriptor omits score); expander is reused for the metadata_footer / Sources-cited line"
  - "latest_eval_scores returns {raw, report_name} (full report text + filename) and degrades to None (not a crash) on a missing/empty report dir — STRIDE T-03-06 malformed-report robustness"
  - "Task 1 (copy + CSS) was already complete from a prior session (commit 4b01ea7); this session executed Task 2 (the pane) only, plus closeout"

patterns-established:
  - "no-live-client gate via inspect.getsource substring scan (Pitfall 5) reused for a UI render module"
  - "shared pytest fixture re-export through a directory-local conftest import"

requirements-completed: [METHOD-01, EXTRACT-02]

# Metrics
duration: ~15min
completed: 2026-07-05
---

# Phase 3 Plan 06: Methodology Pane + Scrubber-Guarded Copy + Monochrome CSS Summary

**The Phase 3 UI foundation: all new user-facing copy added to `ui/copy.py` under its import-time banned-token scrubber assertion, the monochrome `.drhp-redflag-*`/`.drhp-confidence-label`/`.drhp-spec-meter*`/`.drhp-methodology-*` classes in the single stylesheet (accent only for the meter fill), and `ui/methodology_pane.py` — a cached-only "Show your work" expander that renders the five methodology lines (query / retrieved chunks+scores / prompt / sources cited / committed eval scores) from the cached `GroundedAnswer` + the latest committed `eval/reports/*.md`, surfaces the numeric confidence score only here, and makes zero live LLM/Qdrant calls (pinned by an `inspect.getsource` no-client gate).**

## Performance

- **Duration:** ~15 min (Task 2 + closeout; Task 1 was completed in a prior session)
- **Tasks:** 2 (Task 1 auto — prior session; Task 2 `tdd="true"` — this session, tests already RED, made GREEN)
- **Files modified:** 5 (2 created this session, 3 modified across the plan)

## Accomplishments

- **Task 2 (METHOD-01 / D3-17 / Pitfall 5):** `ui/methodology_pane.py` with `render_methodology_pane(*, query, grounded_answer, prompt_path="agent/prompts/generate.md", confidence_tier=None, confidence_score=None, eval_report_dir="eval/reports")`. Opens one `st.expander(METHODOLOGY_TRIGGER, expanded=False)` and renders top-to-bottom: (1) the retrieval query; (2) retrieved chunks with per-source `score`/`section`/`page`/verbatim span read from the cached `claims[].sources[]`; (3) the developer-authored prompt text read off `prompt_path`; (4) the `Sources cited` line reusing `ui.expander.render_citation_expanders(...)[].metadata_footer` (HTML-escaped); (5) the eval-scores line from the latest committed report. The numeric `confidence_score` + rubric tier appear ONLY here.
- **`latest_eval_scores(eval_report_dir)`:** picks the most-recently-dated `eval/reports/*.md` (ISO-date-prefixed filenames sort lexically), returns `{"raw": <report text>, "report_name": <filename>}`, or `None` when the dir is missing / holds no report — driving the eval-not-yet-available copy without recomputing anything.
- **No-live-call gate:** the module imports no `openai`/`genai`/`instructor`/`groq`/`qdrant` client and never invokes the graph; `test_no_llm_or_qdrant_import` (`inspect.getsource` substring scan) passes.
- **Task 1 (prior session — L3-1/L3-8, commit `4b01ea7`):** all Phase 3 copy under the import-time scrubber assertion and the monochrome CSS classes in `app/static/drhplens.css`. Verified this session that `METHODOLOGY_EVAL_NOT_AVAILABLE` and the 5 pane labels already exist verbatim — no copy constant needed to be added.

## Task Commits

1. **Task 1: Phase 3 scrubber-guarded copy + monochrome CSS** — `4b01ea7` (feat) — *prior session*
2. **Task 2: cached-only methodology pane (GREEN, incl. already-RED test + fixture re-export)** — `65586d2` (feat) — *this session*

**Plan metadata:** committed with SUMMARY + STATE + ROADMAP (docs: complete plan)

_Note: the Task 2 test file was authored RED in a prior session; this session shipped the GREEN implementation and committed it together with the implementation (a single `feat` commit is acceptable when the test already exists)._

## Files Created/Modified

- `ui/methodology_pane.py` — `render_methodology_pane` + `latest_eval_scores`; cached-only 5-line pane, no live call (created)
- `tests/unit/conftest.py` — re-exports `synthetic_redflag_record` from `tests.eval.conftest` so the unit test can see it (created)
- `tests/unit/test_methodology_pane.py` — 5 tests (renders-from-cache, eval-not-available, latest-report-pick, none-when-empty, no-llm-import) flipped RED→GREEN (modified)
- `ui/copy.py` — Phase 3 copy under the scrubber assertion (modified — Task 1, prior session)
- `app/static/drhplens.css` — monochrome Phase 3 classes (modified — Task 1, prior session)

## Decisions Made

- **Chunk scores read from the source, not the descriptor:** `render_citation_expanders` returns `metadata_footer`/`snippet`/`section` but not `score`, so the "Retrieved chunks (with scores)" line iterates `grounded_answer.claims[].sources[]` directly for the `0.88`-style score while still reusing the expander for the escaped `Sources cited` footer — reuse where the shape fits, read the cache where it does not.
- **Numeric confidence only in the pane:** `confidence_score` is rendered via `st.caption(f"Confidence score: {confidence_score}")` inside the expander and nowhere else, honoring D3-02/L3-2.
- **Fixture re-export over duplication:** `synthetic_redflag_record` lives once in `tests/eval/conftest.py`; `tests/unit/conftest.py` imports it rather than copying the body — single source of truth, no collection collision.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Cross-directory fixture not visible to the unit test**
- **Found during:** Task 2 (running the already-RED tests)
- **Issue:** `test_methodology_pane.py` (in `tests/unit/`) uses the `synthetic_redflag_record` fixture, but the fixture is defined in `tests/eval/conftest.py`; pytest conftest scoping does not share it across sibling directories, so both fixture-using tests errored with `fixture 'synthetic_redflag_record' not found`.
- **Fix:** Added `tests/unit/conftest.py` re-exporting the fixture (`from tests.eval.conftest import synthetic_redflag_record`) — no fixture-body duplication, no test-assertion change.
- **Files modified:** tests/unit/conftest.py (created)
- **Verification:** all 5 pane tests pass.
- **Committed in:** `65586d2`

**2. [Rule 3 - Blocking] Module docstring tripped the no-client substring gate**
- **Found during:** Task 2 (running `test_no_llm_or_qdrant_import`)
- **Issue:** the docstring literally contained the lowercase token `qdrant` (in the phrase `no_llm_or_qdrant_import`), which the case-sensitive `inspect.getsource` substring scan flagged even though the module makes no live call.
- **Fix:** reworded the docstring to "no LLM or vector-DB client" / "the no-live-client test" so no forbidden lowercase token appears in source (a capitalized "Qdrant" in prose is fine — the gate is case-sensitive).
- **Files modified:** ui/methodology_pane.py
- **Verification:** `test_no_llm_or_qdrant_import` passes; `grep -niE 'openai|genai|instructor|groq|qdrant|GRAPH.invoke'` shows only the case-sensitive-safe capital "Qdrant".
- **Committed in:** `65586d2`

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking issues that prevented the already-RED tests from going green). No scope creep, no architectural change; the pane behavior matches the plan's `<action>`/`<behavior>`.
**Impact on plan:** Both fixes were necessary to make the pre-written tests pass; neither altered the pane's contract or the test assertions.

## Issues Encountered

- Test runner is `.venv/bin/python -m pytest` (plain `python`/`pytest` not on PATH) — used throughout.

## User Setup Required

None - no external service configuration required.

## Verification

- `.venv/bin/python -m pytest tests/unit/test_methodology_pane.py -q` — **5 passed**.
- `.venv/bin/python -m pytest -q` whole suite — **302 passed, 7 skipped, 7 xfailed, 1 failed**; the single failure is the pre-existing out-of-scope `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` (missing `sentence-transformers` / live model), explicitly ignorable. No regression.
- Acceptance gates: `grep -c 'from ui.expander import' ui/methodology_pane.py` = 1 (≥1); `grep -v '^#' ui/methodology_pane.py | grep -Ec 'import (openai|genai|instructor|groq|qdrant)|GRAPH.invoke'` = 0; `import ui.copy` passes the scrubber assertion; `METHODOLOGY_EVAL_NOT_AVAILABLE` exists and renders when no report is present.

## Known Stubs

None. The pane renders all five lines from live-cached data structures + a real on-disk report; the eval-not-available path is the honest degraded state (D3-17), not an unwired placeholder. Wiring the pane into the rendered page is Plan 07's job (this plan builds the isolated, independently-tested component).

## Next Phase Readiness

- Copy, CSS, and the methodology pane are the isolated foundation Plan 07 wires into the red-flag page.
- The eval-scores line reads whatever the latest committed `eval/reports/*.md` is; real per-field F1 numbers materialize once the offline extraction run (deferred-to-live in 03-04) produces populated reports.

## Self-Check: PASSED

- `ui/methodology_pane.py` and `tests/unit/conftest.py` present on disk; `tests/unit/test_methodology_pane.py` modified.
- Commit `65586d2` (Task 2) and `4b01ea7` (Task 1) present in git history.

---
*Phase: 03-structured-signal-extraction-red-flag-table*
*Completed: 2026-07-05*
