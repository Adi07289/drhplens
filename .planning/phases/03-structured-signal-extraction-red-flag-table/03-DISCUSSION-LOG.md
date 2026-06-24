# Phase 3: Structured Signal Extraction (Red-Flag Table) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-25
**Phase:** 3-Structured Signal Extraction (Red-Flag Table)
**Areas discussed:** Confidence scoring, Gold set + F1 design, Numeric-faithfulness gate, IDF bucketing + methodology pane

---

## Confidence scoring (EXTRACT-02)

### How confidence is derived
| Option | Description | Selected |
|--------|-------------|----------|
| Source-grounding rubric | high=verbatim / medium=light-parse / low=inferred; deterministic, no extra LLM cost | ✓ |
| Multi-sample self-consistency | run N times, agreement = confidence; N× LLM cost | |
| Model self-reported | LLM rates itself; poorly calibrated | |

### Confidence UI format
| Option | Description | Selected |
|--------|-------------|----------|
| Neutral high/med/low label | text only, no color (honesty-first) | |
| Numeric score (0.00–1.00) | precise badge; false-precision risk | |
| Both — label + numeric on expand | label up front, numeric in methodology pane | ✓ |

### Missing field rendering
| Option | Description | Selected |
|--------|-------------|----------|
| "Not disclosed in DRHP" | reuse RefusalResponse; absence is a signal | ✓ |
| Hide the row | cleaner, loses signal | |
| "N/A" + low confidence | conflates absent with low-confidence | |

### Confidence calibration in eval
| Option | Description | Selected |
|--------|-------------|----------|
| Yes — accuracy per confidence bucket | confidence becomes a measured claim (counters P10) | ✓ |
| No — UI hint only | not evaluated | |
| You decide | — | |

**User's choice:** Source-grounding rubric; both label+numeric-on-expand; "Not disclosed in DRHP"; report accuracy per confidence bucket.

---

## Gold set + F1 design (EXTRACT-03)

### Gold-set sizing (vs the 20-30 ROADMAP number)
| Option | Description | Selected |
|--------|-------------|----------|
| Right-size to ingested, honest n | label ingested DRHPs, report true n, document 20-30 target | ✓ |
| Commit to 20-30 this phase | expand ingest now; risks stalling on Phase 2 dep | |
| Label 20-30 from PDFs, F1 on overlap | bigger label asset, F1 only on ingested overlap | |

### Which fields labeled
| Option | Description | Selected |
|--------|-------------|----------|
| All 7 fields | full table credibility; numeric+categorical mix | ✓ |
| Numeric fields only for v1 | narrower eval | |
| You decide | — | |

### F1 match definition
| Option | Description | Selected |
|--------|-------------|----------|
| Per-field-type rules | numeric tolerance / boolean exact / set overlap | ✓ |
| Exact match everywhere | punishes harmless rounding | |
| Presence/absence | invites P12 boilerplate-recall trap | |

### Labeling protocol artifact
| Option | Description | Selected |
|--------|-------------|----------|
| Yes — commit a labeling rubric | DS-rigor artifact; cheap | ✓ |
| No — labels only | implicit protocol | |

**User's choice:** Right-size to ingested with honest n (20-30 documented as target); all 7 fields; per-field-type match rules; commit a labeling rubric.

---

## Numeric-faithfulness gate (EVAL-03, ≥0.95)

### Failure definition
| Option | Description | Selected |
|--------|-------------|----------|
| Per-number source-grounding | every number traces to a cited span; extend cite_check; deterministic | ✓ |
| LLM-judge (RAGAS-style) | judge variance + cost | |
| Hybrid | deterministic gate + LLM-judge secondary | |

### 50-query eval set construction
| Option | Description | Selected |
|--------|-------------|----------|
| Hand-curated numeric Q+gold | deterministic ground truth, best artifact | ✓ |
| Auto-derived from gold-set fields | cheaper, couples tracks | |
| Mix: derived core + hand-curated edge cases | — | |

### Gate enforcement mechanism
| Option | Description | Selected |
|--------|-------------|----------|
| Pre-deploy script/make target | `make release` refuses <0.95; + offline CI smoke test | ✓ |
| CI gate (GitHub Actions) | needs secrets + API cost per run | |
| Committed report + checklist | relies on discipline | |

### Gate coverage
| Option | Description | Selected |
|--------|-------------|----------|
| All numeric-emitting surfaces | Q&A + snapshot + red-flag | ✓ |
| Q&A answers only | narrower | |
| You decide | — | |

**User's choice:** Per-number source-grounding (extend cite_check); hand-curated 50 numeric Q+gold; pre-deploy script/make target + offline CI smoke test; covers all numeric surfaces.

---

## IDF bucketing + methodology pane (P12 + METHOD-01)

### IDF corpus
| Option | Description | Selected |
|--------|-------------|----------|
| In-corpus IDF + boilerplate floor | IDF over 8 DRHPs + hand-curated boilerplate list; honest small-n | ✓ |
| In-corpus IDF only | noisy at n=8 | |
| Augment with external corpus | extra sourcing for a stats-only input | |

### Bucket display
| Option | Description | Selected |
|--------|-------------|----------|
| Issuer-specific up top, boilerplate collapsed | hard buckets | |
| Single ranked list w/ specificity shown | ordered by IDF, neutral indicator, more transparency | ✓ |
| You decide | — | |

### Methodology pane location
| Option | Description | Selected |
|--------|-------------|----------|
| Q&A answers + red-flag table | Phase 3 headline surfaces; reuse snapshot if cheap | ✓ |
| Everywhere a claim renders | most complete, more wiring | |
| Q&A answers only for v1 | weakest demo | |

### Methodology pane data sourcing
| Option | Description | Selected |
|--------|-------------|----------|
| Trace cached per-claim, eval scores from report | free trace + report-level scores; no per-expand LLM call | ✓ |
| Live per-claim eval on expand | precise but LLM call + latency each expand | |
| Trace only, no eval scores yet | drops part of METHOD-01 | |

**User's choice:** In-corpus IDF + boilerplate floor; single ranked list with specificity indicator; pane on Q&A + red-flag table; trace cached per-claim, eval scores from latest committed report.

---

## Claude's Discretion

- Red-flag table layout (cards/table/accordion) — defer to UI-SPEC.
- Whether extraction reuses the Phase 2 snapshot grounded-pipeline path (strong default: yes) or a dedicated extraction prompt.
- Exact numeric tolerances, IDF issuer-specific threshold, and boilerplate-phrase floor list contents — tune empirically, document.
- Where the ingest-for-gold-set step runs; `make release` script name/location/report format.

## Deferred Ideas

- Expanding gold set / IDF corpus to full 20-30 DRHPs — bounded by live multi-IPO ingest.
- General RAGAS faithfulness ≥0.95 gate, failure gallery, eval dashboards — Phase 6.
- Peer multiples / GMP — Phase 4. Cross-IPO red-flag comparison — v2.
- Live per-claim eval recomputation in the methodology pane — possible Phase 6 enhancement.
