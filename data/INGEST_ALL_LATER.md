# Multi-IPO DRHP Ingestion — Deferred Live Upsert (Wave 2 → runbook)

Wave 2 (`02-03-PLAN.md`) generalized `pipelines/ingest_swiggy.py` into
`pipelines/ingest.py::ingest_drhp(drhp_id, pdf_path, ...)` and added idempotent
re-ingest (`delete_by_drhp_id` before upsert) and a parse-quality gate (P14).
All of this is **unit-tested with a mocked Qdrant client and a mocked embedder**
— no live Qdrant daemon, no torch/sentence-transformers/docling install, and no
DRHP PDF downloads happened in Wave 2 (CODE-NOW-DEFER-UPSERT).

This runbook is the **one-pass** procedure to take all 8 catalogue IPOs from
"code exists" to "ingested into Qdrant with snapshots ready," once the
environment is available. It supersedes `data/swiggy_drhp/INGEST_LATER.md`
(kept for historical reference) by covering all 8 IPOs through the
generalized pipeline instead of the Swiggy-only one.

---

## Step 0 — Environment setup

```bash
# 1. Start Qdrant locally (or point QDRANT_URL/QDRANT_API_KEY at Qdrant Cloud)
docker run -d -p 6333:6333 -p 6334:6334 \
  -v ~/.qdrant/drhplens:/qdrant/storage \
  --name drhplens-qdrant qdrant/qdrant

curl -sf http://localhost:6333/healthz

# 2. Configure connection (only if .env doesn't already have these)
test -f .env || touch .env
grep -q '^QDRANT_URL=' .env || echo 'QDRANT_URL=http://localhost:6333' >> .env
grep -q '^QDRANT_API_KEY=' .env || echo 'QDRANT_API_KEY=' >> .env

# 3. Install the heavy deps deferred during Wave 2 (torch, docling, embedder)
pip install docling sentence-transformers FlagEmbedding

# 4. Confirm Python 3.11 is active (Docling's real path; Phase 1 fell back to
#    PyMuPDF on 3.13 — see data/swiggy_drhp/INGEST_LATER.md history)
python --version   # expect 3.11.x
```

## Step 1 — Download the 7 new DRHP/RHP/Prospectus PDFs

Source URLs are in `data/catalogue.json` (`source_url` field per IPO). For
each non-Swiggy entry, download and save to `data/<drhp_id>/<drhp_id>.pdf`:

```bash
mkdir -p data/hyundai_2024_10 data/ola_electric_2024_08 data/zomato_2021_07 \
         data/nykaa_2021_10 data/paytm_2021_11 data/lic_2022_05 data/honasa_2023_11

# Example (repeat per IPO, using catalogue.json source_url):
curl -sL -o data/hyundai_2024_10/hyundai_2024_10.pdf \
  "https://www.sebi.gov.in/filings/public-issues/oct-2024/hyundai-motor-india-limited-prospectus_87741.html"
# NOTE: several catalogue source_url entries are SEBI *landing pages*, not
# direct PDF links (e.g. Hyundai, Ola, Zomato, Nykaa, LIC, Honasa). Visit the
# landing page, locate the actual PDF link, and download that — then record
# the real PDF URL back into catalogue.json's source_url for provenance.
# Paytm's source_url IS already a direct PDF link.
```

After downloading, compute and record the SHA-256 pin per IPO (P14 item 4 /
T-02-V6 — protects against silent version drift):

```bash
for f in data/*/[a-z_0-9]*.pdf; do
  drhp_id=$(basename "$(dirname "$f")")
  sha=$(shasum -a 256 "$f" | awk '{print $1}')
  echo "$drhp_id: $sha"
done
# Then manually update each entry's "source_sha256" field in data/catalogue.json
```

**Swiggy note:** Swiggy's existing PDF (`data/swiggy_drhp/swiggy_prospectus_2024_11.pdf`)
was previously ingested via a PyMuPDF fallback (Python 3.13, no Docling). Per
`data/swiggy_drhp/INGEST_LATER.md` and RESEARCH assumption A8, re-ingest Swiggy
with real Docling now that Python 3.11 + Docling are available — the
`delete_by_drhp_id` idempotency fix (this wave) makes that re-ingest safe (no
duplicate points).

## Step 2 — Run the generalized ingest over the full catalogue

```bash
# Dry run first (parse + chunk + embed, NO Qdrant writes) — sanity-check
# chunk counts and parse_quality per IPO before committing to a live upsert:
python -m pipelines.ingest ingest-all --dry-run

# Review the per-IPO "quality=ok" / "quality=fallback" summary printed at the
# end. Any IPO marked "fallback" should be investigated (heterogeneous layout,
# P14) before the live run — see <action> in 02-03-PLAN.md Task 2 for the
# fallback signals (too few sections, all-"Full Document"/"Page N" sections,
# no known DRHP section name matched).

# Live run (parse + chunk + embed + delete-by-drhp_id + upsert, per IPO,
# failure-isolated — one bad DRHP does not block the batch):
python -m pipelines.ingest ingest-all
```

Or ingest a single IPO at a time (useful for re-running just the flagged one):

```bash
python -m pipelines.ingest ingest hyundai_2024_10 --pdf data/hyundai_2024_10/hyundai_2024_10.pdf
```

## Step 3 — Verify

```bash
# Flip the deferred integration test green (currently xfail(run=False)):
pytest tests/integration/test_second_ipo_e2e.py -x

# Existing Swiggy integration check still passes after re-ingest:
pytest tests/integration/test_qdrant_ingest.py -x

# Check Qdrant collection size vs the 1GB free-tier estimate (RESEARCH A2 —
# LIC especially is large; ingest-all prints a per-IPO size estimate):
# If >50% utilization is reported, consider self-hosting Qdrant on Fly.io
# instead of the free-tier cloud cluster.
```

## Step 4 — Update catalogue.json with confirmed metadata

For any IPO whose `source_url` was a landing page (not a direct PDF), and for
every IPO's `source_sha256` (Step 1), update `data/catalogue.json` to record
the real, confirmed values — this file is reviewed in PRs and treated as
trusted config (T-02-02), so getting the provenance right here matters.

## What this runbook intentionally does NOT do

- Does not download any DRHP/RHP/Prospectus PDF (network step, deferred).
- Does not start or require a live Qdrant daemon during Wave 2 execution.
- Does not run `python -m pipelines.ingest ingest-all` for real.
- Does not flip `tests/integration/test_second_ipo_e2e.py` out of
  `xfail(run=False)` — that happens only when this runbook is actually run.

All ingestion *logic* (parameterization, idempotency, parse-quality gate) is
implemented and unit-tested with a mocked Qdrant client + mocked embedder in
Wave 2. This file is the bridge from "code complete" to "data live."
