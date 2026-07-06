---
phase: 4
slug: historical-ipo-dataset-peer-comparator-gmp-display
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-06
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `04-RESEARCH.md` §Validation Architecture. Per-task rows are
> filled by the planner / gsd-nyquist-auditor once PLAN.md files exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` / `pytest.ini` (existing) |
| **Quick run command** | `.venv/bin/python -m pytest tests/unit -q` |
| **Full suite command** | `.venv/bin/python -m pytest -q --deselect tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` |
| **Estimated runtime** | ~10 seconds (unit); embedder live-model test stays deselected |

---

## Sampling Rate

- **After every task commit:** Run the quick unit command.
- **After every plan wave:** Run the full suite.
- **Before `/gsd-verify-work`:** Full suite green (minus the known live-model embedder xfail).
- **Max feedback latency:** ~15 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _TBD by planner_ | — | — | PEER-01/02, GMP-01/02, UI-04 | T-04-* | — | unit | `.venv/bin/python -m pytest ...` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] **jugaad-data endpoint-validation spike** (ROADMAP research flag) — a runnable
      check that the NSE endpoints jugaad-data 0.33.1 depends on still respond;
      documents the nightly integration-test shape. Gate before committing
      jugaad-data as the primary NSE source.
- [ ] **yfinance 1.5.1 smoke test** — pin the version (major bump from STACK.md's
      0.2.50) and confirm `.NS`/`.BO` multiples fetch for a known liquid peer.
- [ ] `tests/unit/test_format_inr.py` — Indian digit grouping (12,34,567) +
      lakh↔crore auto-scale; asserts the `_format_issue_size` Western-grouping bug
      (FLAG-FORMAT) is fixed and all ₹ renders route through `format_inr`.
- [ ] `tests/unit/test_peer_record.py` — peer cached-record schema (per-cell source
      + as-of provenance for current-market AND DRHP-date values), honest `—` miss,
      empty-state when the DRHP names no peers.
- [ ] `tests/unit/test_gmp_record.py` + **GMP no-model-import audit** — an
      `inspect.getsource` test (mirroring Phase 3's `test_no_llm_or_qdrant_import`)
      pinning that the GMP module imports NO model/forecast code (GMP-02 isolation).
- [ ] `tests/unit/test_historical_dataset.py` — status-column taxonomy
      (withdrawn/listed_alive/delisted/merged/name_changed), listing-day return
      target, replace-with-NaN survivorship handling, and the ~7% median MAAR
      sanity-check (Shah & Mehta 2015 ≈ 7.19%) with a methodology-page divergence flag.
- [ ] Shared fixtures in `tests/*/conftest.py` — hand-seeded `data/peers/<id>.json`
      and `data/gmp/<id>.json` (CODE-NOW-DEFER: live scrape/ingest deferred, records
      hand-seeded so renderers are testable without live services).

*The peer/GMP scrapers and the historical-dataset build run at PRECOMPUTE time, not
on page render — validated by fixtures + monkeypatched clients, never live network in CI.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Peer table + GMP block render honestly at 375px (no red/green, per-cell provenance legible, GMP de-emphasized) | UI-04, D4-09 | Visual/interaction contract pytest can't fully assert | Seed `data/peers/<id>.json` + `data/gmp/<id>.json`, run Streamlit, open snapshot page at 375px, confirm against 04-UI-SPEC.md |
| Live GMP spread across real aggregators | GMP-01 | External scrape; catalogue IPOs are already-listed so live GMP is usually absent | Run the GMP precompute against a currently-open IPO (if any) in the user's environment |

---

*Phase: 4-historical-ipo-dataset-peer-comparator-gmp-display*
*Validation strategy drafted: 2026-07-06*
