---
phase: 03-structured-signal-extraction-red-flag-table
plan: 07
subsystem: ui
tags: [red-flag-table, idf-risk-list, specificity-meter, methodology-pane, streamlit, snapshot-page, monochrome, cached-only, no-llm, EXTRACT-01, EXTRACT-02, METHOD-01]

# Dependency graph
requires:
  - phase: 03-structured-signal-extraction-red-flag-table
    plan: 01
    provides: RedFlagRecord/RedFlagField (value/confidence_tier/confidence_score), REDFLAG_FIELD_KEYS canonical order, RankedRisk (idf_score/specificity_band), REDFLAG_QUERIES
  - phase: 03-structured-signal-extraction-red-flag-table
    plan: 03
    provides: pipelines/redflag.py load_redflag + data/redflag/<id>.json cache the page reads (offline, no request-time LLM)
  - phase: 03-structured-signal-extraction-red-flag-table
    plan: 06
    provides: ui/copy.py Phase 3 scrubber-guarded copy, app/static/drhplens.css monochrome .drhp-redflag-*/.drhp-spec-meter*/.drhp-methodology-* classes, ui/methodology_pane.py render_methodology_pane (cached-only)
  - phase: 02
    provides: pages/02_snapshot.py allow-list guard + load_snapshot try/except pattern, ui/snapshot_chat.py render_snapshot_chat, ui/chip.py render_answer_with_chips, ui/expander.py citation expanders, render_risk_block (Phase 2 empty-state fallback)
provides:
  - "ui/snapshot_blocks.py — render_redflag_table(record): 7 stacked monochrome rows in REDFLAG_FIELD_KEYS order, tabular-nums chip-rendered values, neutral Confidence:{tier} text, honest Not-disclosed rows (confidence OMITTED, L3-3), numeric-gate blocked-copy (L3-9), per-row Show-your-work pane — no red/green, no badges, no severity icons"
  - "ui/snapshot_blocks.py — render_idf_risk_list(ranked_risks, record): the SINGLE ranked risk list, descending idf_score, monochrome .drhp-spec-meter (accent fill + text % + Issuer-specific/Industry-standard word), superseding the Phase 2 prioritized ordering; render_risk_block left UNCHANGED as the empty-ranking fallback"
  - "pages/02_snapshot.py — cached RedFlagRecord loaded inside the allow-list + try/except guard; red-flag block rendered high in the locked IA; exactly ONE risk list at runtime (IDF list primary, render_risk_block only in the empty-ranking else-branch)"
  - "ui/snapshot_chat.py — METHOD-01 Show-your-work pane wired onto each Q&A answer (the primary METHOD-01 surface), cached-only"
affects: [Phase 6 methodology page + eval surfacing, Phase 4/5 snapshot-page additions build on this locked IA]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cached-only page render: the red-flag table + IDF list + Q&A pane read only the committed RedFlagRecord/GroundedAnswer cache — zero request-time LLM/Qdrant calls on the snapshot page"
    - "Single-risk-list reconciliation: render_idf_risk_list supersedes the Phase 2 render_risk_block ordering; render_risk_block is retained ONLY as the else-branch fallback when ranked_risks is empty (exactly one renders at runtime)"
    - "Streamlit container correctness: styled card wrappers must be a single st.container(border=True) — a div split across two st.markdown calls does not wrap (each markdown is isolated)"
    - "Per-element Streamlit keys: every methodology-pane toggle/expander carries a unique key (per-field / per-answer) to avoid StreamlitDuplicateElementId"

key-files:
  created: []
  modified:
    - ui/snapshot_blocks.py
    - pages/02_snapshot.py
    - ui/snapshot_chat.py
    - ui/copy.py
    - ui/methodology_pane.py
    - tests/unit/test_methodology_pane.py

key-decisions:
  - "Task 3 was a checkpoint:human-verify (375px mobile visual contract) — the human ran the app against a seeded RedFlagRecord and APPROVED; the checkpoint is PASSED"
  - "The methodology pane was redesigned during verification into an investor-first two-tier pane: plain-English source verification leads (DRHP page + verbatim quote blockquote + one-line trust sentence), developer internals moved behind an off-by-default Show-technical-details toggle (274a02e)"
  - "A runtime-only rendering bug (styled div split across two st.markdown calls rendered as an empty white bar) was fixed live with st.container(border=True); unique per-element keys added to fix a StreamlitDuplicateElementId crash (c8e301b) — neither was catchable offline because the executor cannot run Streamlit"

patterns-established:
  - "Locked snapshot IA: metadata header → red-flag signals table (above-the-fold-adjacent) → single IDF risk list → remaining Phase 2 blocks → Q&A chat with per-answer methodology pane → footer"
  - "Two-tier methodology pane: investor-facing verification by default, developer internals behind an opt-in toggle (off by default)"

requirements-completed: [EXTRACT-01, EXTRACT-02, METHOD-01]

# Metrics
duration: ~40min (implementation) + human visual verification
completed: 2026-07-06
---

# Phase 3 Plan 07: Red-Flag Table + Single IDF Risk List + Methodology Pane Wired Into the Snapshot Page Summary

**The Phase 3 payoff made real: opening any covered IPO's snapshot page now renders the Red-flag signals table (7 stacked monochrome rows in canonical order — tabular-nums chip-rendered values, neutral `Confidence: high|medium|low` text, honest `Not disclosed in DRHP` rows with confidence omitted, and the numeric-gate blocked-copy for ungrounded numbers — no red/green, no badges, no severity icons), a SINGLE IDF-ranked risk list with a monochrome specificity meter (accent fill + text % + Issuer-specific/Industry-standard word) that supersedes the Phase 2 prioritized ordering, and the cached-only "Show your work" methodology pane on both red-flag fields and every Q&A answer — all reading the committed `RedFlagRecord` cache with zero request-time LLM calls.**

## Performance

- **Duration:** ~40 min implementation across Tasks 1-2, plus a human visual-verification checkpoint (Task 3)
- **Tasks:** 3 (Task 1 auto, Task 2 auto, Task 3 checkpoint:human-verify — APPROVED)
- **Files modified:** 6 (across all commits, incl. the two post-verification refinement commits)

## Accomplishments

- **Task 1 — `render_redflag_table` + `render_idf_risk_list` + pane wiring (`40df830`):** extended `ui/snapshot_blocks.py` with `render_redflag_table(record)` rendering the 7 `REDFLAG_FIELD_KEYS` rows (chip-rendered `GroundedAnswer` values via the UNCHANGED `render_answer_with_chips`, neutral confidence text, `_render_not_disclosed` for refusals with the confidence label OMITTED, `FIELD_NUMERIC_GATE_BLOCKED` copy for numeric-gate-blocked fields, and a per-row `render_methodology_pane`), plus the NEW `render_idf_risk_list(ranked_risks, record)` — descending `idf_score` order, the monochrome `.drhp-spec-meter` with a text `%` label + the specificity word, a SINGLE list with no collapsed boilerplate bucket. `render_risk_block` was left UNCHANGED as the Phase-2 empty-state fallback. No red/green/severity coding.
- **Task 2 — wired into the snapshot page in the locked IA (`5586df9`):** extended `pages/02_snapshot.py` to `load_redflag(drhp_id)` inside the same allow-list + try/except guard as `load_snapshot`, render `render_redflag_table` high on the page, and reconcile to a SINGLE risk list (`if redflag_record.ranked_risks:` → `render_idf_risk_list(...)`; `else:` → the Phase 2 `render_risk_block(...)` fallback — exactly one renders at runtime). Wired `render_methodology_pane` onto each Q&A answer in `ui/snapshot_chat.py` (the primary METHOD-01 surface).
- **Task 3 — mobile-first visual verification (checkpoint:human-verify, APPROVED):** the human ran the app against a seeded record at a 375px viewport and confirmed the visual/interaction contract pytest cannot assert (7 rows stack without horizontal scroll, no red/green, single IDF list, honest not-disclosed rows, instant cached panes). Approved — with two refinements requested/discovered live (documented under Deviations).

## Task Commits

1. **Task 1: red-flag table + IDF risk renderer + methodology-pane wiring** — `40df830` (feat)
2. **Task 2: wire red-flag table + single IDF risk list + Q&A pane into the snapshot page** — `5586df9` (feat)
3. **Task 3: mobile-first visual verification (375px)** — checkpoint:human-verify, **APPROVED** (no code commit; verification gate)

**Post-verification refinement commits (discovered during Task 3's human verification):**

4. **Investor-first two-tier methodology pane** — `274a02e` (feat, scoped 03-06) — pane redesign
5. **Real container for red-flag card + unique pane keys** — `c8e301b` (fix, 03-07) — runtime-only bug fixes

**Plan metadata:** this closeout commit (docs: complete plan)

## Files Created/Modified

- `ui/snapshot_blocks.py` — `render_redflag_table` (7 monochrome rows, honest refusals, blocked-number copy, per-row pane) + NEW `render_idf_risk_list` (single ranked list, specificity meter); `render_risk_block` unchanged (modified in `40df830` + `c8e301b`)
- `pages/02_snapshot.py` — cached `RedFlagRecord` load in the allow-list/try-except guard, red-flag block high in the locked IA, single-risk-list reconciliation (modified in `5586df9`)
- `ui/snapshot_chat.py` — METHOD-01 pane wired onto each Q&A answer (modified in `5586df9` + `274a02e`)
- `ui/copy.py` — investor-first pane copy incl. `METHODOLOGY_TECH_TOGGLE` ("Show technical details") + trust-sentence copy (modified in `274a02e`)
- `ui/methodology_pane.py` — two-tier pane: plain-English source verification by default, developer internals behind the off-by-default toggle (modified in `274a02e`)
- `tests/unit/test_methodology_pane.py` — updated to assert the two-tier pane structure (modified in `274a02e`)

## Decisions Made

- **Task 3 checkpoint is PASSED via human approval:** the mobile-first 375px visual contract (row stacking, no red/green, single IDF list, instant cached pane) was verified by the human against a seeded record and explicitly approved. This is the intended flow for a `checkpoint:human-verify` — no code artifact, the approval is the gate result.
- **Single risk list at runtime:** `render_idf_risk_list` is the primary renderer; `render_risk_block` fires only in the empty-`ranked_risks` else-branch — the IDF list supersedes the Phase 2 prioritized ordering (UI-SPEC IA reconciliation), never two competing lists.
- **Methodology pane leads with investor verification:** during verification the pane was restructured so the default view leads with plain-English source verification (DRHP page + verbatim quote as a blockquote + a one-line trust sentence combining confidence-in-words + the committed citation-accuracy %); the numeric/dev internals (retrieval query, chunk scores, full prompt, raw eval report, numeric confidence score) moved behind a `Show technical details` toggle, off by default.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 → user-directed] Investor-first two-tier methodology pane redesign**
- **Found during:** Task 3 (human visual verification)
- **Issue:** The plan's methodology pane surfaced developer internals (retrieval query, chunk scores, full prompt, raw eval report, numeric confidence score) up-front. During live verification the user judged this developer-first ordering wrong for the retail-investor primary audience — the pane should lead with plain-English source verification, not internals.
- **Fix:** Redesigned `render_methodology_pane` into a two-tier pane: the default view now leads with plain-English source verification (DRHP page + verbatim quote rendered as a blockquote + a one-line trust sentence combining confidence-in-words and the committed citation-accuracy %); the developer internals moved behind a `Show technical details` toggle (`METHODOLOGY_TECH_TOGGLE`), off by default.
- **Files modified:** ui/copy.py, ui/methodology_pane.py, ui/snapshot_chat.py, tests/unit/test_methodology_pane.py
- **Verification:** unit tests updated + green; the numeric confidence score still surfaces ONLY inside the pane (behind the toggle now), honoring D3-02/L3-2.
- **Committed in:** `274a02e` (scoped 03-06 as it touches the 03-06 pane module)

**2. [Rule 1 - Bug] Red-flag card rendered as an empty white bar (split-div container) + StreamlitDuplicateElementId crash**
- **Found during:** Task 3 (human visual verification — a runtime-only defect the offline executor could not surface, since it cannot run Streamlit)
- **Issue:** (a) the red-flag card wrapper was a styled `<div>` split across two separate `st.markdown` calls; Streamlit isolates each markdown render, so the styled div closed empty (rendering as a white bar) while the rows flowed outside it. (b) The methodology-pane toggles collided on `StreamlitDuplicateElementId` because multiple panes (per-field / per-answer) shared the same auto-generated element id.
- **Fix:** (a) replaced the split-div wrapper with a real `st.container(border=True)`; (b) added a unique Streamlit `key` to each methodology-pane toggle (per-field / per-answer).
- **Files modified:** ui/snapshot_blocks.py
- **Verification:** re-verified live by the human at 375px — the card now wraps its rows and every pane opens without the duplicate-id crash.
- **Committed in:** `c8e301b`

---

**Total deviations:** 2 (1 user-directed redesign surfaced during human verification; 1 Rule-1 runtime bug fix). Both were discovered live during the Task 3 visual checkpoint — the class of defect (Streamlit render behavior + audience-fit of the pane) is intrinsically unobservable to the offline executor, which cannot run Streamlit.
**Impact on plan:** No architectural change and no scope creep — the red-flag table, single IDF list, and pane wiring all match the plan's `<action>`/`<success_criteria>`. The refinements improved audience-fit (pane) and corrected runtime rendering (container/keys) without altering the data contract or the IA.

## Issues Encountered

- The executor could not run Streamlit (no live infra), so two runtime-only defects (the split-div white bar and the duplicate-element-id crash) only surfaced when the human ran the app during the Task 3 checkpoint. Both were fixed in `c8e301b`. This is the intended value of the `checkpoint:human-verify` gate.
- Test runner is `.venv/bin/python -m pytest` (plain `python`/`pytest` not on PATH) — used throughout.

## User Setup Required

None - no external service configuration required for this plan.

**Phase-level pending (does NOT block this plan's code completion):** the 03-05 live `make release` numeric-faithfulness gate remains pending on the user's environment — it needs `GEMINI_API_KEY` + live Qdrant with the numeric gold-set ingested. The gate logic is CI-tested offline (0.94 fails / 0.95 / 0.96 pass); only the live verification remains (EVAL-03 stays open until then).

## Verification

- `.venv/bin/python -m pytest -q` whole suite — **303 passed, 7 skipped, 7 xfailed, 1 failed**; the single failure is the pre-existing out-of-scope `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` (missing `sentence-transformers` / live model), explicitly ignorable. No regression from the page wiring.
- Structural gates: `render_redflag_table` + `render_idf_risk_list` present in `ui/snapshot_blocks.py`; `pages/02_snapshot.py` imports/calls `load_redflag` + `render_redflag_table` + `render_idf_risk_list`, with `render_risk_block` reachable ONLY in the empty-ranking else-branch (single risk list); `render_methodology_pane` wired in `ui/snapshot_chat.py`.
- Task 3 (checkpoint:human-verify): mobile-first 375px visual contract confirmed by the human against a seeded record — **APPROVED**.

## Known Stubs

None. The page renders the red-flag table, single IDF risk list, and methodology panes from the live cached `RedFlagRecord`/`GroundedAnswer` structures. The empty-state (no cached red-flag record) and error-state (amber `.drhp-refusal` banner) are honest degraded paths, not unwired placeholders. `data/redflag/` holds a local synthetic demo artifact used for the human's visual verification (left untracked, not part of the shipped code).

## Next Phase Readiness

- The Phase 3 headline surfaces are wired into the live snapshot page in the locked IA — the phase's user-visible payoff is complete. Phase 3 code work is done (7 of 7 plans).
- The two-tier methodology pane pattern (investor-first default + developer toggle) and the locked snapshot IA are the foundation Phase 6 builds the full methodology/eval surfacing on.
- ONE human-only item remains open at the phase level: the 03-05 live `make release` numeric-faithfulness gate (needs `GEMINI_API_KEY` + live Qdrant with the gold-set ingested). It does NOT block code completion of this plan or the phase's code work; EVAL-03 stays open until that live run is executed on the user's environment.

## Self-Check: PASSED

- `.planning/phases/03-structured-signal-extraction-red-flag-table/03-07-SUMMARY.md` present on disk.
- Commits `40df830` (Task 1), `5586df9` (Task 2), `274a02e` (pane redesign), `c8e301b` (runtime fix) all present in git history.
- `render_redflag_table` + `render_idf_risk_list` present in `ui/snapshot_blocks.py`; `load_redflag` + both renderers wired into `pages/02_snapshot.py`; `render_methodology_pane` wired into `ui/snapshot_chat.py`.

---
*Phase: 03-structured-signal-extraction-red-flag-table*
*Completed: 2026-07-06*
</content>
</invoke>
