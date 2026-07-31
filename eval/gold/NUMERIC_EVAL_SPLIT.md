# Numeric eval split — disclosed (gate) vs derived (reasoning)

**Added 2026-07-24 (Job B / EVAL-03).**

## Why this split exists

`numeric_faithfulness` is defined as *"the fraction of eval questions whose every
emitted number grounds to a cited DRHP span."* That is a **grounding** metric — it
validly measures whether the model states numbers the document actually discloses.

The original `numeric_eval.jsonl` (50 Qs) conflates two different capabilities:

1. **Numeric grounding** — the answer is a figure the DRHP *states* (e.g. "revenue
   from operations was ₹112,473.90 million"). The number is in the document, so it
   can (and must) ground to a cited span.
2. **Numeric reasoning** — the answer is *computed* across disclosed figures (YoY
   growth %, net-loss margin, OFS/fresh ratio, band width = 390−371, "3 days") or is
   a unit restatement the document never prints (e.g. "expressed in lakh"). The
   answer number appears **nowhere** in the DRHP, so it cannot ground by
   construction — a faithful model would have to show its work.

Holding the **grounding release gate** accountable for reasoning answers is a
category error: it measures the wrong thing and can never reach ≥0.95 no matter how
good grounding is. So the gate scores `numeric_eval_disclosed.jsonl`; the derived
set is tracked separately as a numeric-reasoning eval (measured, not gated).

## This is NOT score-gaming

Membership is by a principled criterion — *"does the DRHP directly state this single
figure?"* — verified against the actual PDF numbers, the gold `note` fields, and the
live grounding results. It is **not** selected by which questions the model passes:

- Disclosed questions that currently **FAIL** the gate: `num-002`, `num-005`
  (retrieval/citation precision — the number is in the index but the LLM cited a
  chunk lacking it).
- Derived questions that currently **PASS**: `num-010`, `num-011` (the model grounds
  on the disclosed components without emitting the computed %).

The 0.95 threshold is unchanged. The derived set is retained in full for the
reasoning track — nothing is deleted.

## Disclosed (23) — scored by the release gate

Directly-stated single figures: total/fresh/OFS issue size, price band (371/390),
face value, lot size, OFS share count, bid dates, QIB/NII/RII allocations, and the
stated restated-financials line items (revenue & loss for FY22/FY23/FY24 + Q1FY25).

`num-001,002,003,004,005,006,007,012,013,014,015,017,018,019,023,024,026,030,031,032,035,036,040`

> **2026-07-25 (human-approved):** num-033 moved to the derived set below. It asks for
> an "implied equity value given the post-issue share count" — a *computed* quantity —
> while its gold answer is the per-share price 390 (which already appears as num-005). A
> computed-value question belongs in the reasoning bucket by the criterion above, and it
> is redundant with num-005. See `NUMERIC_GOLD_REVIEW.md`.

## Derived / reasoning (27) — tracked separately, not gated

Computed values (margins, growth %, absolute diffs, ratios, sums, lot×price,
band width, day count, **implied equity value — num-033**) and lakh unit-restatements
the document never prints.

`num-008,009,010,011,016,020,021,022,025,027,028,029,033,034,037,038,039,041,042,043,044,045,046,047,048,049,050`
