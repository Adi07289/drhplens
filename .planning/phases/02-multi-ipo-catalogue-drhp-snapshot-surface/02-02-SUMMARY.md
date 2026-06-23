---
phase: 02-multi-ipo-catalogue-drhp-snapshot-surface
plan: 02
subsystem: api
tags: [langgraph, pydantic, qdrant, multi-tenant-filter, allow-list]

# Dependency graph
requires:
  - phase: 02-01
    provides: catalogue.json schema stub (Swiggy row), xfail test stubs for Wave 1
provides:
  - drhp_id threaded through GraphState -> intake -> retrieve -> refuse_with_reformulation
  - data/catalogue_loader.py (load_catalogue, is_known_drhp_id) — the V5 allow-list control
  - 8-IPO data/catalogue.json (Swiggy, Hyundai, Ola Electric, Zomato, Nykaa, Paytm, LIC, Honasa)
affects: [02-03-ingest-generalization, 02-04-snapshot-precompute, 02-05-ui-catalogue-snapshot]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "drhp_id flows GraphState -> intake (default-preserving) -> retrieve/refuse (state-read) -> storage.vector.search"
    - "Allow-list-before-search: is_known_drhp_id() gates every drhp_id before it can become a Qdrant filter value (V5)"
    - "lru_cache-backed catalogue loader for repo-committed trusted config"

key-files:
  created:
    - data/catalogue_loader.py
  modified:
    - agent/state.py
    - agent/nodes/intake.py
    - agent/nodes/retrieve.py
    - agent/nodes/refuse_with_reformulation.py
    - data/catalogue.json
    - tests/unit/test_drhp_id_threading.py
    - tests/unit/test_catalogue.py
    - tests/unit/test_drhp_id_allowlist.py

key-decisions:
  - "intake.run defaults state['drhp_id'] to DRHP_ID_DEFAULT only when absent/falsy — preserves every Phase 1 call shape unchanged"
  - "retrieve.run validates drhp_id against the catalogue allow-list before calling search(); unknown ids short-circuit to an infrastructure_error RefusalResponse with empty retrieved_chunks, never reaching Qdrant"
  - "catalogue.json populated with catalogue-level metadata only (no fabricated price bands/financials); source_sha256 stays null until Wave 2 ingest pins it"

patterns-established:
  - "Pattern 1 (RESEARCH): drhp_id threaded through GraphState as a back-compat-preserving default, not a required caller argument"
  - "V5 allow-list gate sits inside the retrieve node, before the search() call, not at the UI layer — defense at the boundary closest to the trust violation"

requirements-completed: [SNAP-01, OPS-01]

duration: 35min
completed: 2026-06-23
---

# Phase 2 Plan 02: drhp_id Threading + Catalogue Allow-List + 8-IPO Catalogue Summary

**Threaded `drhp_id` through GraphState/intake/retrieve/refuse with a back-compat-preserving default, shipped a Pydantic-validated catalogue loader with the V5 allow-list gate, and filled `data/catalogue.json` with all 8 curated IPOs.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-23 (Wave 1 of Phase 2)
- **Completed:** 2026-06-23T18:42Z
- **Tasks:** 2/2 completed
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments
- `drhp_id` is now a first-class `GraphState` key; omitting it still defaults to `DRHP_ID_DEFAULT` (`swiggy_2024_11`), so every Phase 1 invocation shape keeps working unchanged.
- `data/catalogue_loader.py` validates `data/catalogue.json` via a Pydantic `CatalogueIPO` model and exposes `is_known_drhp_id()` — the V5 control that gates `drhp_id` before it can reach the Qdrant filter in `storage.vector.search()`.
- `agent/nodes/retrieve.py` now refuses (with an `infrastructure_error` `RefusalResponse`) on an unknown `drhp_id` *before* calling `search()` — verified by a test that makes `search()` raise if invoked.
- `data/catalogue.json` now lists all 8 curated IPOs (Swiggy, Hyundai Motor India, Ola Electric, Zomato, Nykaa, Paytm, LIC, Honasa/Mamaearth) with catalogue-level metadata sourced from `02-RESEARCH.md`'s confirmed SEBI source list — no fabricated financials.

## Task Commits

Each task was committed atomically:

1. **Task 1: Thread drhp_id through GraphState + intake + retrieve + refuse** - `29cc06b` (feat)
2. **Task 2: Catalogue loader + drhp_id allow-list (V5) + 8-IPO catalogue.json** - `1536a43` (feat)

## Files Created/Modified
- `agent/state.py` - Added `drhp_id: str` to `GraphState` TypedDict with docstring note
- `agent/nodes/intake.py` - Defaults `state["drhp_id"]` to `DRHP_ID_DEFAULT` when absent/falsy
- `agent/nodes/retrieve.py` - Reads `drhp_id` from state; added the V5 allow-list guard before `search()`
- `agent/nodes/refuse_with_reformulation.py` - `search_relaxed` call now reads `state.get("drhp_id") or DRHP_ID_DEFAULT`
- `data/catalogue_loader.py` - New: `CatalogueIPO` Pydantic model, `load_catalogue()`, `is_known_drhp_id()`
- `data/catalogue.json` - Added 7 IPOs (Hyundai, Ola Electric, Zomato, Nykaa, Paytm, LIC, Honasa) alongside the existing Swiggy row
- `tests/unit/test_drhp_id_threading.py` - Flipped xfail stub to 5 real tests (explicit drhp_id routing, back-compat default, intake propagation/default, refuse-node state read)
- `tests/unit/test_catalogue.py` - Flipped xfail stub to 2 real tests (schema validation, exact 8-IPO membership)
- `tests/unit/test_drhp_id_allowlist.py` - Flipped xfail stub to 4 real tests (known id accepted, injection rejected, unknown rejected, retrieve refuses before search)

## Decisions Made
- Used `state.get("drhp_id") or DRHP_ID_DEFAULT` (not `state["drhp_id"]`) in `retrieve.run` and `refuse_with_reformulation.run` as a defensive fallback for any caller that bypasses `intake` (e.g., tests invoking the node directly) — slightly more defensive than the plan's literal `state["drhp_id"]`, with identical behavior for the documented call paths since `intake` always populates the key.
- Placed the V5 allow-list guard inside `retrieve.run` (not as a separate graph node) per the plan's `key_links` pattern (`is_known_drhp_id` referenced directly in `retrieve.py`) — keeps the mitigation co-located with the boundary it protects.
- `issue_size_cr` left as a best-known integer per IPO from public reporting (no source citation required at the catalogue-metadata layer per D2: "hand-curated is fine"); `fresh_vs_ofs` stays `null` for every row per the existing Wave 0 convention — the real OFS/fresh split lives in the Wave 3 snapshot pipeline output, not this catalogue field.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their `<action>` blocks; no architectural changes, no new dependencies, no blocking issues encountered.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. This plan is pure code + repo-committed data; no API keys or live Qdrant needed for execution or verification.

## Next Phase Readiness

- `drhp_id` is fully threaded and allow-list-gated; Wave 2 (02-03, ingest generalization) can now parameterize `pipelines/ingest_swiggy.py` -> `pipelines/ingest.py(drhp_id, pdf_path)` and loop it over `data/catalogue.json`'s 8 entries.
- `data/catalogue_loader.py` is ready for the Wave 4 Streamlit catalogue/snapshot pages to import directly (`load_catalogue()` for the browse grid, `is_known_drhp_id()` if the UI ever needs to validate a query-param `drhp_id`).
- `source_sha256: null` and `snapshot_path` (unwritten files) for the 7 new IPOs are expected nulls/placeholders, not stubs blocking this plan's goal — Wave 2 ingest pins the SHA; Wave 3 (02-04) writes the snapshot JSON files. This plan's goal (threading + allow-list + catalogue schema) is fully achieved without them.
- No blockers. SNAP-01 and OPS-01 requirements are **enabled, not finished** — full satisfaction requires the remaining 7 IPOs to actually be ingested into Qdrant and have snapshots rendered (Waves 2-4), per the plan's explicit instruction not to mark SNAP requirements "Complete" yet.

## Self-Check: PASSED

All created/modified files verified present on disk; both task commits (`29cc06b`, `1536a43`) verified present in git log.

---
*Phase: 02-multi-ipo-catalogue-drhp-snapshot-surface*
*Completed: 2026-06-23*
