---
phase: 05-calibrated-listing-day-forecaster
plan: 07
subsystem: ui
tags: [streamlit, forecast-band, prediction-interval, gmp-marker, calibration-metrics, honesty-invariant, css, cache-only, isolation, wcag]

# Dependency graph
requires:
  - phase: 05-calibrated-listing-day-forecaster
    provides: "05-03 ForecastRecord schema + allow-list-gated load_forecast reader (the cache-only seam this block renders from); 05-01 committed seed render records (swiggy full-render + hyundai abstain) + the two-direction isolation audit whose forward check against ui.forecast_block now runs"
  - phase: 04-historical-ipo-dataset-peer-comparator-gmp
    provides: "GmpRecord + load_gmp cache reader (the GMP marker source); ui.format_inr (the ONE ₹ formatter); the snapshot page block grammar (st.container(border=True, key=...), guarded try/except reads, render_per_answer_footer, .drhp-refusal / .drhp-not-disclosed)"
provides:
  - "ui.forecast_block — cache-only Streamlit render: render_forecast_block(record, gmp_record, issue_price) (band + faint median tick + full-height 0% rule + hollow muted GMP diamond + always-visible coverage/MAE/per-year-RMSE strip + Full-model-card link) plus render_forecast_not_covered / render_forecast_error for the empty/error states"
  - "D-1 axis math as pure helpers: _domain (anchor set incl. 0, 0.08 pad with a 2.0 floor, outward-rounded to 5) + pos(v,lo,hi) clamped to [0,100]; _gmp_implied_return_pct = premium/issue_price*100 (display-layer, never a model feature)"
  - ".drhp-forecast-* CSS on the current dark --drhp-* tokens (band is the ONE amber element; GMP marker/median/0%/metrics fully monochrome) + responsive stacking under the four inherited breakpoints"
  - "Forecast section wired into pages/02_snapshot.py after the peer block, before ranked-risks (L5-4); GMP block stays LAST (D4-02)"
  - "05-UI-SPEC §Copywriting-Contract forecast strings in ui/copy.py under the import-time scrubber"
affects: [05-06, 05-08, 05-09, 05-10, 05-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cache-only render slice landing in PARALLEL with the offline model: the block renders entirely from committed seed ForecastRecords (05-01), so the UI ships before the real walk-forward run (05-06/05-11) with no render change needed when real records land"
    - "Pure-string HTML builders behind thin Streamlit wrappers: _plot_html / _caption_html / _gap_html / _tested_strip_html / _cardlink_html return escaped strings, tested WITHOUT a Streamlit runtime via a fake-st capture harness (monkeypatch the module-level st)"
    - "Honesty-invariant render: band WIDTH is the message (no point-estimate headline, no Display-size number, no green/red — P21); empirical coverage shown as the real held-out number even when it misses 80% (P17); absence (abstain/not-covered/no-GMP) rendered as an honest note, never a fabricated band/metric/GMP"
    - "Display-layer GMP-implied conversion on the SAME return axis: gmp_premium/issue_price*100 reads only cached GMP + cached issue price; the render imports no model module (FCAST-02, pinned by the now-active forward isolation audit)"

key-files:
  created:
    - ui/forecast_block.py
    - tests/unit/test_forecast_block_render.py
  modified:
    - ui/copy.py
    - app/static/drhplens.css
    - pages/02_snapshot.py

key-decisions:
  - "GMP marker uses the MEDIAN of the cached aggregator quotes as the single representative premium (robust across a 2-3 source spread), converted in the display layer; marker + gap line honestly OMITTED (band still renders, no-gap note shown) when no GMP is reported OR no issue price is available — never a fabricated GMP"
  - "No structured per-share issue price is surfaced by SnapshotRecord yet (metadata is a cited GroundedAnswer, not a parsed price), so the page wiring passes issue_price=None via _issue_price_for(record); the GMP marker is honestly omitted today and lights up unchanged once a real issue price lands (05-06/05-11)"
  - "The not-covered + error states live in ui.forecast_block (render_forecast_not_covered / render_forecast_error) — not duplicated in the page — so all five render states are covered in one testable module; the page helper just dispatches error/missing/present"
  - "Per-year RMSE renders as a real 2-column <table> (Year / RMSE, th scope=col, overflow-x:auto) — SR-navigable, never stacked cards; a genuinely-absent year renders the em-dash with aria-label='Not available'"
  - "UI-03/FCAST-04/GMP-03 render-HALVES delivered against the 05-01 seed fixtures; kept Pending in REQUIREMENTS.md until the real records land (mirrors 05-03's FCAST-02-pending posture) — marking them Complete on fixture data would be dishonest"

patterns-established:
  - "Fake-st capture harness: a _CaptureSt with container/markdown/caption/expander monkeypatched onto the module-level st lets render-state tests assert on the emitted HTML (exactly-one-plot-markdown, no expander, no Display-size) with zero Streamlit runtime"
  - "The plot is ONE self-contained st.markdown with inline left:% markers (the Phase 3 white-bar lesson): a single st.container(border=True, key='drhpcard-forecast') wrapper, never a split div"

requirements-completed: [FCAST-01]

# Metrics
duration: ~40 min
completed: 2026-07-19
---

# Phase 05 Plan 07: Calibrated Forecast Band Render Summary

**Shipped the phase's HEADLINE user-facing surface — a cache-only Streamlit forecast section (`ui/forecast_block.py`) rendering the calibrated 80% listing-day-return BAND as the dominant width-driven visual (no point-estimate headline, P21), a muted hollow-diamond GMP-vs-model marker with a labeled gap on the same return axis (display-layer conversion, GMP-03), and an always-visible empirical-coverage / MAE / per-year-RMSE honesty strip (P17, FCAST-04) — wired into the snapshot page after the peer block and before ranked-risks (L5-4), rendering entirely from the 05-01 seed fixtures and importing no model module.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-19
- **Tasks:** 3
- **Files modified:** 5 (2 created, 3 modified)
- **Tests:** `pytest tests/unit -q` → 417 passed, 2 skipped, 1 pre-existing embedder failure (sentence-transformers absent — the documented ignorable failure, not a regression). Baseline was 402 passed / 3 skipped; +14 new render/math tests and the 05-03 forward isolation audit against `ui.forecast_block` is now ACTIVE and green (one importorskip skip converted to a pass).

## Accomplishments
- `ui/forecast_block.py` — the cache-only forecast render. `render_forecast_block(record, gmp_record, issue_price)` fans out covered+GMP (full) / covered+no-GMP (band + honest no-gap note) / abstain (honest note, no band) inside ONE `st.container(border=True, key="drhpcard-forecast")`; the plot (band + median tick + full-height 0% rule + hollow muted GMP diamond + scale) is ONE self-contained `st.markdown` with inline `left:%`. `render_forecast_not_covered` / `render_forecast_error` carry the empty/error states. D-1 axis math (`_domain` / `pos` / `_gmp_implied_return_pct`) as pure helpers. Imports NO model/feature/historical module; every record-sourced string `html.escape`'d (T-05-07-XSS).
- `app/static/drhplens.css` — `.drhp-forecast-*` classes on the current dark `--drhp-*` tokens: band (the ONE amber element — `rgba(224,162,78,0.16)` wash + `rgba(224,162,78,0.60)` 2px edges, 6px radius, 28px tall, 4px min visual width), faint neutral median tick, full-height 0% rule, hollow muted GMP diamond + stem (NEVER amber), axis scale, Body caption, gap line, the always-visible tested strip (eyebrow/stat-grid/RMSE table/note), and the accent-as-text model-card link with a 44×44 `::before` enlarger; responsive stat-row stacking under the existing four breakpoints.
- `ui/copy.py` — every 05-UI-SPEC §Copywriting-Contract forecast string as module-level constants under the import-time scrubber (heading, GMP-free sub-line, interval caption, median annotation, GMP-gap + no-GMP note, tested-strip labels + honesty note, model-card link, not-covered + abstain + error states, both aria-labels); new format placeholders registered in `_SAMPLE_FORMAT_VALUES`. `range`/`interval`/`median` only — no `target` stem.
- `pages/02_snapshot.py` — a forecast cache read with the SAME allow-list-guarded try/except posture as the peer/GMP reads, a `_render_forecast_block` dispatcher, and the render call placed INSIDE `if record is not None:` after `_render_peer_block(...)` and before the ranked-risks branch (L5-4); the quiet GMP block stays the LAST read block (D4-02).

## Task Commits

Each task was committed atomically:

1. **Task 1: Forecast copy strings + .drhp-forecast-* CSS** — `bcb1a62` (feat)
2. **Task 2: ui/forecast_block.py — cache-only render + render-state tests** — `556b1fe` (feat)
3. **Task 3: Wire the forecast block into pages/02_snapshot.py (after peer, before ranked-risks)** — `2bec4bc` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified
- `ui/forecast_block.py` (NEW) — cache-only render + D-1 pure math + empty/error renderers; isolation-clean (no `xgboost`/`mapie`/`sklearn`/`conformal`/`shap`/model-pipeline substrings — the `shape`→`shap` gotcha avoided).
- `tests/unit/test_forecast_block_render.py` (NEW) — full / covered-no-gmp / abstain / not-covered / error render states via the fake-st capture harness + D-1 axis-position math + a CSS 4px-band-floor check (14 tests).
- `ui/copy.py` (MOD) — Phase 5 forecast copy section + new `_SAMPLE_FORMAT_VALUES` placeholders.
- `app/static/drhplens.css` (MOD) — `.drhp-forecast-*` classes + responsive rules.
- `pages/02_snapshot.py` (MOD) — imports, forecast cache read, `_render_forecast_block` + `_issue_price_for` helpers, the L5-4 render call.

## Decisions Made
- **Representative GMP premium = median of cached quotes.** A single implied-return marker needs one premium; the median of the 2-3 aggregator quotes is robust to a lone outlier and reuses the cached GmpRecord the quiet GMP block already reads (no new source, no model coupling).
- **`issue_price=None` today (honest GMP-marker omission).** No structured per-share issue price exists in `SnapshotRecord`; `_issue_price_for(record)` documents this and returns None, so the GMP marker + gap line are honestly omitted (the band still renders with the no-gap note). The full GMP path is exercised in the render tests with a synthetic issue price and lights up unchanged once a real issue price lands.
- **`format_inr` used only for an invisible provenance `title=`.** The locked Typography rule forbids ₹ in the visible forecast chrome (returns in %, errors in points). To honor the plan's "route ₹ inputs through `format_inr`" while keeping the chrome ₹-free, the ₹ basis of the GMP conversion is rendered only as a native `title=` hover tooltip on the marker — honest provenance, off the visible % layout.
- **Empty/error states centralized in `ui.forecast_block`.** `render_forecast_not_covered` / `render_forecast_error` keep all five render states in one testable module; the page helper only dispatches.
- **UI-03/FCAST-04/GMP-03 kept Pending.** Their render-halves are delivered, but the displayed numbers are 05-01 seed fixtures; per the project's honesty posture (05-03 kept FCAST-02 pending), they stay Pending in REQUIREMENTS.md until the real walk-forward records land (05-06/05-11). FCAST-01 (already Complete from 05-01) is the only requirement carried on this plan's frontmatter that is legitimately complete.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical / honesty] Issue price unavailable → GMP marker honestly omitted**
- **Found during:** Task 3 (page wiring)
- **Issue:** The plan directs passing "the issue price sourced from the already-loaded snapshot metadata," but `SnapshotRecord` surfaces no structured per-share issue-price field (the metadata field is a cited `GroundedAnswer`, not a parsed price). Fabricating or regex-scraping a price from prose would violate the honesty invariant.
- **Fix:** Added `_issue_price_for(record)` returning `None` (documented), which drives the render's first-class no-gap state — the GMP marker + gap line are omitted, the band still renders, and the honest no-gap note is shown. The display-layer conversion is fully implemented and unit-tested with a synthetic issue price, so it activates with zero render change once a real issue price is surfaced (05-06/05-11).
- **Files modified:** `pages/02_snapshot.py`
- **Verification:** `test_covered_gmp_present_but_no_issue_price_omits_marker` + `test_covered_no_gmp_omits_marker_shows_honest_note` pass; full suite green.
- **Committed in:** `2bec4bc` (Task 3 commit)

**2. [Rule 2 - Missing critical] Centralized not-covered + error renderers in ui.forecast_block**
- **Found during:** Task 2 (render module)
- **Issue:** The plan's `render_forecast_block(record, gmp_record, issue_price)` signature covers only the record-present states; the not-covered (no record) and error states still need a rendered surface, and the render-state test asks for all five states.
- **Fix:** Added `render_forecast_not_covered()` (heading + `.drhp-not-disclosed` note) and `render_forecast_error()` (amber `.drhp-refusal`) to the same module so the states are testable in one place; the page's `_render_forecast_block` dispatcher calls them for `missing`/`error`.
- **Files modified:** `ui/forecast_block.py`, `pages/02_snapshot.py`
- **Verification:** `test_not_covered_renders_honest_note_no_band` + `test_error_renders_amber_refusal_not_red` pass.
- **Committed in:** `556b1fe` (Task 2) + `2bec4bc` (Task 3)

---

**Total deviations:** 2 auto-fixed (both Rule 2 — required for honest, correct operation). **Impact on plan:** none to scope — both keep the render faithful to the locked honesty invariant (absence shown as absence) and to the plan's own five-state matrix. No new dependencies; the render imports no model module.

## Known Stubs
- **`_issue_price_for(record)` returns `None`** (`pages/02_snapshot.py`) — an intentional, documented honest stub: no structured per-share issue price is surfaced by `SnapshotRecord` yet, so the GMP marker is honestly omitted (band still renders, no-gap note shown — never a fabricated GMP). Resolved when a real issue price lands (05-06/05-11); the display-layer conversion + full GMP render path are already implemented and unit-tested.
- **The block renders from the 05-01 hand-seeded ForecastRecords** (a phase-level CODE-NOW-DEFER decision, not this plan's stub) — swiggy full-render + hyundai abstain; the real walk-forward records arrive in 05-06/05-11.

## Issues Encountered
- **Copy strings with apostrophes are html-escaped at render** (`isn't` → `isn&#x27;t`, `couldn't` → `couldn&#x27;t`): the render-state assertions were adjusted to compare `html.escape(...)` forms for the abstain / error / not-covered notes. Not a defect — escaping every string is the T-05-07-XSS mitigation.
- **Pre-existing (out of scope):** `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` still fails (`sentence-transformers is not installed`) — the documented ignorable embedder failure, unchanged by this plan.

## User Setup Required
None — no external service configuration required. Pure offline render code over cached JSON.

## Next Phase Readiness
- The phase's headline UI is live and offline-green against the seed fixtures — 05-06 (precompute writer) and 05-11 (real walk-forward run + on-device human-verify checkpoint) can regenerate `data/forecasts/*.json` and the section renders the real band/GMP-gap/metrics with no render change.
- The 05-03 two-direction isolation audit's forward check against `ui.forecast_block` is now ACTIVE and green; the last two importorskip-guarded checks (`pipelines.forecast.model` / `walkforward`) auto-execute once 05-05 lands.
- **UI-03 / FCAST-04 / GMP-03 remain Pending** in REQUIREMENTS.md (render-halves delivered, real-data completion at 05-06/05-11). **FCAST-02** stays Pending (05-04 feature-leakage half + this render half delivered; close it only when the model half lands). The on-device 375px/mobile visual is a 05-11 checkpoint (this offline executor cannot run Streamlit).

## Self-Check: PASSED

- Created files verified on disk: `ui/forecast_block.py`, `tests/unit/test_forecast_block_render.py` — FOUND. Modified: `ui/copy.py`, `app/static/drhplens.css`, `pages/02_snapshot.py` — FOUND.
- Task commits verified in git log: `bcb1a62` FOUND, `556b1fe` FOUND, `2bec4bc` FOUND.
- Plan verification re-run: `pytest tests/unit -q` → 417 passed, 2 skipped, 1 pre-existing embedder failure; `import ui.copy` clean; `.drhp-forecast-band` present in CSS; `inspect.getsource(ui.forecast_block)` contains none of the forbidden model tokens; wiring order asserts peer < forecast < ranked-risks and GMP last.

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-19*
