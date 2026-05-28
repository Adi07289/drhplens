# Wave 2 Dry-Run Report — Swiggy DRHP Ingestion

**Date:** 2026-05-28
**Pipeline:** `pipelines/ingest_swiggy.py --dry-run`
**PDF:** `data/swiggy_drhp/swiggy_prospectus_2024_11.pdf`
**Parser:** PyMuPDF 1.27.2 fallback (Docling not yet installed — torch/sentence-transformers conflict on Python 3.13)

---

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total PDF pages | 541 |
| Sections detected | 34 top-level sections |
| Total chunks produced | **1,311** |
| Total tokens (tiktoken gpt-4o) | 566,268 |
| Total characters | 2,286,475 |
| Average chunk size | ~1,744 chars / ~431 tokens |
| Token range | min=53 / max=576 |
| Pages covered | 541 unique PDF pages (100%) |
| Parse time (PyMuPDF) | 9.9s |
| Chunk time | 2.7s |
| Embed time (bge-m3, not run — deferred) | N/A — model not installed |
| Estimated Qdrant usage (1024-d float32 + payload) | ~5.8 MB (0.6% of 1 GB free tier) |

---

## Section Coverage

34 top-level sections detected by the PyMuPDF fallback parser. The bold-heuristic
parser captures major headings. Docling (when installed) will produce a finer-grained
hierarchy (subsection headers included), likely yielding 100–200 sections.

Key sections visible in this run:
- Preamble (cover page, table of contents, front-matter)
- Risk Factors
- Issue Size and Objects of the Issue
- Financial Statements
- Quick Commerce (last section in sample)

**Note on Preamble span:** The PyMuPDF fallback assigns a wide page range
(page_start=0, page_end=284) to the Preamble section because all front-matter
non-heading text accumulates before the first detected heading. This is an
artifact of the heuristic parser. Docling's section-aware parse will assign
tighter page windows.

---

## Sample Chunks

**chunk[0]** (first chunk):
```
drhp_id:            swiggy_2024_11
section:            Preamble
page_start:         0
page_end:           284
printed_page_label: i
span_offsets:       (0, 1617)
chunk_text (200c):  '(Please scan this QR code to view the Prospectus)\nPROSPECTUS\nDated: November 8, 2024\nPlease read Section 26 of the Companies Act, 2013\n100% Book Built Offer\nSWIGGY LIMITED\nCorporate Identity Number:\nU'
```

**chunk[655]** (middle chunk):
```
drhp_id:            swiggy_2024_11
section:            Preamble
page_start:         0
page_end:           284
printed_page_label: i
span_offsets:       (0, 1266)
chunk_text (200c):  '6,893,580 Total 31,737,220 Paid-up share capital 1,202,082 equity shares of face value of ₹10 each 12,020,820 86,477 series B preference shares of face value of ₹10 each 864,770 896,731 series B2 pref'
```

**chunk[1310]** (last chunk):
```
drhp_id:            swiggy_2024_11
section:            Quick Commerce
page_start:         373
page_end:           540
printed_page_label: 354
span_offsets:       (0, 609)
chunk_text (200c):  'Tencent Cloud Europe B.V. 6,327,243 Equity Shares\n₹2,467.62 million\n17. Times Internet Limited\n1,123,320 Equity Shares\n₹438.09 million\n18. West\nStreet\nGlobal\nGrowth\nPartners\n(Singapore) Pte. Ltd. 698,'
```

---

## Estimated Qdrant 1 GB Free-Tier Usage

```
Raw vector bytes:   1,311 chunks × 1024 dims × 4 bytes/float = 5.4 MB
Payload bytes:      1,311 chunks × 512 bytes avg payload = 0.67 MB
Total estimate:     ~5.8 MB (0.6% of 1,024 MB Qdrant free tier)
```

Well within the free tier. Even with Docling producing 5× more chunks (~6,500),
the collection would only use ~30 MB (3% of free tier).

---

## Anomalies and Notes

1. **Preamble page range too wide:** The PyMuPDF heuristic accumulates all
   front-matter into "Preamble" with page_end=284. Docling's hierarchical parse
   will properly split this into Cover Page, Table of Contents, Definitions,
   Abbreviations, etc. — each with tight page windows.

2. **Only 34 sections vs expected ~100–200:** The PyMuPDF bold-heuristic detects
   only the most prominent headings. Docling's TableFormer extracts full heading
   hierarchy including sub-sections and numbered items (e.g., "1.1 Summary of the
   Business", "Risk Factor 1:", etc.).

3. **No table extraction:** PyMuPDF fallback extracts tables as flat text. Docling
   extracts structured tables with row/column semantics. Table chunks in this run
   may have garbled pipe-separated text (see chunk[655] — financial table).

4. **Token ceiling respected:** max chunk = 576 tokens (within 512+13% tolerance).
   No chunk exceeded the 1,280-token hard cap.

5. **sentence-transformers not installed** (torch conflict on Python 3.13 + no
   prebuilt wheel). Embed step skipped in this dry-run. See INSTALL-NOTES.md.

---

## Docling Install Path

When torch becomes available (Python 3.11/3.12 env, or HF Spaces CPU which ships
with torch pre-installed), install and re-run:

```bash
pip install docling sentence-transformers FlagEmbedding
python -m pipelines.ingest_swiggy all --dry-run
```

The cached JSON (`swiggy_prospectus_2024_11.docling.json`) will be overwritten
with the Docling-native JSON (much richer structure), and the section count will
jump from 34 to ~150–200. Chunk count will increase proportionally to ~5,000–8,000.
