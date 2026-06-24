# Phase 2 Close: Multi-IPO Catalogue + DRHP Snapshot Surface

**Status: CODE-COMPLETE, PENDING HUMAN UAT.**

Phase 2 ships the catalogue-browse-then-snapshot-read product surface across
5 waves. All 5 waves are executed and committed. The app is demoable end to
end on the one currently-seeded IPO (Swiggy); the other 7 catalogued IPOs are
real metadata rows whose snapshots are pending the live ingest+precompute run
(no fabricated data anywhere — they show the honest "still being prepared"
state).

## Waves — what each shipped

| Wave | Plan | What it built |
|------|------|---------------|
| 0 | 02-01 | Catalogue data model + `data/catalogue.json` (8 curated IPOs) + `data/catalogue_loader.py` (`load_catalogue`, `is_known_drhp_id` allow-list) |
| 1 | 02-02 | Retrieval scoping by `drhp_id` (multi-IPO Qdrant filtering); threat register T-02-V5 (untrusted drhp_id gate) |
| 2 | 02-03 | (per 02-03-SUMMARY.md) — agent/graph wiring extended for multi-IPO `drhp_id` parameter threading |
| 3 | 02-04 | `agent/snapshot_schema.py` (`SnapshotRecord`), `pipelines/snapshot.py` (`precompute`, `load_snapshot`, `compute_ofs_fresh`), `pipelines/snapshot_queries.py` (the 6 canned SNAPSHOT_QUERIES), and the seeded `data/snapshots/swiggy_2024_11.json` (CODE-NOW hand-authored placeholder exercising the round-trip) |
| 4 | 02-05 | **This plan.** `app.py` catalogue landing, `pages/02_snapshot.py` snapshot page, `ui/snapshot_blocks.py` (6 block renderers + split bar + financials + risk block), `ui/catalogue.py`, `ui/snapshot_chat.py`, templated `ui/copy.py`, Phase 2 CSS, extended `scripts/smoke.sh` |

## What's demoable right now

```
streamlit run app.py
```

- `/` — catalogue landing: 8 IPO cards (Swiggy, Hyundai, Ola Electric, Zomato,
  Nykaa, Paytm, LIC, Honasa), factual only (issuer · sector · listing date ·
  issue size), no green/red, no listing-gain badges. Winners and flops are
  visually identical chrome (D2-07, the hardest invariant — verified).
- Click the **Swiggy** card → `/snapshot?drhp_id=swiggy_2024_11` — the only
  IPO with a real seeded snapshot:
  - 6 cited blocks in locked order: metadata, Business, Key Financials, Risk
    Factors, Use of Proceeds (OFS-vs-fresh split bar foregrounded — 41% OFS /
    59% fresh, accent + neutral grey, no red/green), Promoters & Management
    (honest "Not disclosed in this DRHP." for pledging — SNAP-07).
  - Every cited claim reuses the UNCHANGED Phase 1 citation chip + expander
    renderer — click `[1]` to see the verbatim DRHP span + SEBI page link.
  - Below the 6 blocks: the co-located Q&A chat, bound to `swiggy_2024_11`,
    fully functional (same Phase 1 graph, parameterized by drhp_id).
- Click any of the other 7 cards → snapshot page renders the honest
  "This snapshot is still being prepared." state (no exception, no fake
  data) with a usable chat below it bound to that IPO's `drhp_id`.
- `/methodology` — unchanged Phase 1 stub, still does not 404.

## What needs the live ingest + precompute runbook

The 7 non-Swiggy catalogue rows are real DRHP metadata (issuer, sector,
listing date, issue size, SEBI source URL) but have no committed
`data/snapshots/<id>.json` yet. To make them demoable with real cited
content:

1. Ingest each DRHP/RHP PDF into Qdrant (Wave 2 `pipelines.ingest`, scoped by
   `drhp_id` per the multi-IPO retrieval wiring from Wave 1).
2. Run `python -m pipelines.snapshot precompute-all` (or `precompute-one
   <drhp_id>` per IPO) — the real 6x8 pre-compute run against live
   `agent.graph.GRAPH` + live Qdrant + live Gemini/Groq, per
   `data/INGEST_ALL_LATER.md`. This also REGENERATES `swiggy_2024_11.json`,
   replacing the CODE-NOW hand-authored seed with real claim_ids and spans
   from the actual agent pipeline.
3. Re-run `bash scripts/smoke.sh` + `pytest tests/unit -q --timeout=15` after
   the live run to catch any schema drift between the hand-seeded JSON shape
   and what the real pipeline emits.
4. (Future, not blocking Phase 2 close) Wire a structured per-year financials
   extractor into `render_financials_table`'s `years`/`rows` parameters once
   one exists — financials currently render as cited prose, which is honest
   and complete, just not yet the `.drhp-fin-table` grid the UI-SPEC
   describes for the live-data future state.

## Human-UAT steps (open — not yet performed)

See `02-05-SUMMARY.md` §Human-UAT Steps for the full 8-step checklist
(catalogue chrome neutrality, card→snapshot nav, 6-block order + split bar +
honest not-disclosed, citation chip interaction, co-located chat, mobile
breakpoints 375/640/1024, missing-snapshot state, unknown-drhp_id state).
None of these require new code — they are visual/interactive confirmation
that the automated checks (full 264-test unit baseline + `scripts/smoke.sh`
boot probes for `/`, `/methodology`, `/snapshot?drhp_id=swiggy_2024_11`) are
standing in for during this autonomous execution pass.

## Requirements traceability

SNAP-01 through SNAP-07 and OPS-01 are code-complete on the seeded Swiggy
data path. Per plan constraint, they are **not** marked fully `Complete` in
`REQUIREMENTS.md` — only marked complete for the portion delivered (UI +
honest-absence handling + co-located chat); full completion across all 8
IPOs is gated on the live precompute runbook above.

## Regression posture

The full Phase 1 + Phase 2 unit baseline (264 tests) stayed green through
every task of this wave, including the `app.py` rewrite (the highest-risk
regression surface — Swiggy's Phase 1 chat behavior is now reachable only
via `/snapshot?drhp_id=swiggy_2024_11`, not `/`). One pre-existing failure
(`test_bge_m3_real_embed_query_1024_dim`, missing `sentence-transformers`
locally) is unrelated to this wave and was left untouched per execution
instructions.
