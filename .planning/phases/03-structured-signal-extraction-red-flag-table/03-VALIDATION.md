---
phase: 3
slug: structured-signal-extraction-red-flag-table
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-25
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pytest configured (existing `tests/` suite, 237+ unit tests green) |
| **Quick run command** | `pytest -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 seconds (unit); eval tracks (F1, numeric gate) run against live Qdrant + Gemini separately |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~60 seconds (unit). Live-service eval tracks (gold-set F1, 50-query numeric gate) are run via the pre-deploy `make release`-style script, not on every commit.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-XX-XX | XX | X | EXTRACT-01/02/03, EVAL-03, METHOD-01 | — | Numbers never rendered unsourced (numeric cite_check) | unit | `pytest -q` | ❌ W0 | ⬜ pending |

*Planner/executor populate concrete rows per task. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test stubs for the 7-field extractor (EXTRACT-01) + per-field-type F1 scorer (EXTRACT-03)
- [ ] Test stubs for the numeric-faithfulness check (unit-aware/tolerance lakh-crore-₹) extending `cite_check` (EVAL-03)
- [ ] Offline fixture-based smoke test for the ≥0.95 release gate logic (no live services)
- [ ] Test stubs for in-corpus IDF + boilerplate-floor bucketing (P12)
- [ ] Test stubs for confidence-rubric derivation + confidence-bucket reliability reporting (EXTRACT-02)
- [ ] Fixtures: a small set of hand-labeled gold rows + cited-span samples for deterministic eval tests

*Derive concrete file paths from RESEARCH.md "## Validation Architecture" (Wave 0 test gaps).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Red-flag table renders with no red/green coding + confidence labels neutral | EXTRACT-02 (UI) | Visual/Streamlit rendering | Open the snapshot page for an ingested IPO; confirm table is monochrome, confidence shows high/med/low text, numeric only in "Show your work" pane |
| "Show your work" methodology pane reveals query/chunks/prompt/sources/eval scores | METHOD-01 | Interaction + cached-data rendering | Expand the pane on a Q&A answer and a red-flag field; confirm cached trace + report-level eval scores, no live latency |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s (unit)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
