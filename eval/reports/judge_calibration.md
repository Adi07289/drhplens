# Judge-vs-Human Calibration Record — DRHPLens

> **STATUS: ⛔ PENDING (blocking HITL — D-14, Plan 06.3-10 Task 6).**
> This calibration has **NOT** been performed. It requires human labelling work an
> executor cannot fake, and it burns scarce Gemini free-tier quota (≈20 req/day on
> `gemini-3.5-flash`, spike 002). **No correlation value and no real faithfulness
> number are recorded here** — doing so without the labels would be evaluation
> theater (T-6.3-THEATER, the P10 guard). The faithfulness surface therefore stays
> the honest **`-1` "not measured"** sentinel everywhere until this clears.

---

## What this record gates

The **advice-by-implication** LLM-judge lane and the DeepEval **`faithfulness_deepeval`**
lane both stay **REPORTED, never gated**, and surface the honest `-1` "not measured"
sentinel until a human calibrates the judge against real labels. A judge value may only
be promoted from `-1` to a real number **if** judge-vs-human correlation is **≥ 0.7** on
**≥ 50** examples. Below 0.7, the surface **stays `-1`** (do NOT commit a number below
the threshold — hard-gating an uncalibrated non-deterministic judge is itself a flaky-gate
failure, T-6.1-16).

## Current measured value (honest)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| `faithfulness_deepeval` (`eval/reports/eval_summary.json`) | **`-1.0`** | Not measured — sentinel. Preserved. |
| Judge-vs-human correlation | **not computed** | Pending ≥50 human labels. |
| N human-labelled examples | **0** | Pending. |

## Human runbook (to be completed by the SEBI-compliance-literate reviewer)

1. **Label ≥ 50 examples pass/fail.** Draw adversarial-compliance / faithfulness examples
   from `eval/gold/stress/*.jsonl` (the D-09 set) + sampled live-chat traces (Langfuse
   smart-sampling of advice-adjacent / low-faithfulness / very-long / retried runs). The
   SEBI-literate reviewer (or the operator standing in per D-10) labels each pass/fail —
   this is the "advice by implication" boundary a regex cannot catch.
2. **Run the judge on the same set** and compute judge-vs-human correlation. Pace the run
   across days if needed (≈20 req/day free-tier ceiling; use `deepeval test run ... -c -i
   -n 1`, serial).
3. **Record the outcome in THIS file:** N examples, the correlation value, and the
   decision:
   - **correlation ≥ 0.7** → a real (non `-1`) faithfulness number MAY be committed to
     `eval/reports/eval_summary.json` and surfaced; update the table above.
   - **correlation < 0.7** → the surface **STAYS `-1`**; record the value here and keep the
     judge REPORTED-only. Do NOT commit a number below 0.7.

## Gold-set span-tightening (paired HITL — D-14, do NOT auto-run)

An experienced Indian IPO investor/analyst must **read the Swiggy DRHP PDF** and set real
`expected_sources` answer pages (span-tightening to ≤ 2–3 pp) for the gold set. **Do NOT
re-run auto-substring matching** — it was already refused on honesty grounds in 6.1
(distinctive answer numbers are not verbatim in the chunk text; generic substrings
over-match; see `.planning/phases/06.1-.../deferred-items.md` "Gold-set tightening —
ATTEMPTED"). Until a human tightens the spans, `recall@10` and `citation_accuracy` remain
honest **saturated regression FLOORS, not quality wins** (already disclosed on the surface
+ in the eval report).

---

*Pending record created 2026-08-13 (Plan 06.3-10 Task 6). Tracked as blocking items H-4
(calibration) and H-5 (span-tightening) in `06.3-HUMAN-UAT.md`. Faithfulness surface: `-1`,
preserved.*
