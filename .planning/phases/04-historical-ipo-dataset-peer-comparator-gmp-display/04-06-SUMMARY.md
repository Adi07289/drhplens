---
phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
plan: 06
subsystem: ui
tags: [streamlit, gmp, grey-market, monochrome, isolation, css]

requires:
  - phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
    provides: format_inr (04-02), GmpRecord + load_gmp cached record (04-04), page/CSS/copy files (04-05)
provides:
  - render_gmp_block — cached-only, de-emphasized, monochrome read-only GMP display
  - three first-class GMP states (multi-source spread, single-source, absent)
  - GMP block wired as the last read block above the Q&A divider
affects: []

tech-stack:
  added: []
  patterns: [monochrome multi-source range strip (mirrors render_split_bar), inline GMP-02 isolation audit]

key-files:
  created: []
  modified: [app/static/drhplens.css, ui/copy.py, ui/snapshot_blocks.py, pages/02_snapshot.py]

key-decisions:
  - "GMP is display-only + cache-only; the render module imports no model/forecast code (GMP-02 isolation, inspect.getsource audit)"
  - "Absent-GMP is the COMMON first-class state (already-listed IPOs) — an honest note, never a zero or error"
  - "The multi-source spread IS the honesty signal — divergence rendered monochrome, no red/green, no arrow, no headline number"

patterns-established:
  - "De-emphasized surface: last read block, no accent, collapsed disclosure + persistent caveat"

requirements-completed: [GMP-01, GMP-02, UI-04]

duration: ~30min
completed: 2026-07-07
---

# Phase 4 · Plan 06: Read-only monochrome GMP block Summary

**The grey-market premium now renders as the quietest surface in the app — a monochrome multi-source range strip (₹low–₹high across N sources, the divergence being the honesty signal), an absent-GMP honest note as the common case, a collapsed "why we don't trust it" explainer with a persistent caveat, and a pinned GMP-02 isolation audit — approved at the 375px visual checkpoint.**

## What shipped

- **`render_gmp_block`** in `ui/snapshot_blocks.py` — renders from the cached `load_gmp(drhp_id)` `GmpRecord` (no live scrape at render); `st.container(border=True)`; three first-class states: **multi-source spread** (`₹25–₹67 across 3 sources`, muted ticks, `role="img"` + text aria "the sources disagree"), **single-source** ("Only one source reported — no cross-source check available."), and **absent** ("No grey-market premium is being reported for this IPO right now." via `.drhp-not-disclosed`, never a zero). De-emphasized (D4-02): the last read block above the Q&A `2xl` divider, no accent, no red/green, no arrow, no bold headline number. Collapsed `st.expander("What is GMP? Why we don't trust it", expanded=False)` (unique `key`) + persistent always-visible caveat.
- **GMP-02 isolation** — `test_gmp_isolation.py` + an inline assert that `inspect.getsource(ui.snapshot_blocks)` contains none of `xgboost`/`mapie`/`sklearn`/`forecast`/`pipelines.features`/`pipelines.historical`. Display-only, cache-only.
- **Copy + CSS + wiring** — GMP strings in `ui/copy.py` under the scrubber; monochrome range-strip CSS in the single stylesheet; `format_inr` for every ₹; source labels `_html.escape`d (T-04-06-XSS verified with a `<script>` payload); wired into `pages/02_snapshot.py` as the last read block **without clobbering 04-05's** peer/glossary content.

## Verification

- Plan `<verify>`: `test_copy_no_banned_tokens.py` (23 passed), `tests/unit` (375 passed), inline `render_gmp_block` + isolation assert pass.
- Whole suite: **389 passed** (+14 across 04-05/04-06), 10 skipped, 7 xfailed (bge-m3 embedder deselected). No regression.
- **375px visual checkpoint: APPROVED by the user** (2026-07-07) — verified against both the `hyundai_2024_10` (3-source spread) and `swiggy_2024_11` (absent-GMP) seeds.

## Notes

- Commits: `66c9f84` (CSS + copy), `07a1efa` (renderer + wiring).
- The GMP source docstrings deliberately avoid the word "forecast"/model tokens so the isolation audit passes over their own source.

## Self-Check

- [x] `render_gmp_block` present, cache-only, `st.container(border=True)`, de-emphasized/last/monochrome.
- [x] Three first-class states; absent-GMP as an honest note (no zero).
- [x] GMP-02 isolation audit green (no model imports).
- [x] Copy under the scrubber; no red/green; whole suite green; 375px approved.
