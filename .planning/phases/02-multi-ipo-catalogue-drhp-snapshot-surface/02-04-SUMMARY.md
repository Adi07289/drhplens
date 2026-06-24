---
phase: 02-multi-ipo-catalogue-drhp-snapshot-surface
plan: 04
subsystem: snapshot pre-compute (data layer)
tags: [snapshot, agent-reuse, refusal, ofs-fresh, scrubber, code-now-defer]
dependency_graph:
  requires: ["02-02 (catalogue_loader, drhp_id threading)", "02-03 (generalized ingest)"]
  provides: ["agent/snapshot_schema.py::SnapshotRecord", "pipelines/snapshot.py::precompute/load_snapshot/compute_ofs_fresh", "data/snapshots/<drhp_id>.json cache format"]
  affects: ["Wave 4 (02-05) catalogue + snapshot UI reads this cache directly"]
tech_stack:
  added: []
  patterns:
    - "Snapshot field = serialized GroundedAnswer (claim_ids intact) or RefusalResponse — zero new citation shape"
    - "Discriminated on-disk JSON union via a {\"refusal\": ...} wrapper key, reconstructed in SnapshotRecord.from_dict"
    - "Percent/keyword proximity matching (not strict regex anchoring) for compute_ofs_fresh — robust to '100% fresh issue, no OFS' phrasing"
key_files:
  created:
    - agent/snapshot_schema.py
    - pipelines/snapshot_queries.py
    - pipelines/snapshot.py
    - data/snapshots/swiggy_2024_11.json
  modified:
    - tests/unit/test_snapshot_cache.py
    - tests/unit/test_snapshot_fields.py
    - tests/unit/test_ofs_fresh.py
    - data/INGEST_ALL_LATER.md
decisions:
  - "Seeded swiggy_2024_11.json by hand (not via a mocked precompute run) so the use_of_proceeds claim text is real-world-accurate (41% OFS / 59% fresh, Swiggy's actual split) and numerically self-consistent with the stored ofs_fresh value"
  - "compute_ofs_fresh uses percentage-to-keyword proximity (20-char window) rather than naive regex spans, because naive [^.]*? spans across both keywords in 'X% fresh issue, no OFS' and misattribute the number"
  - "Defense-in-depth banned-token re-check inside precompute() even though the graph's own scrub node already gates generate() — never trust a single gate when the artifact is committed to git"
metrics:
  duration: "~50 min"
  completed: "2026-06-24"
---

# Phase 2 Plan 04: Snapshot Pre-Compute (Schema + Pipeline) Summary

Built the offline snapshot pre-compute data layer: a `SnapshotRecord` schema that stores each of the 6 SNAP-02..07 field blocks as a reused `GroundedAnswer` (citations intact) or honest `RefusalResponse`, a `precompute()` loop that calls the existing compiled agent 6x per IPO with canned queries (zero new LLM path), and a neutral `compute_ofs_fresh()` for the SNAP-06 split — all unit-tested against a monkeypatched `GRAPH.invoke`, no live Gemini/Qdrant calls.

## What Was Built

**Task 1 — `agent/snapshot_schema.py` + `pipelines/snapshot_queries.py` + seed:**
- `SnapshotRecord` (Pydantic): `drhp_id`, `computed_at`, `fields: dict[str, GroundedAnswer | RefusalResponse]`, `ofs_fresh: dict | None`. `to_json()`/`from_json()` apply a `{"refusal": ...}` wrapper-key discriminator on serialize/deserialize since `GroundedAnswer` has no native discriminator field (and the schema is locked — Phase 3 METHOD-01 depends on it verbatim, so no field was added to it).
- `pipelines/snapshot_queries.py::SNAPSHOT_QUERIES` — the 6 canned query strings (metadata, business, financials, risks, use_of_proceeds, promoter), copied verbatim from 02-RESEARCH.md §Pattern 3.
- `pipelines/snapshot.py::load_snapshot(drhp_id)` reads `data/snapshots/<drhp_id>.json`.
- `data/snapshots/swiggy_2024_11.json` — hand-authored CODE-NOW seed (6 fields, real-world-accurate Swiggy facts: price band ₹371-390, lot size 38, ₹11,327cr issue, 41% OFS / 59% fresh). Promoter field is a `RefusalResponse` (Swiggy's prospectus doesn't disclose promoter pledging — exercises the honest-refusal path). Marked with a `_source_note` flagging it as a placeholder for the live runbook to regenerate.

**Task 2 — `precompute()` + `compute_ofs_fresh()`:**
- `precompute(drhp_id)` loops `SNAPSHOT_QUERIES`, calls `GRAPH.invoke({"question": query, "drhp_id": drhp_id, "regenerate_attempts": 0})` once per field. Grounded answers are re-scrubbed before commit (defense-in-depth on top of the graph's own scrub node — a banned-token hit yields a `RefusalResponse(reason="banned_token")`, never unscrubbed prose in the committed cache). Refusal-only states store the `RefusalResponse` honestly.
- `compute_ofs_fresh(field)` extracts `{ofs_pct, fresh_pct, source_claim_id}` from the use-of-proceeds field via percentage/keyword proximity matching (handles "100% fresh issue, no OFS" without misattributing the percent to the farther keyword). Returns `None` when the field is a refusal or the split can't be determined — never a fabricated value. No verdict/color/severity key is ever emitted (SNAP-06 neutrality, checker-verifiable).
- Typer CLI: `python -m pipelines.snapshot precompute-one <drhp_id>` / `precompute-all` (loops `load_catalogue()`, per-IPO failure isolation mirroring `pipelines.ingest.ingest_all`).
- `data/INGEST_ALL_LATER.md` extended with "Step 5 — Snapshot pre-compute," the deferred live-run procedure (run after live ingestion in Steps 0-4).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] compute_ofs_fresh naive regex misattributed percentages across keywords**
- Found during: Task 2, `test_compute_ofs_fresh_pure_fresh_yields_0_100`
- Issue: An initial `[^.]*?\bOFS\b` regex spanned across "fresh" to reach a farther "OFS" mention in the same sentence (e.g. "100% fresh issue, no OFS" matched the 100% to OFS, not fresh), inverting the computed split.
- Fix: Replaced span-based regex with percentage-to-nearest-keyword proximity matching (20-char window), picking whichever keyword (OFS / fresh) is physically closer to each "%" occurrence.
- Files modified: `pipelines/snapshot.py`
- Commit: `a95b5c9`

**2. [Rule 1 - Bug] Hand-seeded swiggy.json was not numerically self-consistent**
- Found during: post-Task-2 spot check (ran `compute_ofs_fresh` against the seed's own use_of_proceeds field and got `None` instead of the stored 41/59)
- Issue: The seed's use_of_proceeds claim text described the OFS/fresh split narratively without embedding the percentages, so a live `precompute()` re-run would silently diverge from the stored `ofs_fresh` value.
- Fix: Added the explicit "59% fresh issue and 41% offer for sale" figures to the `c_ofs002` claim text/verbatim_span and the field's answer_prose, so `compute_ofs_fresh` recomputes the same 41/59 pair that's hand-stored.
- Files modified: `data/snapshots/swiggy_2024_11.json`
- Commit: `a95b5c9`

None of the other deviations — plan executed essentially as written.

## Known Stubs

- `data/snapshots/swiggy_2024_11.json` is explicitly a CODE-NOW placeholder (flagged via its `_source_note` field), built from hand-authored Swiggy facts rather than a live `GRAPH.invoke()` run. It is structurally valid (round-trips, carries claim_ids, all 6 fields present) and numerically self-consistent, but the claim text/verbatim_span/chunk_ids are illustrative, not extracted from a real Qdrant retrieval. **Resolved by:** the live `precompute-one swiggy_2024_11` / `precompute-all` run documented in `data/INGEST_ALL_LATER.md` Step 5, once live ingestion (Steps 0-4) has run.
- No other catalogue IPO has a snapshot file yet — `hyundai_2024_10.json` etc. do not exist on disk. This is intentional per CODE-NOW-DEFER scope (Task 1/2 only required the Swiggy seed); `precompute-all` generates the rest once live infra is available.

## Threat Flags

None. This plan's only new surface (the snapshot cache JSON, the `precompute()` agent-reuse loop, the `compute_ofs_fresh` parser) was already covered by the plan's own `<threat_model>` (T-02-03 snapshot-cache poisoning, T-02-04 prompt-injection-via-DRHP-content, T-02-07 honest-absence). No new trust boundary was introduced.

## Self-Check: PASSED

- FOUND: agent/snapshot_schema.py
- FOUND: pipelines/snapshot_queries.py
- FOUND: pipelines/snapshot.py
- FOUND: data/snapshots/swiggy_2024_11.json
- FOUND: tests/unit/test_snapshot_cache.py (4 tests, all passing)
- FOUND: tests/unit/test_snapshot_fields.py (4 tests, all passing)
- FOUND: tests/unit/test_ofs_fresh.py (6 tests, all passing)
- FOUND: data/INGEST_ALL_LATER.md Step 5 section
- Commit c1a025a: FOUND in git log
- Commit a95b5c9: FOUND in git log
- `pytest tests/unit -q --timeout=15` → 264 passed, 1 failed (pre-existing `test_bge_m3_real_embed_query_1024_dim`, ignorable per execution context), 0 xfailed (all 3 Wave-3 stubs flipped green)
