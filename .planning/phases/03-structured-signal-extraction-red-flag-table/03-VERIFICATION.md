---
phase: 03-structured-signal-extraction-red-flag-table
verified: 2026-07-06T00:00:00Z
status: human_needed
score: 5/6 success criteria fully verified in code (SC3 partial — honest-n gold set + live F1 pending ingest)
mode: mvp
re_verification: null
overrides_applied: 0
gaps: []
deferred: []
human_verification:
  - test: "Run the live numeric-faithfulness release gate: `make release` (requires GEMINI_API_KEY + live Qdrant)."
    expected: "Gate computes numeric_faithfulness over eval/gold/numeric_eval.jsonl (50 Qs), writes eval/reports/<date>-numeric-gate.md, and exits 0 only if >=0.95 (else exits non-zero and blocks deploy)."
    why_human: "Requires live Gemini + Qdrant services which are intentionally absent from this venv. Gate LOGIC is fully offline-tested (tests/eval/test_release_gate.py: 0.94->exit, 0.95/0.96->pass); only the live number is unverifiable here."
  - test: "Run the extraction F1 eval against live services: `python scripts/eval_extraction.py` after ingesting labeled DRHPs."
    expected: "Per-field F1 + confidence-bucket reliability populated with real predictions (currently scored_cells=0 / macro F1 0.000 because the extractor cannot run offline)."
    why_human: "F1 requires the extractor to run over each labeled DRHP, which requires live Qdrant+Gemini ingest (Phase 2 carryover, data/INGEST_ALL_LATER.md). The scorer logic is unit-tested (tests/eval/test_extraction_f1.py, 52 Phase-3 tests green)."
  - test: "Open the Streamlit snapshot page for swiggy_2024_11 and inspect the red-flag table + IDF risk list visually."
    expected: "7 stacked monochrome rows in canonical order, confidence as neutral high/med/low TEXT (no color/badge), not-disclosed rows shown honestly with confidence omitted, a single IDF-ranked risk list (no red/green), and a 'Show your work' pane on each field/answer. (03-VALIDATION.md Manual-Only checks.)"
    why_human: "Visual/interaction rendering of Streamlit cannot be verified via grep; honesty invariants (monochrome, neutral confidence, meter-not-verdict) need a human eye."
---

# Phase 3: Structured Signal Extraction (Red-Flag Table) — Verification Report

**Phase Goal:** A retail user opening any covered IPO sees a structured red-flag signal table (RPT % of revenue, OFS vs fresh-issue %, promoter pledge %, customer concentration, auditor history, debt trajectory, going-concern mentions), each field with a visible extractor-confidence score, backed by a hand-labeled gold-set F1 evaluation committed in the repo and a numeric-faithfulness release gate of >=0.95.
**Verified:** 2026-07-06
**Status:** human_needed (all mechanisms delivered in code; 3 items require live-service / visual human verification)
**Mode:** MVP
**Re-verification:** No — initial verification

---

## User Flow Coverage

User story / goal: «A retail user opening any covered IPO sees a structured red-flag signal table, each field with a visible confidence score, backed by a committed gold-set F1 and a >=0.95 numeric-faithfulness release gate.»

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Open snapshot page | Red-flag table renders for an ingested IPO | `pages/02_snapshot.py:119` calls `render_redflag_table(redflag_record)`; cache read at `:166` via `load_redflag` | ✓ |
| See 7 fields | RPT%, OFS/fresh, pledge, customer conc., auditor, debt, going-concern — all seven, always | `data/redflag/swiggy_2024_11.json` holds all 7 canonical keys populated (5 grounded, 2 honest refusals); `render_redflag_table` iterates `REDFLAG_FIELD_LABELS` | ✓ |
| See confidence | Each grounded field shows neutral high/med/low text | Cache tiers: rpt_pct=high(0.91), ofs=medium(0.68), debt=low(0.52)… ; `snapshot_blocks.py:378` renders `.drhp-confidence-label` text; numeric score only in pane | ✓ |
| See not-disclosed honestly | Absent fields render "Not disclosed in DRHP", confidence omitted | promoter_pledge_pct + auditor_history are REFUSAL with tier=None; `_render_redflag_refusal` (`snapshot_blocks.py:312`) | ✓ |
| See issuer-specific risks first | Single IDF-ranked list, most issuer-specific first | `render_idf_risk_list` (`snapshot_blocks.py:413`) wired at `pages/02_snapshot.py:197-198`; 5 ranked_risks banded issuer_specific→industry_standard | ✓ |
| Show your work | One-click pane reveals query/chunks/prompt/sources/eval scores from cache | `render_methodology_pane` wired per field (`snapshot_blocks.py:387`); no-live-call test green | ✓ |
| Outcome — trustworthy table | Numbers are source-grounded (>=0.95 gate) and evaluated (F1 committed) | Gate logic + numeric track committed & offline-tested; F1 scaffold + gold labels committed (live numbers pending ingest — human item) | ⚠ partial |

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
|---|---------------------------|--------|----------|
| SC1 | EXTRACT-01: structured 7-field red-flag table on the snapshot page | ✓ VERIFIED | `agent/redflag_schema.py` locks 7 canonical keys + rejects unknown; `pipelines/redflag.py` precompute/`load_redflag`; committed populated cache; `render_redflag_table` wired at `02_snapshot.py:119` |
| SC2 | EXTRACT-02: each field carries a visible confidence score | ✓ VERIFIED | `pipelines/confidence.py:classify_confidence` deterministic (verbatim→high / parse→medium / cross-section→low), no LLM; tier rendered as neutral text, numeric score only in pane (`methodology_pane.py:197`) |
| SC3 | EXTRACT-03: hand-labeled gold set + per-field F1 committed | ⚠ PARTIAL | `eval/gold/extraction_labels.jsonl` (7 cells, n=1 swiggy), `extraction_rubric.md` (152 lines), `scripts/eval_extraction.py` (set-overlap/numeric/boolean + confidence-bucket split), committed report `eval/reports/2026-06-25-extraction-f1.md`. **Deviation:** honest n=1 vs ROADMAP "20-30 DRHPs" (intentional per D3-05); committed F1 = 0.000 placeholder (scored_cells=0) until live extraction runs. Scorer logic unit-tested. |
| SC4 | EVAL-03: numeric-faithfulness track + >=0.95 release gate that refuses deploy | ✓ VERIFIED (logic) | `eval/gold/numeric_eval.jsonl` (50 Qs), `scripts/release_gate.py:enforce_gate` (`sys.exit(1)`+report < gate), `Makefile` `release:`+`gate-test:` targets, `NUMERIC_FAITHFULNESS_GATE=0.95` (docstring: "not a tunable to relax" — NOT lowered), `run_eval.compute_numeric_faithfulness` reuses `cite_check`. Offline test: 0.94→exit, 0.95/0.96→pass. Live run is a human item. |
| SC5 | P12/EXTRACT-01: IDF issuer-specific vs boilerplate bucketing, single foregrounded list | ✓ VERIFIED | `pipelines/risk_idf.py:rank_risks` in-corpus IDF + `boilerplate_phrases.txt` (25 phrases) fuzzy floor + `IDF_BAND_THRESHOLDS` bands; `render_idf_risk_list` is a SINGLE ranked list superseding Phase-2 ordering (`02_snapshot.py:197-206` — IDF list XOR Phase-2 fallback) |
| SC6 | METHOD-01: cached-only "Show your work" pane on Q&A + red-flag surfaces | ✓ VERIFIED | `ui/methodology_pane.py` renders query/chunks/scores/prompt/sources/eval-report from cache; no-live-call test asserts no openai/genai/groq/qdrant/GRAPH.invoke tokens; two-tier redesign (source-verification default + technical toggle) present; wired per field + Q&A |

**Score:** 5/6 fully verified in code; SC3 partial (mechanism verified, honest-n + live F1 numbers pending ingest — documented deviation D3-05).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `agent/redflag_schema.py` | RedFlagRecord (7 fields) + RankedRisk + to_json/from_dict | ✓ VERIFIED | 7-key frozenset + validator rejects unknown; RankedRisk 3-band; confidence None on refusal |
| `agent/policies.py` | NUMERIC_FAITHFULNESS_GATE=0.95, IDF_BAND_THRESHOLDS, tolerances | ✓ VERIFIED | Gate 0.95 locked (not lowered); IDF bands (2.0,4.0); F1 tolerances; boilerplate fuzz 85; numeric rel-tolerance 0.01 |
| `agent/nodes/cite_check.py` | per-number source-grounding (unit-aware + tolerance) | ✓ VERIFIED | `_extract_scaled_numbers`/`_number_reconciles`/`_scaled_numbers_grounded`; ₹crore↔lakh reconciliation; no LLM import |
| `pipelines/redflag.py` | precompute_redflags + load_redflag | ✓ VERIFIED | GRAPH.invoke × 7 canned queries; classify_confidence per field; allow-list path gating; refusal on blocked numbers |
| `pipelines/risk_idf.py` | rank_risks (IDF + boilerplate floor) | ✓ VERIFIED | in-corpus IDF over load_catalogue corpus; fuzzy boilerplate clamp; band mapping |
| `pipelines/redflag_queries.py` | REDFLAG_QUERIES 7 keys == schema allow-list | ✓ VERIFIED | key_links pattern confirmed |
| `scripts/release_gate.py` | >=0.95 gate body with sys.exit | ✓ VERIFIED | pure `enforce_gate` + live `main`; report on both branches |
| `scripts/eval_extraction.py` | per-field-type F1 + confidence-bucket split | ✓ VERIFIED | set_overlap_f1; reads REDFLAG_FIELD_KEYS + F1_NUMERIC_TOLERANCES; dated report writer |
| `eval/gold/numeric_eval.jsonl` | ~50 numeric Qs + gold + source page | ✓ VERIFIED | exactly 50 lines, gold_numeric+source_page fields |
| `eval/gold/extraction_labels.jsonl` | 7 fields × n DRHPs | ⚠ PARTIAL | 7 cells, n=1 (honest-n per D3-05; 20-30 documented as target) |
| `ui/methodology_pane.py` | cached-only pane, no live call | ✓ VERIFIED | zero forbidden client tokens; numeric confidence only in pane |
| `ui/snapshot_blocks.py` | render_redflag_table + render_idf_risk_list + pane wiring | ✓ VERIFIED | both renderers present; refusal + numeric-gate-blocked copy paths |
| `pages/02_snapshot.py` | red-flag + single IDF risk list wired | ✓ VERIFIED | load_redflag + render_redflag_table + render_idf_risk_list; single-list XOR Phase-2 fallback |
| `Makefile` | release target wrapping the gate | ✓ VERIFIED | `release:` → release_gate.py; `gate-test:` → offline pytest |

### Key Link Verification

All 18 key links across the 7 plans verified (`gsd-sdk query verify.key-links`): REDFLAG_QUERIES↔schema allow-list, confidence↔cite_check normalization, cite_check↔policy tolerance, redflag↔GRAPH↔confidence↔risk_idf↔catalogue, eval_extraction↔schema/policy/reports, release_gate↔policy gate, run_eval↔cite_check, Makefile↔release_gate, methodology_pane↔expander/reports, copy↔scrubber, snapshot_blocks↔methodology_pane/chip, page↔load_redflag. All "Pattern found in source".

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `.venv/bin/python -m pytest -q` | 303 passed, 7 skipped, 7 xfailed, 1 failed (bge-m3 live embed — expected IGNORE) | ✓ PASS |
| Phase 3 subset | pytest 9 Phase-3 test files | 52 passed | ✓ PASS |
| Gate offline logic | `test_release_gate.py` | 0.94→SystemExit(non-zero); 0.95/0.96→pass; asserts GATE==0.95 | ✓ PASS |
| Methodology no-live-call | `test_methodology_pane.py` | getsource forbids openai/genai/groq/qdrant/GRAPH.invoke — passes | ✓ PASS |
| Committed cache populated | inspect data/redflag/swiggy_2024_11.json | 7 fields (5 grounded w/ tiers, 2 refusals tier=None), 5 ranked risks | ✓ PASS |
| Live `make release` | (not run) | Requires GEMINI_API_KEY + live Qdrant | ? SKIP → human |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| ui/copy.py | 43-50 | `QUESTION_PLACEHOLDER` | ℹ INFO | Phase-2 input-box placeholder copy constant, not a stub marker — no impact |

No TODO/FIXME/XXX/TBD debt markers in Phase 3 source. CSS "red/green" grep matched only the `.drhp-redflag-*` class-name substring and a "no red for losses" comment — no color coding present.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| EXTRACT-01 | 03-01/03/07 | ✓ SATISFIED | 7-field schema + precompute + populated cache + table render |
| EXTRACT-02 | 03-02/06/07 | ✓ SATISFIED | deterministic confidence + neutral text label + pane-only numeric |
| EXTRACT-03 | 03-04 | ⚠ PARTIAL | gold labels + rubric + scorer + committed report present; honest n=1 vs 20-30 (D3-05 deviation) + live F1 numbers pending ingest |
| EVAL-03 | 03-05 | ✓ SATISFIED (logic) | 50-Q set + release_gate sys.exit + Makefile + 0.95 gate; live run pending (human) |
| METHOD-01 | 03-06/07 | ✓ SATISFIED | cached-only pane, no-live-call test, wired on fields + Q&A |

### Human Verification Required

1. **Live numeric-faithfulness gate** — Run `make release` with live Gemini+Qdrant. Expected: computes score over the 50-Q set, writes `eval/reports/<date>-numeric-gate.md`, exits non-zero if <0.95. *Gate logic is fully offline-verified; only the live number is pending.* This is a KNOWN-PENDING human-only step, distinct from any code gap.
2. **Live extraction F1 numbers** — Run `python scripts/eval_extraction.py` after live ingest. Expected: real per-field F1 + confidence-bucket reliability (currently placeholder 0.000, scored_cells=0). *Scorer logic unit-tested; blocked only by Phase-2 live multi-IPO ingest carryover.*
3. **Visual honesty invariants** — Open the Streamlit snapshot page (03-VALIDATION.md Manual-Only): monochrome table, neutral high/med/low text, not-disclosed rows, single IDF risk list, Show-your-work pane. Needs a human eye.

### Gaps Summary

No code-level gaps. Every Phase 3 mechanism is implemented, wired, and tested offline; the full suite matches the documented baseline (303 passed; the sole failure is the expected live-only bge-m3 embedder test).

The one shortfall against the literal ROADMAP contract is **SC3 / EXTRACT-03**: the committed gold set is n=1 (swiggy, 7 fields) rather than "20-30 DRHPs", and the committed F1 report shows placeholder 0.000 because the extractor cannot produce predictions without live Qdrant+Gemini. This is an **intentional, documented deviation** (decision **D3-05**: "right-sized to the ingested DRHP set with honest n … documenting 20-30 as the committed target"), coupled to the deferred live multi-IPO ingest (`data/INGEST_ALL_LATER.md`, a Phase-2 carryover). The mechanism grows automatically as the catalogue is ingested — it is not a broken or missing artifact.

**This SC3 deviation looks intentional.** To formally accept it, add to this file's frontmatter:

```yaml
overrides:
  - must_have: "A per-field F1 from a hand-labeled gold set of 20-30 DRHPs committed under eval/gold/extraction_labels.jsonl"
    reason: "D3-05 right-sizes the gold set to the ingested DRHP set with honest n (currently n=1 swiggy); 20-30 is a documented target bounded by the deferred live multi-IPO ingest (data/INGEST_ALL_LATER.md). Scorer + rubric + report scaffold committed and unit-tested; F1 numbers populate on live ingest."
    accepted_by: "<name>"
    accepted_at: "<ISO timestamp>"
```

Overall: the phase goal — a retail user sees an honest, cited, confidence-scored red-flag table with an issuer-specific risk list and a show-your-work pane, backed by an enforced numeric-faithfulness gate — is achieved in code. Remaining items are live-service execution and visual confirmation, routed to human verification.

---

_Verified: 2026-07-06_
_Verifier: Claude (gsd-verifier)_
