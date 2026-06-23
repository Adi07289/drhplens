---
phase: 2
slug: multi-ipo-catalogue-drhp-snapshot-surface
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-23
---

# Phase 2 — Validation Strategy

> Per-phase validation contract. Derived from `02-RESEARCH.md` §Validation Architecture. Reuses the Phase 1 pytest harness + the 219-test baseline (must stay green).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python 3.11 venv — real Docling + torch now available) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/unit -x -q --timeout=15` |
| **Full suite command** | `pytest tests/ -x -q --timeout=60` |
| **Baseline** | 219 unit tests from Phase 1 MUST stay green after every Phase 2 commit |

---

## Sampling Rate

- **After every task commit:** `pytest tests/unit -x -q --timeout=15`
- **After every wave:** `pytest tests/ -x -q --timeout=60`
- **Before phase close:** full suite green; snapshot-faithfulness eval run once on the ingested IPOs

---

## Per-Task Verification Map

| Task ID | Wave | Requirement | Threat | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|-------------|--------|-----------------|-----------|-------------------|--------|
| 2-drhp_id-thread | 1 | SNAP-01 | V5 | `drhp_id` flows through GraphState → retrieve → search; default preserves Phase 1 behavior | unit | `pytest tests/unit/test_drhp_id_threading.py -x` | ⬜ pending |
| 2-drhp_id-allowlist | 1 | SNAP-01 | V5 | `drhp_id` validated against catalogue allow-list before reaching `search()`; unknown id rejected | unit | `pytest tests/unit/test_drhp_id_allowlist.py -x` | ⬜ pending |
| 2-catalogue-loader | 1 | SNAP-01, OPS-01 | — | `data/catalogue.json` loads + validates against schema; all entries have required fields | unit | `pytest tests/unit/test_catalogue.py -x` | ⬜ pending |
| 2-ingest-generalize | 2 | INGEST (reuse) | — | `pipelines/ingest.py(drhp_id, pdf_path, metadata)` parameterized; no module-level hard-codes | unit | `pytest tests/unit/test_ingest_generalize.py -x` | ⬜ pending |
| 2-ingest-idempotent | 2 | INGEST (reuse) | — | Re-ingest deletes existing points by `drhp_id` filter first — no duplicate points | unit | `pytest tests/unit/test_ingest_idempotent.py -x` | ⬜ pending |
| 2-parse-quality-gate | 2 | (P14) | — | A DRHP that parses to < N sections / fails table extraction is flagged, not silently ingested | unit | `pytest tests/unit/test_parse_quality.py -x` | ⬜ pending |
| 2-snapshot-cache-rw | 3 | SNAP-02..07 | — | `data/snapshots/<drhp_id>.json` round-trips; carries claim_ids; scrubber-clean | unit | `pytest tests/unit/test_snapshot_cache.py -x` | ⬜ pending |
| 2-snapshot-fields | 3 | SNAP-02..07 | — | 6 field blocks computed via agent; "not disclosed" stored honestly when DRHP silent (esp. SNAP-07 pledging) | unit | `pytest tests/unit/test_snapshot_fields.py -x` | ⬜ pending |
| 2-ofs-fresh-split | 3 | SNAP-06 | — | OFS-vs-fresh % computed from use-of-proceeds; foregrounded; neutral (no green/red) | unit | `pytest tests/unit/test_ofs_fresh.py -x` | ⬜ pending |
| 2-catalogue-page | 4 | SNAP-01, OPS-01 | — | Catalogue grid renders IPO cards (factual only, no perf badges); click → snapshot route | manual | `bash scripts/smoke.sh` | ⬜ pending |
| 2-snapshot-page | 4 | SNAP-02..07 | — | Snapshot page renders 6 cited blocks + co-located Q&A chat; citations use Phase 1 chips | manual | `bash scripts/smoke.sh` | ⬜ pending |
| 2-2nd-ipo-e2e | 5 | INGEST + SNAP | T-2-DRHP | Ingest a 2nd IPO end-to-end + pre-compute its snapshot; retrieval scoped to that drhp_id | integration | `pytest tests/integration/test_second_ipo_e2e.py -x` (xfail until live Qdrant) | ⬜ pending |
| 2-snapshot-faithfulness | 5 | SNAP-04 | — | Financials snapshot cited spans actually support the summary (faithfulness ≥ Phase 1 baseline) | eval | `pytest tests/eval/test_snapshot_eval.py -x --run-eval` (deferred) | ⬜ pending |
| 2-p13-recall-probe | 5 | (P13) | — | Indian-finance recall probe (lakh/crore/RPT/QIB queries) — gates the hybrid-retrieval decision | eval | `pytest tests/eval/test_p13_recall.py -x --run-eval` (deferred) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements (test stubs)

- [ ] Stub test files for every row above (xfail until their wave implements them)
- [ ] `tests/integration/test_second_ipo_e2e.py` — xfail(run=False) until live Qdrant
- [ ] `tests/eval/test_snapshot_eval.py` + `tests/eval/test_p13_recall.py` — gated by `--run-eval`
- [ ] `data/catalogue.json` schema stub (content fills in Wave 1)
- [ ] `data/snapshots/` directory + `.gitkeep`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test |
|----------|-------------|------------|------|
| Catalogue grid browse → pick IPO → snapshot page, all factual (no green/red winner/loser badges) | SNAP-01, OPS-01 | Visual + interaction | `streamlit run app.py`, browse catalogue, click an IPO, verify neutral cards |
| Snapshot field citation chips expand to DRHP source span | SNAP-02..07 | Streamlit interaction | Click `[1]` on a snapshot block, verify inline source expander |
| OFS-vs-fresh split visual foregrounded + neutral | SNAP-06 | Visual | Verify the split bar reads "promoter cash-out vs growth capital" without red/green |
| "Not disclosed in DRHP" shown honestly for a silent field | SNAP-07 | Visual + correctness | Find an IPO where pledging isn't disclosed; verify honest empty state |
| Mobile responsive catalogue + snapshot at 375/640/1024 | UI-01 (inherited) | Visual | Chrome DevTools per 02-UI-SPEC |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 stub
- [ ] No 3 consecutive tasks without automated verify
- [ ] Phase 1 219-test baseline stays green throughout
- [ ] `nyquist_compliant: true` after Wave 0 stubs land

**Approval:** pending
