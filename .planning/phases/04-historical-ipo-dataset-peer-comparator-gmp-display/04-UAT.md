---
status: complete
phase: 04-historical-ipo-dataset-peer-comparator-gmp-display
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md, 04-05-SUMMARY.md, 04-06-SUMMARY.md]
started: 2026-07-07
updated: 2026-07-07
---

## Current Test

[testing complete]

## Tests

### 1. Indian rupee formatting
expected: Issue size + financials render ₹ with lakh/crore + Indian digit grouping (12,34,567), never Western commas.
result: pass

### 2. Peer-multiples table
expected: |
  swiggy snapshot page — directly after Key Financials, a "peer comparison" table:
  rows = companies (Swiggy first, marked "This IPO"), then Zomato; columns = P/E · P/B ·
  EV/EBITDA · ROE. Muted superscript source letters (d/s/y/n) next to values + a legend
  below. Missing cells show "—"; a loss-making P/E shows "NM". NO red/green — a low and a
  high multiple look identical. On a narrow screen the company-name column stays pinned
  (sticky) while the 4 metric columns scroll.
result: pass

### 3. Glossary tooltip
expected: |
  Hover (desktop) or tap (mobile) a glossary term or the "NM" cell in the peer table — a
  small definition popover appears (e.g. "Not meaningful — the company reported a loss"),
  opens instantly with no lag, and dismisses on move-away/tap-away.
result: pass

### 4. GMP block — absent state
expected: |
  swiggy snapshot page — the LAST block before the Q&A chat is the GMP block, and it reads
  "No grey-market premium is being reported for this IPO right now." with NO fabricated
  number. It is the quietest block on the page — monochrome, no accent colour, no big
  headline number, a persistent short caveat, and a collapsed "What is GMP? Why we don't
  trust it" expander.
result: pass

### 5. GMP block — multi-source spread
expected: |
  hyundai snapshot page (http://localhost:8501/snapshot?drhp_id=hyundai_2024_10) — the GMP
  block shows a monochrome range strip headlined "₹25–₹67 across 3 sources" with muted
  ticks (the divergence between sources is the point), NO red/green, no up/down arrow. The
  "What is GMP? Why we don't trust it" explainer is collapsed by default and expands to a
  full explanation; the caveat stays visible.
result: pass

### 6. Honesty-invariant sweep
expected: |
  Across both pages: nowhere in the peer table or GMP block is there red/green colour, a
  badge, an up/down arrow, a "buy/sell/subscribe" word, or a single "GMP suggests strong
  demand"-style signal. Everything reads as factual data, not advice.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]

## Known deferred (not a UAT gap)

- 04-07 full historical panel build is deferred (chittorgarh source rot — documented in
  data/historical/README.md). It is backend-only / not user-visible; Phase 4 stays 6/7.
