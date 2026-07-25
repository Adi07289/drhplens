# Numeric gold-set review — disclosed subset (2026-07-25)

Human-review pass over the 24 `numeric_eval_disclosed.jsonl` questions (Job B / EVAL-03).
Every gold value was verified to be **actually stated in the DRHP** (millions form).
Findings below are recommendations for a human to accept/reject — they are NOT applied,
because removing/altering a failing question changes the gate and that call is not the
model's to make (anti-p-hacking).

## Verdict: 22 sound · 1 defective · 1 awkward

### ⚠ num-033 — DEFECTIVE + REDUNDANT (recommend REMOVE or REWORD)

> "What was the implied equity value at the upper price band, given the post-issue
> share count, that the cover page price band reflects per share?"  gold = **390 rupees**

- **Defect:** the question asks for an *implied equity value given the post-issue share
  count* — i.e. a **computed market cap** (price × shares, ≈ ₹1.1 trillion) — but the gold
  answer is the per-share **price 390**. Question and answer do not match. The gold `note`
  itself concedes: *"Per-share cap is Rs 390; restated to the disclosed upper band figure."*
- **Redundant:** the gold answer (390) duplicates **num-005** ("upper end of the price
  band per equity share" = 390), which is already in the disclosed set.
- The LLM correctly says the DRHP does not state that implied value → it can never ground.
- **Recommendation:** remove num-033 (defective + duplicate) OR reword it to a coherent
  disclosed question. **If a human accepts the removal on its merits, the disclosed gate
  becomes 22/23 = 0.957 (≥ 0.95).** Flagged, not applied — this is a human decision.

### ~ num-040 — AWKWARD UNIT (recommend REWORD; keep)

> "What was the fresh-issue size of the Swiggy IPO expressed in crore (rounded…)?" gold = 4,499 crore

- The DRHP states the fresh issue in **millions** (₹44,990 million = 4,499 crore). Forcing
  "expressed in crore" invites the model to answer in a unit the document never prints; it
  grounds only via the million↔crore reconciliation. Currently passes, but the framing is
  fragile. **Recommendation:** reword to "…in the units the DRHP discloses" or accept the
  millions answer. Low priority.

### Sound (22)

num-001, 002, 003, 004, 005, 006, 007, 012, 013, 014, 015, 017, 018, 019, 023, 024, 026,
030, 031, 032, 035, 036 — each asks for a single figure the DRHP directly states. (num-030
currently fails for an LLM answer-quality reason, not a gold defect — see the quick-task SUMMARY.)

## Bottom line for the gate

- As-is (24 Qs): **0.917**.
- If the human removes the defective/redundant num-033 on its merits: **0.957 (green)**.
- num-030 remains an honest LLM-answer-quality miss regardless (not a gold defect).
