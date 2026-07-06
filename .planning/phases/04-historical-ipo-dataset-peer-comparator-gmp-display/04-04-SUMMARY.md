---
phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
plan: 04
subsystem: pipelines
tags: [gmp, grey-market-premium, pydantic, requests-cache, beautifulsoup4, tenacity, isolation-audit, typer]

# Dependency graph
requires:
  - phase: 04-01
    provides: catalogue allow-list (is_known_drhp_id), data/<kind>/<id>.json cache spine, yfinance/source validation
provides:
  - "GmpRecord/GmpQuote schema (agent/gmp_schema.py) capturing 2-3 aggregator quotes with a derived spread"
  - "Absent-GMP (quotes==[]) and single-source GMP as first-class committed states"
  - "pipelines/gmp.py: allow-list-gated load_gmp/precompute_gmp + Typer CLI, per-source failure isolation"
  - "pipelines/gmp_sources.py: 3 hard-coded-host aggregator scrapers (SSRF-controlled, monkeypatched in CI)"
  - "GMP-02 isolation import-audit test (tests/unit/test_gmp_isolation.py) over both GMP modules"
  - "Two seed fixtures: swiggy_2024_11 (absent) + hyundai_2024_10 (synthetic 3-source spread)"
affects: [04-06 GMP renderer, Phase 5 prediction reverse-leakage audit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GMP module-isolation import-audit (inspect.getsource substring pin) — mirrors Phase 3 test_no_llm_or_qdrant_import"
    - "Absent-signal-as-first-class-state (quotes==[]) rather than error/edge case"
    - "Multi-source quotes kept SEPARATE to preserve divergence (D4-01), spread derived on demand"

key-files:
  created:
    - agent/gmp_schema.py
    - pipelines/gmp_sources.py
    - pipelines/gmp.py
    - data/gmp/swiggy_2024_11.json
    - data/gmp/hyundai_2024_10.json
    - tests/unit/test_gmp_schema.py
    - tests/unit/test_gmp_isolation.py
    - tests/unit/test_gmp_precompute.py
  modified: []

key-decisions:
  - "spread() derived on demand (not stored): a pure function of committed quotes, keeps the cache minimal + diff-reviewable"
  - "spread() returns None for <2 quotes (absent AND single-source) — a cross-source check needs >= 2 sources"
  - "agent/gmp_schema.py imports ONLY pydantic + stdlib (no agent.schemas) — absent state is quotes==[], no RefusalResponse needed"
  - "3 aggregators: investorgain / ipowatch / ipocentral, all hard-coded hosts (SSRF control T-04-04-SSRF)"

patterns-established:
  - "GMP-02 isolation pin: inspect.getsource substring audit forbidding xgboost/mapie/sklearn/forecast/pipelines.features/pipelines.historical/GRAPH.invoke"
  - "Per-source failure isolation in a scrape loop: one aggregator raising is logged + skipped, never fabricates a value"

requirements-completed: [GMP-01, GMP-02]

# Metrics
duration: ~20min
completed: 2026-07-06
---

# Phase 4 Plan 04: GMP Data Layer + Isolation Audit Summary

**Read-only, cache-only grey-market-premium data layer — GmpRecord preserving 2-3 aggregator quotes and their spread, with absent-GMP and single-source as first-class states, pinned computationally isolated from any prediction pipeline by an inspect.getsource import-audit.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-06
- **Completed:** 2026-07-06
- **Tasks:** 2
- **Files created:** 8

## Accomplishments
- `GmpRecord`/`GmpQuote`/`GmpSpread` schema: separate per-aggregator quotes so their disagreement (D4-01) is preserved; `spread()` derives low/high/n over >= 2 quotes, `None` otherwise.
- Absent-GMP (`quotes == []`) and single-source (`len == 1`) are first-class committed states — never a fabricated number, never a zero.
- `pipelines/gmp.py` mirrors `redflag.py`'s allow-list path-gate (`_gmp_path` → `is_known_drhp_id` before path formation) + Typer `precompute-one`/`precompute-all`, WITHOUT the agent graph.
- `pipelines/gmp_sources.py`: three hard-coded-host aggregator scrapers (investorgain / ipowatch / ipocentral), lazy network-safe session, per-source honest degradation to `None`.
- GMP-02 isolation import-audit (`test_gmp_isolation.py`) over `agent.gmp_schema` + `pipelines.gmp` + `pipelines.gmp_sources` — forbids `xgboost`/`mapie`/`sklearn`/`forecast`/`pipelines.features`/`pipelines.historical`/`GRAPH.invoke`.
- Two committed seed fixtures unblock the 04-06 renderer offline: `swiggy_2024_11.json` (absent — the common already-listed case) and `hyundai_2024_10.json` (synthetic 3-source spread demo).

## Task Commits

Each task followed a RED → GREEN TDD posture:

1. **Task 1: GmpRecord schema + GMP-02 isolation audit**
   - `8ef2978` test(04-04): schema + isolation tests (RED)
   - `af26557` feat(04-04): GmpRecord/GmpQuote schema (GREEN)
2. **Task 2: aggregator scrapers + precompute/load + seeds**
   - `cb50d0a` test(04-04): precompute tests + isolation extension (RED)
   - `864e957` feat(04-04): gmp_sources.py + gmp.py + two seed fixtures (GREEN)

## Files Created/Modified
- `agent/gmp_schema.py` - GmpRecord/GmpQuote/GmpSpread; to_dict/from_dict/to_json; spread() + is_absent/is_single_source; imports only pydantic + stdlib.
- `pipelines/gmp_sources.py` - 3 hard-coded-host aggregator fetchers, lazy CachedSession, `source_fetchers()` registry (dynamically resolved so tests monkeypatch cleanly).
- `pipelines/gmp.py` - `load_gmp`/`_gmp_path` allow-list gate, `precompute_gmp(write=)` with per-source isolation, Typer CLI.
- `data/gmp/swiggy_2024_11.json` - absent-GMP seed (`quotes: []`).
- `data/gmp/hyundai_2024_10.json` - synthetic hand-seeded 3-source spread seed (25/67/50).
- `tests/unit/test_gmp_schema.py` - round-trip, spread math, absent + single-source states.
- `tests/unit/test_gmp_isolation.py` - the GMP-02 inspect.getsource substring audit.
- `tests/unit/test_gmp_precompute.py` - multi/single/absent/per-source-failure paths, path-gate, write=False, round-trip, both seeds.

## Decisions Made
- **spread() derived, not stored:** a pure function of the committed quotes — keeps the on-disk cache minimal and diff-reviewable.
- **`< 2` quotes → no spread:** both absent and single-source honestly report no cross-source check.
- **Schema imports only pydantic + stdlib:** the absent state is simply `quotes == []`; no `RefusalResponse` import was needed, keeping the isolation surface as tight as possible.
- **Absent-GMP is the COMMON case:** 7 of 8 catalogue IPOs are already listed, so no live grey-market premium exists — the empty record is the honest default, not an error path.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None. All forbidden isolation tokens (notably the word "forecast") were kept out of both GMP module sources so the substring audit passes over their own docstrings/comments.

## Known Stubs
- `pipelines/gmp_sources.py` live-fetch bodies (`_live_quote`, `_slugify`, `_parse_gmp`) are `# pragma: no cover` seams for the DEFERRED live scrape. This is intentional CODE-NOW-DEFER: no live network in CI; the actual open-IPO-window scrape is a deferred human runbook step. Not a blocking stub — the committed seed fixtures + monkeypatched tests fully exercise the data layer offline, and 04-06 reads only the cache.

## Deferred Live-Scrape Runbook Step
The real GMP scrape must be run manually during an OPEN IPO window (GMP legitimately exists only for not-yet-listed issues). Implement `_parse_gmp` per each aggregator's current markup, then `python -m pipelines.gmp precompute-one <open_ipo_drhp_id>`. For the 8 catalogue IPOs (all already listed) the honest result is an absent record; the hyundai seed is a clearly-flagged synthetic demo for the spread visual only.

## Test Results
- Plan tests: `tests/unit/test_gmp_schema.py tests/unit/test_gmp_isolation.py tests/unit/test_gmp_precompute.py` → **19 passed**.
- Whole unit suite: **360 passed, 1 failed** — the single failure is the pre-existing, explicitly-ignored `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` (sentence-transformers not installed). No other regression (baseline was 341 passed + that same ignored failure).
- `load_gmp('swiggy_2024_11').quotes` = 0 (absent); `load_gmp('hyundai_2024_10').quotes` = 3 (spread).

## Next Phase Readiness
The GMP data layer is ready for the 04-06 renderer: both offline states (absent + multi-source spread) are exercisable via committed seeds, the spread is derivable, and the isolation invariant is pinned. Phase 5 owns the reverse audit (the predictor must not import `pipelines.gmp`).

## Self-Check: PASSED
All 8 plan artifacts + SUMMARY exist on disk; all 4 task commits (`8ef2978`, `af26557`, `cb50d0a`, `864e957`) present in git history.

---
*Phase: 04-historical-ipo-dataset-peer-comparator-gmp-display*
*Completed: 2026-07-06*
