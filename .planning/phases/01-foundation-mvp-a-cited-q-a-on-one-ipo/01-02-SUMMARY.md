---
phase: 01-foundation-mvp-a-cited-q-a-on-one-ipo
plan: "02"
subsystem: schemas-scrubber-disclaimer
tags:
  - wave-1
  - pydantic-v2
  - schemas
  - compliance
  - banned-token-scrubber
  - disclaimer-surfaces
  - trust
dependency_graph:
  requires:
    - 01-01 (scaffolding, pyproject.toml, test stubs)
  provides:
    - agent/schemas.py (RetrievedChunkRef, Claim, GroundedAnswer, RefusalReason, RefusalResponse)
    - agent/state.py (GraphState TypedDict)
    - compliance/banned_tokens.py (BANNED_TOKENS, BANNED_TOKEN_PATTERN)
    - compliance/scrubber.py (scrub, ScrubResult)
    - compliance/disclaimer_text.py (ANCHOR_COPY + 5 variant constants)
    - ui/copy.py (17 scrubber-clean copy constants with import-time assertion)
    - ui/disclaimer.py (DisclaimerSurface, render_disclaimer_gate)
  affects:
    - Wave 2 (RetrievedChunkRef field names align with ChunkPayload)
    - Wave 3 (GraphState keys consumed by every LangGraph node)
    - Wave 4 (DisclaimerSurface rendered into app.py; ui/copy.py imported)
    - Phase 3 METHOD-01 (GroundedAnswer/Claim/claim_id schema consumed verbatim)
    - Phase 6 legal review (ANCHOR_COPY is the single source of truth)
tech_stack:
  added:
    - pydantic v2 (Field pattern regex, field_validator, model_validator, min_length, max_length)
    - dataclasses (ScrubResult)
    - re (IGNORECASE | UNICODE compiled regex with morphological stems)
    - unicodedata (NFKC normalization in scrubber)
    - inspect (import-time copy assertion in ui/copy.py)
  patterns:
    - Pydantic v2 cross-phase contract locked in SKELETON §B
    - Morphological stem regex (subscri, accumulat, etc.) with \w* outside capturing group
    - Import-time scrubber assertion for copy module (TRUST-03 defense-in-depth)
    - Single-source-of-truth disclaimer constants (one edit propagates to all surfaces)
    - lastindex-based canonical root extraction from re.Match
key_files:
  created:
    - agent/schemas.py
    - agent/state.py
    - compliance/banned_tokens.py
    - compliance/scrubber.py
    - compliance/disclaimer_text.py
    - ui/copy.py
    - ui/disclaimer.py
    - tests/unit/test_schemas.py (20 real tests, xfail flipped green)
    - tests/unit/test_scrubber.py (48 real tests, xfail flipped green)
    - tests/unit/test_disclaimer_surface.py (19 real tests, xfail flipped green)
    - tests/unit/test_copy_no_banned_tokens.py (18 real tests, xfail flipped green)
  modified: []
decisions:
  - "Used morphological STEMS (subscri, accumulat) rather than full word forms — Python 3.13 does not match subscribe in subscribing because subscribing != subscribe + ing (e-dropping rule)"
  - "matched_token extracted via re.Match.lastindex (the participating group index in alternation), returning canonical root with \\w* outside the group"
  - "FLAG-9 applied: test_render_persistent_footer_includes_methodology_link_token asserts CSS class drhp-footer, not inline font-size; Wave 4 CSS refactor does not break this test"
  - "REFUSAL_BANNED_TOKEN_COPY reworded from 'implied a recommendation' to 'implied investment advice' — import-time assertion correctly caught the banned token"
  - "unsubscribed does NOT fire the scrubber with stem subscri (word boundary prevents match) — improved over naive subscribe stem which fired on unsubscribed"
metrics:
  duration: "~45 minutes"
  completed: "2026-05-28"
  tasks_completed: 3
  files_created: 11
---

# Phase 01 Plan 02: Pydantic v2 Schemas + Banned-Token Scrubber + Disclaimer Infrastructure

Locked cross-phase schema contract (SKELETON §B), deterministic SEBI-compliance scrubber with morphological stem matching, and three-surface DisclaimerSurface abstraction — all compliance infrastructure live before any LLM call exists in the codebase.

## What Was Built

### Task 1 — Pydantic v2 schemas + GraphState

**`agent/schemas.py`** — five exported classes:

| Class | Key fields | Constraints |
|-------|------------|-------------|
| `RetrievedChunkRef` | chunk_id, page_start, page_end, printed_page_label, section, score, verbatim_span, span_offsets | span_offsets validator rejects start > end (STRIDE T-1-02) |
| `Claim` | claim_id, text, source_chunk_id, drhp_page, section, verbatim_span, span_offsets, sources | claim_id pattern `^c_[a-z0-9]{6,16}$`; sources min_length=1 (PITFALL P18) |
| `GroundedAnswer` | answer_prose, claims, sub_question_addressed, sub_question_unaddressed | model_validator enforces unique claim_ids |
| `RefusalReason` | Literal["low_retrieval_score", "unsupported_claim", "banned_token", "infrastructure_error"] | Locked vocabulary; Wave 3 graph branches on these |
| `RefusalResponse` | reason, explanation, reformulation_suggestions | reformulation_suggestions max_length=3 (UI-SPEC chips) |

**`agent/state.py`** — `GraphState` TypedDict with 12 locked keys:
`question, retrieved_chunks, reranked_top_k, gate1_passed, gate1_max_score, sub_questions, grounded_answer, scrub_passed, regenerate_attempts, all_claims_grounded, cite_check_failures, refusal`

Tests: 20 real tests in `tests/unit/test_schemas.py` — claim_id regex boundary cases, span_offsets inversion, sources min_length, GroundedAnswer unique claim_ids, RefusalReason vocabulary, RefusalResponse max_length, GraphState key presence.

### Task 2 — Banned-token scrubber

**`compliance/banned_tokens.py`** — 16 canonical tokens, compiled `BANNED_TOKEN_PATTERN` (IGNORECASE | UNICODE).

**BANNED_TOKENS list with rationale:**

| Token | Category | Rationale |
|-------|----------|-----------|
| subscribe | UI-SPEC L-5 locked | IPO subscription action |
| avoid | UI-SPEC L-5 locked | Sell-equivalent advisory |
| buy | UI-SPEC L-5 locked | Direct purchase recommendation |
| sell | UI-SPEC L-5 locked | Direct sale recommendation |
| target | UI-SPEC L-5 locked | Target price anchor |
| recommend | UI-SPEC L-5 locked | Analyst recommendation vocabulary |
| fair value | UI-SPEC L-5 locked | Valuation-opinion phrase |
| overvalued | UI-SPEC L-5 locked | Valuation-opinion word |
| undervalued | UI-SPEC L-5 locked | Valuation-opinion word |
| target price | UI-SPEC L-5 locked | Explicit price-target phrase |
| accumulate | Planner-discretion | Brokerage "accumulate" rating |
| outperform | Planner-discretion | Sell-side analyst rating |
| underperform | Planner-discretion | Sell-side analyst rating |
| book profits | Planner-discretion | Direct sell-instruction (Indian retail) |
| bullish | Planner-discretion | Directional market-sentiment word |
| bearish | Planner-discretion | Directional market-sentiment word |

**Stem-based morphological matching (key deviation from naive plan):**
The plan's text said `\b(subscribe)\w*\b` would catch "subscribing", but Python 3.13 confirms that "subscribe" is NOT a substring of "subscribing" (subscribe ends in 'e'; subscribing drops the 'e' before adding 'ing'). We use linguistic stems:
- `subscri` → subscribe, subscribed, subscribing, subscriber, subscription
- `accumulat` → accumulate, accumulated, accumulating

**`compliance/scrubber.py`** — `ScrubResult(passed, match, matched_token)` dataclass + `scrub(text)` function. Pure deterministic regex; NFKC normalization; `matched_token` = canonical root via `match.lastindex`; hard-block semantics per D-09.

Tests: 48 real tests in `tests/unit/test_scrubber.py` — all base forms, morphological variants, multi-word phrases, case insensitivity, word boundary, homoglyph behavior.

### Task 3 — DisclaimerSurface + copy module

**`compliance/disclaimer_text.py`** — 6 constants:
- `ANCHOR_COPY` — D-07 byte-for-byte: "DRHPLens reads prospectuses for you. It cites what the document says and shows historical context. Decisions about investing are yours. This is not investment advice."
- `MODAL_HEADING` = "Read this once."
- `MODAL_BODY_ADDENDUM` — contains "large language models" (SEBI Jan-2025 RA AI-disclosure)
- `MODAL_CTA` = "I understand — open DRHPLens"
- `PERSISTENT_FOOTER_SUFFIX` = " · methodology"
- `PER_ANSWER_FOOTER` = "Informational only — not advice."

**`ui/copy.py`** — 17 required constants (all passing the banned-token scrubber at import time):
HERO_HEADING, HERO_SUBHEADING, QUESTION_PLACEHOLDER, MODAL_CTA, EMPTY_STATE_HEADING, EMPTY_STATE_BODY, COLD_START_COPY, LOADING_ANSWER_COPY, REFUSAL_NO_GROUNDING_TEMPLATE, REFUSAL_PARTIAL_GROUNDING_TEMPLATE, REFUSAL_BANNED_TOKEN_COPY, ERROR_QDRANT_UNREACHABLE, ERROR_LLM_TIMEOUT, ERROR_RATE_LIMIT, PER_ANSWER_DISCLAIMER, METHODOLOGY_STUB_HEADING, METHODOLOGY_STUB_BODY.

**`ui/disclaimer.py`** — `DisclaimerSurface` class + `render_disclaimer_gate` module-level function:
- `render_modal()` → dict {heading, body, cta_text}
- `render_persistent_footer()` → HTML with class="drhp-footer", inline font-size: 12px, /methodology link
- `render_per_answer_footer()` → HTML with class="drhp-disclaimer-per-answer", "Informational only — not advice."
- `render_disclaimer_gate(session_state)` → modal dict or None (pure Python, no Streamlit import)

Tests: 19 real tests in test_disclaimer_surface.py; 18 real tests in test_copy_no_banned_tokens.py.

## Wave 0 xfail Stubs Flipped Green

| xfail stub | Plan file | Tests added | Wave |
|------------|-----------|-------------|------|
| test_claim_id_pattern_enforced | test_schemas.py | 20 tests total | 1 ✅ |
| test_every_banned_token_conjugation_blocked | test_scrubber.py | 48 tests total | 1 ✅ |
| test_three_surfaces_render_anchor_copy | test_disclaimer_surface.py | 19 tests total | 1 ✅ |
| test_every_copy_string_passes_scrubber | test_copy_no_banned_tokens.py | 18 tests total | 1 ✅ |

**All 4 Wave 0 xfail stubs are now green.**

## Test Summary

```
pytest tests/unit/ -x -q --timeout=10
108 passed, 7 skipped, 1 xfailed in 0.40s
```

- 108 passed (up from 3 real tests in Wave 0)
- Wave 0 integrity tests (`test_drhp_integrity.py`) still green: 3 passing
- 7 skipped = Wave 2/3/4/5 stubs (expected)
- 1 xfailed = `test_chunker.py` Wave 2 stub (expected)

## Deviations from Plan

### [Rule 1 - Bug] Morphological stem matching instead of full word roots

**Found during:** Task 2 implementation

**Issue:** The plan's `\b(subscribe)\w*\b` regex does not match "subscribing" in Python 3.13 because "subscribing" = "subscrib" + "ing" (e-dropping), not "subscribe" + "ing". Python literal matching confirms `"subscribe" in "subscribing"` is False.

**Fix:** Used shorter linguistic stems that are actual prefixes of all inflections:
- `subscri` covers subscribe, subscribed, subscribing, subscriber, subscription
- `accumulat` covers accumulate, accumulated, accumulating, accumulation

**Trade-off documented:** "unsubscribed" no longer fires (with stem `subscri`, the `\b` before "subscri" within "unsubscribed" doesn't fire because 'n' before 'subscri' is \w). This is an IMPROVEMENT — the original plan's `subscrib` stem would have incorrectly blocked "unsubscribed users" (legitimate phrase).

**Files modified:** compliance/banned_tokens.py

### [Rule 2 - Missing validation] REFUSAL_BANNED_TOKEN_COPY reworded

**Found during:** Task 3 import of ui/copy.py

**Issue:** The UI-SPEC Copywriting Contract has "Couldn't return that answer because it would have implied a **recommendation**." — but "recommendation" contains the banned root "recommend". The import-time scrubber assertion correctly fired.

**Fix:** Reworded to "Couldn't return that answer because it would have implied investment advice." — same semantic intent, passes the scrubber.

**This is a feature, not a bug:** the import-time assertion exists precisely to catch this case.

**Files modified:** ui/copy.py

### FLAG-9 Applied

Per plan execution instructions: `test_render_persistent_footer_includes_methodology_link_token` tests for the `.drhp-footer` CSS class presence, NOT for `font-size: 12px` inline style. Separate test `test_sebi_10pt_floor_satisfied` tests the font-size inline style. This ensures Wave 4's CSS refactor does not require rewriting the methodology link test.

## Dependency Install Status

Minimal install via Python 3.13 venv:
- `pydantic>=2`, `pytest>=8`, `pytest-timeout` — INSTALLED
- Heavy deps (sentence-transformers, docling, langgraph, streamlit, etc.) — DEFERRED to Wave 2/3
- Wave 1 has no import-time dependency on heavy deps; all 108 tests pass with minimal install

## TRUST Requirements Implemented

| REQ | Description | Status |
|-----|-------------|--------|
| TRUST-01 | Three-surface disclaimer (modal + footer + per-answer) | ✅ closed |
| TRUST-02 | Banned-token scrubber prevents prescriptive language | ✅ closed |
| TRUST-03 | SEBI Jan-2025 prominence + AI-disclosure in modal | ✅ closed |

## Known Stubs

None — all Wave 1 deliverables are fully implemented. No stubs flow to UI rendering in this wave (DisclaimerSurface is the abstraction layer; Wave 4 wires it into app.py).

## Threat Flags

No new threat surface introduced. Wave 1 is pure Python with no network endpoints, no file access beyond read-only, no auth paths.

T-1-02 mitigation (span_offsets validator) and T-1-08 mitigation (import-time copy assertion) are now in code.

## Self-Check: PASSED

- [x] agent/schemas.py — exports RetrievedChunkRef, Claim, GroundedAnswer, RefusalReason, RefusalResponse; ≥ 60 lines
- [x] agent/state.py — exports GraphState with 12 required keys
- [x] compliance/banned_tokens.py — exports BANNED_TOKENS (16 tokens), BANNED_TOKEN_PATTERN (IGNORECASE|UNICODE)
- [x] compliance/scrubber.py — exports scrub, ScrubResult
- [x] compliance/disclaimer_text.py — exports ANCHOR_COPY (byte-for-byte D-07), MODAL_HEADING, MODAL_BODY_ADDENDUM, MODAL_CTA, PERSISTENT_FOOTER_SUFFIX, PER_ANSWER_FOOTER
- [x] ui/copy.py — exports 17 required constants; imports cleanly (assertion passes)
- [x] ui/disclaimer.py — exports DisclaimerSurface, render_disclaimer_gate
- [x] Commits: 8ab0e45 (Task 1), df8f7d5 (Task 2), 89ec2d0 (Task 3)
- [x] pytest tests/unit/ — 108 passed, 7 skipped, 1 xfailed
- [x] Wave 0 integrity tests still green (3 passing)
- [x] All 4 xfail stubs flipped green
