# Red-Flag Extraction Gold-Set Labeling Rubric (EXTRACT-03 / D3-08)

This is the committed labeling protocol that sits beside
`eval/gold/extraction_labels.jsonl`. It documents *what* each of the 7 canonical
red-flag fields means, *where in a DRHP* to read its value, *how* the F1 scorer
matches a prediction against the gold, the *committed calibration constants*
(numeric tolerances + IDF band thresholds), edge-case parsing rules, and the
single-labeler / honest-n posture.

It is what a DS reviewer looks for: the gold set is only as credible as the
written protocol that produced it.

---

## 1. Field definitions and where to look in a DRHP

The 7 canonical field keys are locked to `agent.redflag_schema.REDFLAG_FIELD_KEYS`
(UI-SPEC R-1 fixed order). For each field: definition + the DRHP section to read.

| `field_key` | What it captures | Where to read it in the DRHP |
|-------------|------------------|------------------------------|
| `rpt_pct` | Related-party transactions as a **% of revenue/income** for the most recent fiscals | The **Related Party Transactions** note in the Restated Financial Statements; divide the aggregate RPT figure by restated revenue from operations for the same period |
| `ofs_vs_fresh` | The **fresh-issue %** of the total offer (the company-bound portion; OFS % = 100 − fresh %) | **The Issue** / cover page split, and **Objects of the Offer** (only the fresh issue funds the company) |
| `promoter_pledge_pct` | The **% of promoter holding that is pledged / encumbered** | **Capital Structure** / promoter-holding + the pledge disclosure; if no promoter group is identified, the field is *not disclosed* |
| `customer_concentration` | The **set of top customers** (or the dependence statement) driving revenue concentration | **Risk Factors** (customer-dependence risk) and **Our Business** (key customers); B2C platforms typically disclose none |
| `auditor_history` | The **set of statutory auditors** plus any **changes / qualifications / reservations / adverse remarks** | **Statutory Auditors** block of the Restated Financial Statements and the auditor's report; an auditor *change* or *qualification* is a distinct set member |
| `debt_trajectory` | The **trend of total borrowings** over the last 3–5 fiscals (rising/falling), expressed as the latest total-borrowings figure | **Restated Balance Sheet** borrowings line + the **MD&A** liquidity/indebtedness discussion |
| `going_concern` | Whether the auditors raise **any going-concern observation / material-uncertainty** statement | The **auditor's report** emphasis-of-matter / material-uncertainty paragraph in the Restated Financial Statements |

Absence is a first-class label (see §5): a field genuinely undisclosed in the
DRHP is labeled `null` (numeric/boolean) or `"not_disclosed"` (set), never dropped.

---

## 2. Per-field-type match rules (how the scorer scores)

`scripts/eval_extraction.py` dispatches on the gold row's `field_type`:

- **`numeric`** (`rpt_pct`, `ofs_vs_fresh`, `promoter_pledge_pct`, `debt_trajectory`):
  a prediction matches when `abs(pred − gold) <= F1_NUMERIC_TOLERANCES[field_key]`.
  Absolute tolerance, per field — no hard-coded tolerance in the scorer body.
- **`boolean`** (`going_concern`): **exact equality only** — no tolerance. A
  going-concern qualification is binary; a near-miss is a miss.
- **`set`** (`customer_concentration`, `auditor_history`): item-level
  precision/recall **F1 via rapidfuzz set-overlap** —
  `set_overlap_f1(pred, gold, thresh=85)` counts a gold item matched when some
  predicted item scores `rapidfuzz.fuzz.token_set_ratio >= thresh`. Empty-pred
  **and** empty-gold returns `1.0` (correctly-empty agreement); a disjoint
  pred/gold returns `0.0`.

A **not_disclosed gold cell matched by a stored `RefusalResponse`** scores
CORRECT and stays in the F1 denominator (D3-03 — refusals are first-class
labels, never silently dropped to inflate the number).

The scorer additionally splits per-field F1 **AND** accuracy by confidence
bucket (high / medium / low), so confidence becomes a *measured* reliability
claim, not decoration (D3-04 / P10).

---

## 3. Committed calibration constants (the discretion record)

These restate the values currently exported by `agent/policies.py`. They are the
calibration record: editing a value there must be reflected here.

### 3a. Per-field numeric tolerances — `agent.policies.F1_NUMERIC_TOLERANCES`

| `field_key` | Absolute tolerance (percentage points) |
|-------------|----------------------------------------|
| `rpt_pct` | 0.5 |
| `ofs_vs_fresh` | 0.5 |
| `promoter_pledge_pct` | 0.5 |
| `debt_trajectory` | 0.5 |

Rationale: ±0.5 percentage point absorbs disclosed-rounding noise (a DRHP that
prints "approximately 59%" vs an extracted 59.0). These are placeholder defaults
over a tiny gold set; recalibrate per field as the labeled set grows toward the
20–30 target (§5) and re-record the values here.

### 3b. IDF band thresholds — `agent.policies.IDF_BAND_THRESHOLDS = (2.0, 4.0)`

The two in-corpus IDF cutpoints mapping a risk's specificity score to a band
(D3-14): `score < 2.0` → `industry_standard`; `2.0 <= score < 4.0` →
`mostly_issuer_specific`; `score >= 4.0` → `issuer_specific`. These are
calibrated for a *larger* corpus; over today's n≈1–8 ingested set the max IDF
(`log N`) is well below 4.0, so the ranker is honest about small-n (it asserts
relative rank + the boilerplate floor, not absolute bands — see 03-03-SUMMARY).

### 3c. Boilerplate fuzz floor — `agent.policies.IDF_BOILERPLATE_FUZZ_THRESHOLD = 85`

A normalized risk scoring `rapidfuzz.token_set_ratio >= 85` against any phrase in
`eval/gold/boilerplate_phrases.txt` is clamped to the bottom band regardless of
its IDF. 85 mirrors the set-overlap match threshold and the existing cite-check
fuzzy posture (`CITE_CHECK_TOKEN_RATIO = 80`).

---

## 4. Edge-case parsing rules

- **Rounding:** label the value as the DRHP prints it; the ±0.5 pp numeric
  tolerance (§3a) absorbs the printed-rounding gap. Do not "correct" a printed
  figure to a recomputed one.
- **lakh / crore units:** **1 crore = 100 lakh**, 1 crore = 10 million. Convert
  every monetary figure to a single canonical unit before computing a ratio
  (e.g. an RPT amount in ₹ crore over revenue in ₹ crore). A trajectory figure is
  labeled in ₹ crore. Never mix lakh and crore in one ratio.
- **"Top-5 customers = X%":** for `customer_concentration`, the gold is the *set
  of named customers* (or the dependence statement), not the bare percentage; a
  single anchor-customer disclosure ("one customer = 62% of revenue") is labeled
  as that one-item set. If only an aggregate "top-5 = X%" with **no names** is
  disclosed, label the set with the literal bucket label (e.g. `"top 5 customers"`).
- **auditor-change vs auditor-name:** `auditor_history` is a *set*. A statutory
  auditor's *name* is one member; a *change of auditor* (e.g. "resigned",
  "newly appointed") is a **distinct** member; a *qualification / adverse remark*
  is another distinct member. A clean, unchanged auditor → a one-member set with
  just the name.
- **`ofs_vs_fresh` direction:** gold is the **fresh-issue %** (the company-bound
  portion). OFS % is its complement (100 − fresh %). Label fresh, not OFS.

---

## 5. Single-labeler note + honest-n statement (D3-05)

- **Single labeler.** These labels were authored by one labeler against the
  committed seed snapshot; there is **no second-annotator agreement** measured
  yet. Treat per-field F1 as indicative, not adjudicated. A second labeler +
  Cohen's κ is the documented next step.
- **Honest n — true n now is 1 DRHP (`swiggy_2024_11`).** It is the only DRHP
  seeded into `data/snapshots/` / live Qdrant today (per `data/snapshots/`), and
  F1 requires each labeled DRHP to be **ingested** so the extractor can run on it.
  We label all 7 fields for that one DRHP — **7 labeled cells** — and do **not**
  fabricate labels for un-ingested DRHPs. The numbers are honest, not padded.
- **Committed target: 20–30 labeled cells.** As additional catalogue IPOs go live
  (bounded by `data/INGEST_ALL_LATER.md`), label their 7 fields each, growing
  toward the 20–30 ROADMAP target. 20–30 is a documented *target*, not a claimed
  *current* figure.
- **Arithmetic traceability.** Every numeric `gold_value` must be arithmetically
  correct and traceable to a real DRHP figure (with `source_page`). Where the
  seed carries no traceable figure (`rpt_pct`, `debt_trajectory` today), the cell
  is honestly labeled `null` / not_disclosed rather than fabricated — to be
  relabeled with the real figure once live ingest lands.

## 6. Absence is a labeled value, not a dropped row (D3-03)

A field the DRHP does not disclose is a **labeled cell**: `gold_value` is `null`
(numeric/boolean) or `"not_disclosed"` (set), with `source_page` `null`. When the
extractor stores a `RefusalResponse` ("Not disclosed in DRHP") for that cell, the
scorer counts it **CORRECT** and keeps it in the F1 denominator. Refusals are
never silently dropped — dropping them would let an extractor inflate F1 by simply
refusing on hard fields. The current gold set carries **3 not_disclosed cells**
(`customer_concentration`, `promoter_pledge_pct`, `rpt_pct` — and `debt_trajectory`),
exercising this refusal-scoring path.
