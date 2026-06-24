---
phase: 02-multi-ipo-catalogue-drhp-snapshot-surface
plan: 03
subsystem: pipeline
tags: [ingestion, idempotency, parse-quality, qdrant, docling, mocked-upsert]

# Dependency graph
requires:
  - phase: 02-02
    provides: drhp_id threaded through GraphState; 8-IPO catalogue.json with front_matter_pages/source_sha256 fields
provides:
  - pipelines/ingest.py::ingest_drhp(drhp_id, pdf_path, ...) — parameterized, no module-level hard-codes
  - storage/vector.py::delete_by_drhp_id(drhp_id) — idempotent-reingest primitive
  - pipelines/ingest.py::parse_quality_gate(sections) — P14 fallback-parse detector
  - data/INGEST_ALL_LATER.md — one-pass runbook for the deferred live 8-IPO upsert
affects: [02-04-snapshot-precompute, 02-06-ingest-runbook-execution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ingest_drhp(drhp_id, pdf_path, ...) parameterizes parse/chunk/embed/upsert — Swiggy constants removed from the pipeline body"
    - "delete-by-drhp_id-filter before upsert (idempotent re-ingest, T-02-A6)"
    - "parse_quality_gate: <MIN_SECTIONS OR all-fallback-named sections OR no known-DRHP-section match => extraction_quality='fallback'"
    - "ingest_swiggy.py reduced to a thin shim re-exporting moved names bound to Swiggy constants — Phase 1 imports unchanged"
    - "CODE-NOW-DEFER-UPSERT: all logic unit-tested with mocked Qdrant client + mocked embedder; no live daemon, no heavy-dep install, no PDF downloads in this wave"

key-files:
  created:
    - pipelines/ingest.py
    - data/INGEST_ALL_LATER.md
  modified:
    - pipelines/ingest_swiggy.py
    - storage/vector.py
    - tests/unit/test_ingest_generalize.py
    - tests/unit/test_ingest_idempotent.py
    - tests/unit/test_parse_quality.py

key-decisions:
  - "Moved all parse/chunk/embed/upsert logic into pipelines/ingest.py; ingest_swiggy.py keeps zero new logic — it imports from ingest.py and binds Swiggy constants as defaults, so test_chunker.py/test_parser.py/test_qdrant_ingest.py imports keep working unchanged"
  - "front_matter_pages is now a parameter threaded through ingest_drhp -> extract_sections_from_docling -> _infer_printed_label, replacing the Swiggy-tuned ROMAN_NUMERAL_THRESHOLD_PAGE=20 module constant (A5); catalogue.json's per-IPO front_matter_pages field (Wave 1) is the source of truth at the ingest-all call site"
  - "Idempotency implemented as delete-by-filter (not deterministic chunk_ids) per RESEARCH Pattern 2 recommendation — delete_by_drhp_id() is called immediately before upsert_chunks() inside ingest_drhp's non-dry-run path"
  - "parse_quality_gate is a pure function over List[Section] (no I/O) — easy to unit-test without Qdrant/Docling; ingest_drhp surfaces its result in IngestReport.extraction_quality and ingest-all reports per-IPO status without aborting the batch (P14 failure isolation)"
  - "Created data/INGEST_ALL_LATER.md as the multi-IPO successor to data/swiggy_drhp/INGEST_LATER.md (kept for historical reference) — single runbook covering env setup, the 7 PDF downloads, SHA-256 pinning, ingest-all dry-run then live run, and verification"

metrics:
  duration_minutes: 38
  completed: 2026-06-24
  tasks_completed: 2
  files_changed: 7
  tests_added: 13
  tests_baseline: 237
  tests_after: 250
---

# Phase 2 Plan 3: Ingestion Generalization + Idempotency + Parse-Quality Gate Summary

Generalized the Swiggy-only `pipelines/ingest_swiggy.py` into a parameterized, multi-IPO `pipelines/ingest.py::ingest_drhp(drhp_id, pdf_path, ...)` with idempotent re-ingest (delete-by-drhp_id before upsert) and a parse-quality gate that flags fallback/garbage parses instead of silently shipping bad data — all unit-tested against a mocked Qdrant client and mocked embedder, with the actual 8-IPO live upsert deferred to a runbook.

## What Was Built

**Task 1 — `pipelines/ingest.py` (parameterized ingest_drhp + Swiggy shim):**
- New `pipelines/ingest.py` holds all parse/chunk/embed/upsert logic, moved verbatim (with parameterization) from `pipelines/ingest_swiggy.py`.
- `ingest_drhp(drhp_id, pdf_path, *, json_cache_path=None, front_matter_pages=20, max_tokens=512, overlap_tokens=100, source_sha256=None, dry_run=False) -> IngestReport` — the single entry point. No `DRHP_ID`/`PDF_PATH`/`JSON_CACHE_PATH` module constants exist in `ingest.py` at all; everything is a parameter.
- `_infer_printed_label` and `extract_sections_from_docling` now take `front_matter_pages` as a parameter (default 20), replacing the hard-coded `ROMAN_NUMERAL_THRESHOLD_PAGE` Swiggy constant inside the generalized pipeline (A5 fix).
- `chunk_sections(sections, drhp_id, ...)` — `drhp_id` is now a required positional/keyword parameter with no Swiggy default inside `ingest.py` (the Swiggy default lives only in the shim wrapper).
- `verify_sha256(pdf_path, expected_sha256)` — verifies PDF bytes against a catalogue SHA-256 pin before parsing; raises `ValueError` on mismatch (T-02-V6), returns `None` (not a failure) when no pin is supplied.
- Typer CLI: `python -m pipelines.ingest ingest <drhp_id> --pdf <path>` (single IPO) and `python -m pipelines.ingest ingest-all [--dry-run]` (loops `data.catalogue_loader.load_catalogue()`, per-IPO try/except so one failed IPO is logged + skipped without aborting the batch — P14 item 1).
- `pipelines/ingest_swiggy.py` reduced to a thin shim: re-exports `Section`, `chunk_docling_json`, `CHUNK_ABSOLUTE_MIN`, etc. from `pipelines.ingest`, keeps the Swiggy constants (`DRHP_ID`, `PDF_PATH`, `JSON_CACHE_PATH`, `ROMAN_NUMERAL_THRESHOLD_PAGE`), and provides Swiggy-bound wrapper functions (`extract_sections_from_docling`, `chunk_sections`) plus the original `parse`/`chunk`/`embed`/`upsert`/`all` CLI commands, all delegating into the generalized pipeline.

**Task 2 — Idempotency + parse-quality gate:**
- `storage/vector.py::delete_by_drhp_id(drhp_id)` — calls `ensure_collection()` then `client().delete(... points_selector=rest.FilterSelector(filter=rest.Filter(must=[rest.FieldCondition(key="drhp_id", match=rest.MatchValue(value=drhp_id))])))`. Idempotent (deleting a drhp_id with no points is a no-op).
- `ingest_drhp`'s non-dry-run path now calls `delete_by_drhp_id(drhp_id)` immediately before `upsert_chunks(chunks, vectors)` — verified via a call-order recorder in tests, so re-ingesting an IPO can never duplicate points (T-02-A6).
- `parse_quality_gate(sections) -> "ok" | "fallback"` — pure function, no I/O. Returns `"fallback"` if `len(sections) < MIN_SECTIONS` (10), OR every section name matches a fallback pattern (`full document` / `tables` / `preamble` / `page N`), OR no section name matches `KNOWN_DRHP_SECTION_RE` (`risk factors|objects of the (issue|offer)|our business|restated`). Returns `"ok"` otherwise.
- `IngestReport.extraction_quality` carries the gate's verdict; `ingest-all` prints per-IPO status (`ok`/`fallback`/`failed`) in its summary without aborting the batch.

**Runbook:**
- `data/INGEST_ALL_LATER.md` — the multi-IPO successor to `data/swiggy_drhp/INGEST_LATER.md` (kept as historical record). Covers: starting Qdrant, installing the deferred heavy deps (docling, sentence-transformers, FlagEmbedding), downloading the 7 new PDFs from `catalogue.json` source URLs (flagging which are landing pages vs. direct PDF links), computing+recording SHA-256 pins, running `ingest-all --dry-run` then the live run, verification via `test_second_ipo_e2e.py` and `test_qdrant_ingest.py`, and the Qdrant 1GB free-tier capacity check (RESEARCH A2).

## Deviations from Plan

None — plan executed exactly as written. One scope clarification: `storage/vector.py::delete_by_drhp_id` was implemented as part of Task 1's commit dependency chain but committed under Task 2 (its designated task) since `pipelines/ingest.py` references it lazily (import inside the function body, not at module load) — Task 1's commit and tests do not depend on `delete_by_drhp_id` existing yet, preserving clean per-task atomicity.

## Self-Check: PASSED

Verified files exist:
- `pipelines/ingest.py` — FOUND
- `pipelines/ingest_swiggy.py` — FOUND (shim)
- `storage/vector.py` — FOUND (delete_by_drhp_id added)
- `data/INGEST_ALL_LATER.md` — FOUND
- `tests/unit/test_ingest_generalize.py` — FOUND (4 real tests)
- `tests/unit/test_ingest_idempotent.py` — FOUND (3 real tests)
- `tests/unit/test_parse_quality.py` — FOUND (6 real tests)

Verified commits exist: `97e0ab3` (Task 1), `76098e3` (Task 2) — both present in `git log --oneline`.

Verified test counts: baseline 237 passed/6 xfailed/1 ignorable-failure -> after Wave 2 250 passed/3 xfailed (the 3 remaining xfails are Wave 3 stubs: `test_ofs_fresh`, `test_snapshot_cache`, `test_snapshot_fields` — untouched by this plan)/1 ignorable-failure (pre-existing `test_bge_m3_real_embed_query_1024_dim`, out of scope). No regressions.
