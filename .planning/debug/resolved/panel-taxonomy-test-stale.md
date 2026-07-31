---
slug: panel-taxonomy-test-stale
status: resolved
trigger: "test_committed_sample_parquet_has_full_taxonomy_and_a_nan_row fails on clean HEAD after the 05-11 live crawl replaced the seed sample parquet with the real 1,378-row live panel"
created: 2026-07-27
updated: 2026-07-27
---

# Debug: stale committed-panel taxonomy test

## Current Focus
- hypothesis: the test asserts a seed-sample property (all 5 statuses) that the real live panel does not satisfy
- next_action: (resolved)

## Evidence
- timestamp 2026-07-27: `pytest ...::test_committed_sample_parquet_has_full_taxonomy_and_a_nan_row` fails at line 370 `assert set(df["status"].unique()) == STATUS_VALUES`.
- Verified on clean HEAD (stashed all working changes) → still fails ⇒ pre-existing, not introduced by the 05-11 residuals.
- Committed `data/historical/ipo_panel.parquet` = REAL live panel: 1,378 rows; PANEL_COLUMNS match; statuses present = {listed_alive, withdrawn}; MISSING from the 5-value taxonomy = {delisted, merged, name_changed}; 133 NaN-return rows retained; `sanity_check_median` median 0.1019 vs baseline 0.0719 → flag None (within band).
- Only the taxonomy-equality assertion fails; the NaN + sanity assertions pass.

## Eliminated
- hypothesis: the panel is corrupt / schema-broken — REJECTED (columns match, 133 NaN rows retained, median sane).
- hypothesis: my 05-11 residual commits caused it — REJECTED (fails identically on clean HEAD).

## Resolution
- root_cause: The test's `set(status) == STATUS_VALUES` ("all five present") was a property of the hand-crafted SEED sample parquet (one row per status). The 05-11 live crawl replaced the committed `ipo_panel.parquet` with the real NSE + withdrawn survivorship panel, which legitimately contains only {listed_alive, withdrawn}. The committed panel is the source of truth; the test expectation was stale.
- fix: `tests/unit/test_historical_panel.py` — renamed to `test_committed_panel_valid_taxonomy_survivorship_and_a_nan_row`; replaced the equality assertion with the REAL invariants: `set(status) <= STATUS_VALUES` (only valid statuses) AND `set(status) - {"listed_alive"}` non-empty (survivorship overlay retained, P3). Kept the schema, NaN-retention, and median-sanity guards unchanged. Guard NOT weakened: a survivor-only panel now still fails the survivorship assertion (proven: `{'listed_alive'} - {'listed_alive'} == set()` → falsy).
- verification: renamed test passes; full unit suite `523 passed, 1 skipped, 0 failed`.
- files_changed: tests/unit/test_historical_panel.py
