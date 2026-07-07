---
phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
plan: 05
subsystem: ui
tags: [streamlit, peer-table, glossary, tooltips, css, provenance]

requires:
  - phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
    provides: format_inr (04-02), PeerRecord + load_peers cached record (04-03)
provides:
  - render_peer_table — cached-only peer-multiples table (per-cell provenance, both as-of dimensions, honest —/NM/empty-state)
  - glossary_term helper + pure-CSS tooltips on 8 Indian-IPO terms
  - peer table wired into the snapshot page after Key Financials
affects: [04-06 GMP block shares the same page/CSS/copy files]

tech-stack:
  added: []
  patterns: [pure-CSS hover/focus-within tooltip (no JS), sticky-left table via .drhp-fin-table-wrap overflow]

key-files:
  created: []
  modified: [app/static/drhplens.css, ui/copy.py, ui/snapshot_blocks.py, pages/02_snapshot.py, tests/unit/test_copy_no_banned_tokens.py]

key-decisions:
  - "Peer table renders from the cached load_peers record — no live source call on page render"
  - "Glossary tooltips are pure CSS (:hover/:focus-within) — no JS, no third-party lib, 44px tap target"
  - "QIB glossed as 'Qualified Institutional Investor' (not 'Buyer' — 'Buyer' trips the compliance scrubber's buy stem)"

patterns-established:
  - "Per-cell provenance: muted superscript source-letter + aria-label + one-line legend"
  - "Both current-market + DRHP-date values labeled per cell where available"

requirements-completed: [PEER-01, PEER-02, UI-04]

duration: ~50min (incl. one session-limit restart)
completed: 2026-07-07
---

# Phase 4 · Plan 05: Peer-multiples table + glossary tooltips Summary

**The DRHP's own listed-peer set now renders as a monochrome, sticky-left multiples table (P/E · P/B · EV/EBITDA · ROE) with per-cell source + as-of provenance, honest — / NM / empty states, and pure-CSS glossary tooltips — all from the cached record with zero live calls, approved at the 375px visual checkpoint.**

## What shipped

- **`render_peer_table(record)`** in `ui/snapshot_blocks.py` — renders from the cached `load_peers(drhp_id)` `PeerRecord`; `st.container(border=True)` card (no split-div); companies as rows (IPO first with `This IPO` tag), 4 multiples as columns, sticky-left company column; muted superscript provenance (d/s/y/n) + legend; both current-market (headline) and `… as of DRHP` secondary values; `—` (missing), `NM` (loss-making P/E) with glossary note, negatives in parentheses in identical `text-primary` — **no red/green** (D4-09). Honest empty-state when the peer set is a `RefusalResponse` (D4-06). Peer-set citation chip (the only accent) reuses the unchanged `render_citation_expanders` (D4-04); scraped names HTML-escaped (T-04-05-XSS).
- **`glossary_term` helper + pure-CSS tooltips** — `:hover`/`:focus`/`:focus-within` popover (no JS, no lib), dotted-underline trigger, 44px `::before` tap target, keyboard + mobile accessible, over the 8 terms (RPT/QIB/NII/RII/GMP/OFS/DRHP/anchor investor). All copy in `ui/copy.py` under the import-time scrubber.
- **Page wiring** — inserted into `pages/02_snapshot.py` directly after Key Financials (UI-SPEC IA block 7), guarded by the redflag allow-list + try/except + empty-state posture.

## Verification

- `test_copy_no_banned_tokens.py`: 23 passed (+3 new — 8 glossary terms present, defs scrubber-clean, peer copy clean).
- Whole suite: **375 passed** (+3), 10 skipped, 7 xfailed (the pre-existing bge-m3 embedder test deselected). No regression.
- Streamlit AppTest smoke render: 0 exceptions; peer table + legend + `This IPO` tag rendered.
- **375px visual checkpoint: APPROVED by the user** (2026-07-07).

## Notes

- Commits: `eb24750` (CSS + copy), `b7fcb88` (renderer + helper), `0dadf22` (page wiring).
- The first attempt hit the session limit after only partial CSS edits (reverted); re-run committed atomically per task.
- Live screener scrape + DRHP-date multiple extraction remain the CODE-NOW-DEFER runbook step (04-03).

## Self-Check

- [x] `render_peer_table` present, cache-only, `st.container(border=True)`.
- [x] Per-cell provenance + both as-of dimensions + honest —/NM/empty-state; no red/green.
- [x] Pure-CSS glossary tooltips on the 8 terms; copy under the scrubber.
- [x] Wired into the snapshot page; whole suite green; 375px approved.
