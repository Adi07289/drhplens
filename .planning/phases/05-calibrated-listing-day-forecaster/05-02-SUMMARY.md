---
phase: 05-calibrated-listing-day-forecaster
plan: 02
subsystem: infra
tags: [survivorship, nse, sebi, chittorgarh, ssrf, requests-cache, pandas, pytest, historical-panel, data-pipeline]

# Dependency graph
requires:
  - phase: 04-historical-ipo-dataset-peer-comparator-gmp
    provides: "pipelines.historical panel schema (PANEL_COLUMNS/STATUS_VALUES/assemble_panel), typed coercers (coerce_price/coerce_date/normalize_status), SSRF allow-list + cached polite session, validate.sanity_check_median (>20%-median survivor-inflation flag)"
  - phase: 05-calibrated-listing-day-forecaster
    provides: "05-01 modeling stack + shared offline fixtures (this plan needs none of it, but shares the wave)"
provides:
  - "pipelines.historical.sources.fetch_nse_past_issues (Source A, listed core) — NSE public-past-issues via _get()->_check_host; nse-lib preferred lazily, cookie-primed GET fallback; raw JSON snapshotted (A1)"
  - "pipelines.historical.sources.fetch_sebi_withdrawn (Source B, P3 withdrawn/pulled overlay) = SEBI public-issues filings + chittorgarh withdrawn report 202"
  - "www.nseindia.com added to ALLOWED_HOSTS (SSRF); _get gains query params; _STATUS_ALIASES extended for SEBI/withdrawn wording"
  - "build.build_panel two-source merge + _merge_sources dedupe by (issuer, issue_date) with listed-core-wins collision rule; non-zero-row guard on the live build CLI (Pitfall 7)"
  - "Offline monkeypatched survivorship merge test + nightly live-NSE integration canary (tests/integration/test_nse_past_issues.py) wired into nightly-nse.yml"
affects: [05-03, 05-04, 05-05, 05-06, 05-09, 05-10, 05-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-source survivorship merge: listed-core ∪ withdrawn overlay, deduped by (issuer, issue_date), listed-core wins collisions, withdrawn survives when overlay-only (P3)"
    - "CODE-NOW-DEFER live fetchers proven OFFLINE via monkeypatched source seams (no real network under pytest); live crawl gated to the 05-11 checkpoint"
    - "Raw-payload snapshot (save-raw, A1) before parsing unconfirmed NSE/SEBI field names"

key-files:
  created:
    - tests/integration/test_nse_past_issues.py
  modified:
    - pipelines/historical/sources.py
    - pipelines/historical/build.py
    - tests/unit/test_historical_panel.py
    - .github/workflows/nightly-nse.yml

key-decisions:
  - "FCAST-03 NOT marked complete: it spans 5 Phase-5 plans (05-02/05-05/05-09/05-10/05-11) and explicitly requires walk-forward CV; this plan delivers only the survivorship-universe half (the SEBI/issuer-side merge). Left Pending honestly."
  - "The dead chittorgarh HTML scraper (fetch_chittorgarh_index) is kept but DEMOTED to optional enrichment (D5-04); build_panel no longer calls it as the primary listed-core path"
  - "The `nse` library is imported lazily and is optional (gated behind the 05-11 human-verify checkpoint, T-05-02-SC); the hand-rolled cookie-primed _get fallback keeps the nightly canary runnable without installing nse"
  - "Merge collision rule: listed-core row wins (keeps its listing price + status — a company that actually listed is not 'withdrawn'); a withdrawn overlay row survives only when its issuer is absent from the listed core"

patterns-established:
  - "Per-source failure-isolated two-source merge (one flaky feed never aborts the batch, P14)"
  - "Nightly integration canary: @pytest.mark.integration + NSE_LIVE_SMOKE gate, deselected from the quick unit loop, wired into nightly-nse.yml"

requirements-completed: []

# Metrics
duration: ~15 min
completed: 2026-07-16
---

# Phase 5 Plan 02: Survivorship-Safe Two-Source Universe Merge Summary

**Repointed the historical universe assembler off the dead chittorgarh HTML scraper onto a survivorship-safe two-source merge — NSE `public-past-issues` (Source A, listed core) ∪ SEBI/chittorgarh-withdrawn overlay (Source B, the P3 control) — deduped by (issuer, issue_date), reusing the existing panel schema/validator/coercers/SSRF allow-list/cached session verbatim and proven OFFLINE with monkeypatched fetchers.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-16T18:09Z
- **Completed:** 2026-07-16T18:24Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments
- Added `fetch_nse_past_issues` (Source A) and `fetch_sebi_withdrawn` (Source B, the P3 withdrawn/pulled overlay) to `sources.py`, both `# pragma: no cover - live only`, both routing every fetch through `_get()` → `_check_host` (no bare `requests.get`), every parsed field through the existing typed coercers, with the raw payload snapshotted before parsing (A1).
- Extended `ALLOWED_HOSTS` with `www.nseindia.com` (SSRF T-05-02-SSRF) while keeping the SEBI + chittorgarh + nsearchives hosts; extended `_STATUS_ALIASES` for SEBI/withdrawn wording; added an optional `params` kwarg to `_get` so dates pass as query params (no URL derived from an argument).
- Demoted `fetch_chittorgarh_index` from the primary listed-core path to optional enrichment (D5-04) — kept, but no longer called first by `build_panel`.
- Rewired `build_panel` to a per-source-isolated two-source merge with `_merge_sources` deduping by `(issuer, issue_date)` (listed-core wins collisions; withdrawn survives when overlay-only), and added a non-zero-row guard to the live `build` CLI (Pitfall 7 — a silent 0-row build is the 04-07 failure mode).
- Extended `tests/unit/test_historical_panel.py` with an offline monkeypatched merge test asserting non-zero `withdrawn` + a real `listed_alive`/`delisted` mix, dedupe collapse of the duplicate issuer, and a retained NaN-return row; added a nightly live-NSE integration canary and wired it into `nightly-nse.yml`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Two survivorship-safe source fetchers + SSRF allow-list extension** — `a415400` (feat)
2. **Task 2: Two-source merge + dedupe in build.py + offline survivorship test** — `c8b75e6` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified
- `pipelines/historical/sources.py` — +`www.nseindia.com` in `ALLOWED_HOSTS`; new URL constants (NSE past-issues/home, SEBI public-issues, chittorgarh withdrawn 202); `fetch_nse_past_issues` + `_fetch_nse_past_issues_payload` + `_parse_nse_past_issue`; `fetch_sebi_withdrawn` + repurposed `fetch_sebi_offer_documents` + `_fetch_chittorgarh_withdrawn`; `_save_raw` (A1); `_get(params=...)`; extended `_STATUS_ALIASES`; demoted `fetch_chittorgarh_index` docstring; updated `__all__`.
- `pipelines/historical/build.py` — `_row_key` + `_merge_sources`; `build_panel` two-source merge (Source A/B each failure-isolated); non-zero-row guard added to `build_cli`.
- `tests/unit/test_historical_panel.py` — `import datetime`; offline two-source-merge test with monkeypatched fetchers and a guard that the primary chittorgarh path is not called.
- `tests/integration/test_nse_past_issues.py` (NEW) — nightly `@pytest.mark.integration` live-NSE `public-past-issues` canary, `NSE_LIVE_SMOKE`-gated, deselected from `pytest tests/unit -q`.
- `.github/workflows/nightly-nse.yml` — added the new test to the nightly run list and `tenacity` to the install step (the `_get` retry path the NSE fallback needs).

## Decisions Made
- **FCAST-03 left Pending (not marked complete).** FCAST-03 ("walk-forward CV on a survivorship-eliminated SEBI/issuer-side universe") is claimed by five Phase-5 plans (05-02/05-05/05-09/05-10/05-11). This plan delivers only the survivorship-universe half; the walk-forward CV half is built later. Marking it complete now would be dishonest (project honesty invariant), so it stays Pending in REQUIREMENTS.md.
- **chittorgarh demoted, not deleted (D5-04).** `fetch_chittorgarh_index` is retained as optional enrichment/cross-check for a future JSON-API rewrite, but is no longer the primary listed-core path.
- **`nse` library stays optional/lazy (T-05-02-SC).** It is imported inside the function and NOT installed here (gated behind the 05-11 human-verify checkpoint); the hand-rolled cookie-primed `_get` fallback keeps the nightly canary and the live build runnable without it.
- **Merge collision rule = listed-core wins.** On an (issuer, issue_date) collision the listed-core row keeps its listing price + status; a withdrawn overlay row survives only when its issuer is absent from the listed core — that is exactly the P3 control the survivor-only feeds drop.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Wired the nightly NSE integration test into `nightly-nse.yml` (+`tenacity`)**
- **Found during:** Task 2 (integration test)
- **Issue:** The plan's must_have truth is "A nightly integration test CAN hit the live NSE past-issues endpoint." The existing `nightly-nse.yml` invokes an explicit file list, so a new test file marked `integration` would never actually run nightly — the truth would be nominal, not operational. The job's pip install also lacked `tenacity`, which the `_get` retry decorator (the NSE cookie-primed fallback path) imports.
- **Fix:** Added `tests/integration/test_nse_past_issues.py` to the nightly run list and `tenacity` to the install step. Did NOT add the `nse` library to CI (it is gated behind the 05-11 human-verify checkpoint, T-05-02-SC) — the fallback path runs without it.
- **Files modified:** `.github/workflows/nightly-nse.yml`
- **Verification:** The new test collects under `-m integration`, is `NSE_LIVE_SMOKE`-gated (skips offline), and is deselected from `pytest tests/unit -q` (0 collected there).
- **Committed in:** `c8b75e6` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing-critical). **Impact on plan:** Necessary to make the plan's nightly-integration must_have operationally real. No scope creep beyond the CI wiring the truth requires; no `nse` dependency added to CI (respects the 05-11 checkpoint gate).

## Issues Encountered
- **Pre-existing (out of scope):** `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` fails with `RuntimeError: sentence-transformers is not installed` — the documented, ignorable embedder failure (sentence-transformers absent from this venv), unrelated to this plan. Not a regression: the suite went 375 passed → 376 passed (+1 new merge test), same single embedder failure throughout.
- **ruff not installed in `.venv` / no pre-commit config:** lint could not be run locally and no git hooks fire. Code follows the file's existing ruff conventions (line length, `# noqa: BLE001` per-source/per-row isolation, deferred imports); a follow-up `ruff check` in a fuller env is advisable but nothing here introduces obvious violations.

## User Setup Required
None - no external service configuration required. The live crawl (NSE/SEBI/chittorgarh egress + the optional `nse` library) remains a DEFERRED seam gated to the 05-11 human-verify checkpoint; nothing must be configured to land this plan.

## Next Phase Readiness
- The survivorship-safe universe merge is implemented and offline-proven (FCAST-03/P3 data half). Downstream modeling slices (05-04 features, 05-05 walk-forward) can build the feature matrix off `build_panel`'s two-source output once the live panel is materialized at the 05-11 checkpoint; until then the 05-01 synthetic fixture covers the tests.
- Carry-over (does NOT block Phase 5 code): the actual live panel build (real ~200–300-row universe) is still a deferred network step — run it at the 05-11 checkpoint (needs NSE/SEBI egress and, ideally, the human-verified `nse` library). The nightly canary now watches the NSE past-issues endpoint for drift.
- FCAST-03 remains Pending in REQUIREMENTS.md (walk-forward CV half outstanding) — do not close it until the later Phase-5 plans land.

## Self-Check: PASSED

- Created file verified on disk: `tests/integration/test_nse_past_issues.py` — FOUND.
- Task commits verified in git log: `a415400` FOUND, `c8b75e6` FOUND.
- Plan verification re-run: `pytest tests/unit/test_historical_panel.py -q` → 13 passed; `www.nseindia.com in ALLOWED_HOSTS` → True; module imports do no network (offline suite 376 passed / 1 pre-existing embedder failure); the NSE integration test is deselected from `tests/unit -q` (0 collected) and skips cleanly offline.

---
*Phase: 05-calibrated-listing-day-forecaster*
*Completed: 2026-07-16*
