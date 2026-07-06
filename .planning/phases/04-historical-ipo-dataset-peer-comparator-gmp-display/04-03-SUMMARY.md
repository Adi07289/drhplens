---
phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
plan: 03
subsystem: pipelines
tags: [peer-comparator, pydantic, yfinance, screener, rapidfuzz, requests-cache, union-discriminator-codec, precompute-cache]

requires:
  - phase: 04-01
    provides: yfinance==1.5.1 + requests-cache + jugaad-data pinned; validated .info peer-multiple keys (trailingPE/priceToBook/enterpriseToEbitda/returnOnEquity; ROE is a fraction)
  - phase: 03
    provides: redflag_schema union-discriminator codec + redflag.py precompute/load/allow-list rails to mirror
provides:
  - PeerRecord/PeerCompany/PeerMetric/PeerCell schema with per-cell source+as_of provenance (current + drhp_date dimensions) and the {refusal} union codec
  - pipelines/peer_sources.py source-priority ladder (screener s -> yfinance y -> NSE n) with honest missing/NM handling
  - pipelines/peers.py precompute_peers + load_peers + is_known_drhp_id allow-list gate + Typer CLI
  - pipelines/peer_queries.py PEER_SET_QUERY canned DRHP peer-SET query
  - hand-seeded data/peers/swiggy_2024_11.json (offline renderer fixture, CODE-NOW-DEFER)
affects: [04-05 peer table renderer, 04-04 GMP display, 05 forecaster peer features]

tech-stack:
  added: []
  patterns:
    - "Per-cell provenance across TWO as-of dimensions (current + drhp_date), each labelled with its source flag"
    - "Source-priority ladder returning first-available cell + honest '—' (None) / NM sentinel"
    - "CODE-NOW-DEFER: monkeypatched sources + hand-seeded cache; live scrape deferred to runbook"

key-files:
  created:
    - agent/peer_schema.py
    - pipelines/peer_queries.py
    - pipelines/peer_sources.py
    - pipelines/peers.py
    - data/peers/swiggy_2024_11.json
    - tests/unit/test_peer_schema.py
    - tests/unit/test_peer_sources.py
    - tests/unit/test_peers_precompute.py
  modified: []

key-decisions:
  - "PeerCell adds a not_meaningful boolean sentinel so a negative/undefined P/E renders NM (value None) — distinct from a missing cell (value None, not_meaningful False)"
  - "0/None/NaN coerced to missing for all ratios (P15); negative ROE kept as a real value; only P/E negative -> NM"
  - "yfinance returnOnEquity (fraction) stored ×100 as percent so screener + yfinance ROE share units"
  - "peer-name -> ticker via rapidfuzz against a hand-curated allow-list; unknown name -> no ticker (no wrong guess), keeping SSRF hosts hard-coded"
  - "Refusal peer_set -> companies == [] (D4-06 honest empty-state; never a fabricated peer set)"

patterns-established:
  - "PeerRecord.to_dict/from_dict reuse the {refusal} discriminator verbatim from redflag_schema for the peer_set value"
  - "resolve_multiples is precompute-time only; import is network-safe (lazy session/yfinance)"

requirements-completed: [PEER-01, PEER-02]

duration: 40min
completed: 2026-07-06
---

# Phase 4 Plan 03: Peer Comparator Data Layer Summary

**PeerRecord schema + a screener→yfinance→NSE source-priority ladder + an allow-list-gated precompute/load pipeline that gathers the DRHP's own cited listed peers and their market multiples with honest per-cell (value, source, as-of) provenance — never a fabricated peer or number.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-07-06T00:00:00Z
- **Completed:** 2026-07-06
- **Tasks:** 3 (all TDD: RED → GREEN)
- **Files modified:** 8 created

## Accomplishments

- `agent/peer_schema.py` — `PeerRecord(drhp_id, computed_at, peer_set, companies, as_of)` mirroring `RedFlagRecord`. `peer_set` is `GroundedAnswer | RefusalResponse` via the verbatim `{"refusal": ...}` discriminator codec (D4-06 empty-state IS a `RefusalResponse`). Each `(company, metric)` is a `PeerMetric` carrying a `current` cell (primary) and an optional `drhp_date` cell (BOTH dimensions where available). Each `PeerCell(value, source, as_of, not_meaningful)` records the D4-05 source flag (`s`/`y`/`n`/`d`) and as-of dimension; a fully-missing cell is `PeerCell()` → `—`; a negative/undefined P/E carries the `not_meaningful` NM sentinel. Locked `PEER_METRIC_KEYS` frozenset + rejecting `field_validator`; `GroundedAnswer`/`RefusalResponse` imported (never redefined) from `agent/schemas.py`.
- `pipelines/peer_sources.py` — the D4-05 ladder: `resolve_multiples` fetches each source once (`screener_multiples` → `yfinance_multiples` → `nse_multiples`) and picks the first-available value per cell, recording its source flag. `_clean_ratio` coerces 0/None/NaN → missing (P15); `returnOnEquity` fraction → percent (×100). `rapidfuzz` name→ticker allow-list; only hard-coded source hosts (SSRF control); import is network-safe (lazy `requests-cache` session + lazy `yfinance`).
- `pipelines/peers.py` — `precompute_peers` runs the canned `PEER_SET_QUERY` once through the existing `agent.graph.GRAPH` (PEER-01, no new LLM path), stores the cited `GroundedAnswer` as `peer_set`, loops named peers + the IPO's own row through the ladder (PEER-02), and stores a `RefusalResponse` honest empty-state (companies `[]`) when the DRHP names no peers. `load_peers`/`_peers_path` gate `drhp_id` through `is_known_drhp_id` before path formation (T-04-03-PATH). Typer `precompute-one`/`precompute-all` with per-IPO failure isolation (P14).
- `pipelines/peer_queries.py` — `PEER_SET_QUERY` canned "Comparison with Listed Industry Peers / Basis for Issue Price" query.
- `data/peers/swiggy_2024_11.json` — hand-seeded PeerRecord: DRHP-cited peer set (Zomato Limited, page 118), the IPO's own row with BOTH current + drhp_date cells (P/E as NM for the loss-making issuer), one honest `—` cell (Swiggy EV/EBITDA), and Zomato's current-market multiples. Unblocks the 04-05 renderer offline.

## Task Commits

1. **Task 1: PeerRecord schema** — `a2fa89f` (test) → `01aa024` (feat)
2. **Task 2: peer_queries + peer_sources ladder** — `05c7fe1` (test) → `3786dd9` (feat)
3. **Task 3: peers precompute + load + gate + seed** — `9be37d1` (test) → `cb084a1` (feat)

**Plan metadata:** (final docs commit — this SUMMARY + STATE + ROADMAP)

## Files Created/Modified

- `agent/peer_schema.py` — PeerRecord/PeerCompany/PeerMetric/PeerCell + `{refusal}` codec + locked metric-key validator
- `pipelines/peer_queries.py` — PEER_SET_QUERY constant
- `pipelines/peer_sources.py` — source-priority ladder + per-cell provenance + coercion + rapidfuzz ticker match
- `pipelines/peers.py` — precompute_peers/load_peers + allow-list gate + Typer CLI
- `data/peers/swiggy_2024_11.json` — seed peer cache fixture
- `tests/unit/test_peer_schema.py` — round-trip, refusal codec, missing/NM cells, key/source rejection (7 tests)
- `tests/unit/test_peer_sources.py` — ladder order, missing→None, 0-coercion, ROE %, NM, SSRF (12 tests)
- `tests/unit/test_peers_precompute.py` — grounded/refusal states, path gate, seed load, round-trip, isolation (8 tests)

## Decisions Made

- **`not_meaningful` sentinel on `PeerCell`** for negative/undefined P/E — the schema's chosen encoding for the plan's "sentinel distinguishable for the NM render". Keeps `value` None (never a misleading number) while recording which source reported it.
- **ROE stored as percent** (yfinance fraction ×100) so screener and yfinance ROE share units and the renderer just appends `%`.
- **Unknown peer name → no ticker** (rapidfuzz `score_cutoff`), so an unresolved name honestly skips the yfinance rung rather than guessing a wrong symbol — also keeps the SSRF host set hard-coded.
- **NSE/BSE rung is an honest placeholder** returning all-None today (NSE/BSE expose no stable public ratio endpoint); the ladder contract is complete and the deferred jugaad-data integration has a seam.

## Deviations from Plan

None - plan executed exactly as written. All three tasks followed the TDD RED→GREEN cycle; every acceptance criterion and `<verify>` command passed.

## Issues Encountered

None. `pydantic.ValidationError` is a subclass of `ValueError`, so the Literal-based source-flag and metric-key rejections are caught by the tests' `pytest.raises(ValueError)` as intended.

## Known Stubs

- `nse_multiples` returns all-None by design (documented placeholder rung — NSE/BSE have no stable public ratio endpoint). The ladder degrades honestly to yfinance / `—`; this does not block PEER-02.
- `screener_multiples` live HTTP path + the real DRHP-date multiple extraction for the IPO's own row are the **deferred live-extraction runbook step** (CODE-NOW-DEFER). Under `tests/unit` every source is monkeypatched and the hand-seeded `data/peers/swiggy_2024_11.json` demonstrates the full BOTH-dimensions shape. The live 8×-per-IPO peer precompute (peer-SET extraction against live Qdrant + market-multiple scrape) runs from the ingest runbook, mirroring the Phase 3 red-flag CODE-NOW-DEFER posture.

## User Setup Required

None - no external service configuration required this plan. Live peer precompute (deferred) needs internet egress + the DRHP peer section ingested into live Qdrant; both are runbook steps, not code blockers.

## Next Phase Readiness

- 04-05 (peer table renderer) can `load_peers('swiggy_2024_11')` offline and render per-cell provenance (source superscripts) + the cited peer-SET chip + honest `—`/`NM`/empty-state.
- Verification: `pytest tests/unit/test_peer_schema.py tests/unit/test_peer_sources.py tests/unit/test_peers_precompute.py -q` → **27 passed**. Whole suite: **355 passed, 10 skipped, 7 xfailed** (+ the 1 pre-existing ignorable `test_bge_m3_real_embed_query_1024_dim` live-model failure) — no regression from the 328-baseline (328 + 27 new).

## Self-Check: PASSED

- [x] `agent/peer_schema.py` exists
- [x] `pipelines/peer_queries.py` exists
- [x] `pipelines/peer_sources.py` exists
- [x] `pipelines/peers.py` exists
- [x] `data/peers/swiggy_2024_11.json` exists and `load_peers('swiggy_2024_11')` returns a PeerRecord with 2 companies + an honest `—` cell
- [x] Commits `a2fa89f`, `01aa024`, `05c7fe1`, `3786dd9`, `9be37d1`, `cb084a1` present in `git log`

---
*Phase: 04-historical-ipo-dataset-peer-comparator-gmp-display*
*Completed: 2026-07-06*
