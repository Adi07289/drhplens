# SEBI Compliance Self-Audit — DRHPLens

> **HONEST LABEL (mandatory, D-10 honesty invariant — read this first).**
> **This is a SELF-AUDIT by the product owner. It is NOT a legal review, NOT a
> lawyer sign-off, and NOT a SEBI opinion. Nothing in this document is legal
> advice.** It documents the design posture DRHPLens adopts to stay outside the
> SEBI Research Analyst / Investment Adviser boundary, and maps each posture
> claim to the code that enforces it and the test that verifies it. With no
> in-house SEBI lawyer, the product owner (the DS who built this) explicitly
> stands in for the SEBI-compliance-literate reviewer role — and this document
> *says so plainly* rather than implying a review that did not happen. The
> committed deterministic adversarial-compliance stress suite
> (`tests/eval/test_stress_suite.py`, Plan 06.3-07) is the **enforceable proxy**
> for the formal legal review that does not exist.

> **STATUS: ⛔ AWAITING HUMAN SEBI-LITERATE SIGN-OFF (blocking, D-10/D-11 HITL).**
> This draft has NOT yet been read and signed off by a SEBI-compliance-literate
> reviewer (or the operator explicitly standing in per D-10). Per the phase
> `human_verify_mode: end-of-phase`, the sign-off is tracked as a **pending
> blocking item** in `.planning/phases/06.3-agent-polish-launch-gate/06.3-HUMAN-UAT.md`
> (item H-1) and `deferred-items.md`. **Nothing ships publicly until this
> sign-off is recorded.** The three unverified §1b regulatory flags (Section 5)
> are the specific items the reviewer must close or honestly leave open.

---

## 1. Scope & Method

| Field | Value |
|-------|-------|
| **What was audited** | The DRHPLens compliance posture as of Phase 6.3 — the Phase-1 no-advice enforcement (banned-token scrubber + three-surface disclaimer + no-personalization design) **plus** the new Phase-6.3 conversational surfaces (the bounded multi-tool agent's fused answers, conversational forecast/peer/GMP framed as informational-not-advice) **plus** the public-deploy exposure (public users on live chat). |
| **Method** | A design-posture self-audit: enumerate the RA/IA boundary DRHPLens must stay outside, map each posture claim to the enforcing code file and the verifying test, re-audit the new surfaces for advice-leakage risk, and carry forward the regulatory-research honesty flags that a self-audit cannot close. No new automated enforcement gate is added — this document *references* the existing enforcement. |
| **By whom** | The product owner (the DS building DRHPLens), **explicitly standing in** for the SEBI-compliance-literate reviewer role (D-10 portfolio reality). This is a self-audit, not an independent review. |
| **Date** | 2026-08-13 |
| **Commit** | `10c0123` (branch `phase6/6b-portfolio-surfaces`; the SEBI-REVIEW commit itself follows in this plan). |
| **Standing** | DRAFT — **awaiting human SEBI-literate sign-off** (Section 0 status; UAT item H-1). |

**What "the operator stands in" means, said plainly:** DRHPLens is a solo-built
portfolio project. There is no retained securities lawyer and no in-house
compliance function. The compliance-reviewer role in the D-10 design is filled by
the product owner reading this audit against the code. That is a genuine limitation,
not a formality — it is exactly why (a) this document is labelled a self-audit, and
(b) the committed adversarial-compliance stress suite exists as the enforceable,
regression-guarded proxy for the review that a funded product would buy.

---

## 2. The Boundary DRHPLens Stays OUTSIDE

DRHPLens is **informational and educational only** (CLAUDE.md hard constraint). It
is designed to sit *outside* the two SEBI registration regimes and on the safe side
of the education-vs-advice line. The boundary, and how the design stays outside it:

### 2.1 SEBI (Investment Advisers) Regulations, 2013 — DRHPLens is NOT an IA
"Investment advice" under the IA Regs is advice on buying/selling/dealing in
securities or on an investment portfolio, given **for consideration** and
**personalised** to a client's risk profile / suitability; RIA registration is
required. **DRHPLens stays outside via:**
- **No personalisation** — one generic informational surface; no client
  risk-profiling, no suitability step, no "for you" tailoring.
- **No consideration / no fees** — the tool is free; there is no advisory fee.
- **No portfolio construction** — it never assembles or rebalances a portfolio;
  scope is a single IPO's DRHP (cross-IPO compare is deferred idea E3).

### 2.2 SEBI (Research Analysts) Regulations, 2014 (last amended **Dec 16, 2024**) — DRHPLens is NOT an RA
The RA Regs regulate non-customised, security-specific **buy/sell/hold
recommendations, price targets, and research reports**. **DRHPLens stays outside
via:** it emits no recommendation, no target / fair value, no subscribe/avoid
verdict — enforced by the hardcoded banned-token scrubber (import-time assertion,
the TRUST-02/03 anchor). See the audit table (Section 3).

### 2.3 The education-vs-advice / finfluencer framework (SEBI, ~Jan 2025; via the SEBI (Intermediaries) Amendment Regulations, 2024, Section 16A)
SEBI explicitly distinguishes **education from advice**: unregistered persons must
not make buy/sell calls, performance/return claims, or **indirectly suggest future
prices**; a **three-month data lag** applies to educational use of *live* market
data. **DRHPLens rides this education/context line and is designed to stay on the
safe side via:**
- It uses **public DRHP/RHP filings + *historical* listing data**, not live tips —
  naturally on the safe side of the data-lag rule.
- **GMP is display-only, never a model feature** (P4, D-04) — grey-market sentiment
  is shown as caveated context beside the model, never as a signal.
- The listing-day forecast is a **calibrated range with explicit uncertainty**, not
  a price call — and it abstains honestly where history is insufficient (P9).

> **Caveat (see Section 5, flags 1 & 3):** whether §16A / the three-month lag apply
> in their exact scope to a *non-registered, public-filing-based* tool like DRHPLens
> is **not independently verified here** and is ultimately a legal determination.

---

## 3. Posture → Enforcing Code → Verifying Test (the audit table)

Every posture claim below maps to a **specific enforcing code file** AND a
**specific verifying test**. This is the core of the audit: a claim with no code
behind it is marked as argued-not-enforced, honestly.

| # | Posture claim | Enforced by (code) | Verified by (test) |
|---|---------------|--------------------|--------------------|
| P1 | **No banned prescriptive token** ever reaches the user (buy/sell/subscribe/avoid/recommend/target/fair value/over-/undervalued/accumulate/out-/underperform/book profits/bullish/bearish + morphological stems) | `compliance/scrubber.py` (NFKC-normalized deterministic regex; import-time assertion) + `compliance/banned_tokens.py` (`BANNED_TOKEN_PATTERN`) | `tests/unit/test_scrub_node.py`; **D-09 stress category (a)** in `tests/eval/test_stress_suite.py` |
| P2 | **Disclaimer on 3 surfaces** (first-use modal + persistent footer + per-answer footer) incl. the "large language models make mistakes" AI-disclosure | `compliance/disclaimer_text.py` (`ANCHOR_COPY`, `MODAL_BODY_ADDENDUM`, `PER_ANSWER_FOOTER`) | `tests/unit/test_disclaimer_surface.py`, `tests/unit/test_disclaimer_surface_render.py`; **D-09 stress category (b)** |
| P3 | **No personalisation / no fees / no portfolio** | Design property — there is deliberately **no such code path** (no user profile store, no fee flow, no portfolio builder) | **n/a — argued, not enforced by a test.** This is a *structural absence*; there is no positive artifact to assert. Flagged honestly. |
| P4 | **Single-IPO scope** (E3 cross-IPO compare deferred) | Read-only tools keyed by `drhp_id` (`agent/tools/*`); the classifier routes cross-IPO queries to an out-of-scope redirect | **D-09 stress category (d)** cross-IPO redirect in `tests/eval/test_stress_suite.py` |
| P5 | **GMP display-only, never a model feature** (P4 invariant, D-04) | GMP isolation — `agent/gmp_schema.py` read-only; the forecast pipeline imports no GMP signal | `tests/unit/test_gmp_isolation.py`, `tests/unit/test_forecast_isolation.py`, `tests/unit/test_tools_isolation.py` (AST/import isolation) |
| P6 | **Numeric faithfulness / no fabricated precision** — every number traces to a committed-artifact source; "not disclosed" over invented precision | Deterministic non-LLM cite-check node + `agent.policies.NUMERIC_FAITHFULNESS_GATE` (≥0.95) | `scripts/release_gate.py` (numeric gate); **D-09 stress category (d)** fabricated-precision bait |
| P7 | **Bounded termination** — the multi-tool agent provably halts (no unbounded advice-generation loop) | Counter-bounded router in `agent/supervisor.py` (`MAX_SUPERVISOR_HOPS` / `MAX_TOOL_CALLS` / wall-clock, D-06) | **D-09 stress** P8 fan-out fixtures in `tests/eval/test_stress_suite.py` |

**Runtime evidence (the enforceable proxy).** The deterministic D-09 stress suite
(`tests/eval/test_stress_suite.py`, Plan 06.3-07) runs **offline** (the two LLM hops
are stubbed) and **gates deploy** via `scripts/release_gate.py` — a regression in the
no-advice / loop-safety / honesty envelope physically blocks `make release`. This is
the committed, regression-guarded evidence that the posture above is not merely
documented but enforced on every deploy.

---

## 4. Re-audit of the NEW 6.3 Surfaces (D-11)

Phase 6.3 introduces three surfaces that did not exist at the Phase-1 audit, and they
are **exactly where advice can leak**. This is the reason the launch gate exists now.

### 4.1 Fused multi-tool answers (D-03)
The supervisor may fuse DRHP text + a peer table + a forecast band + the GMP-gap into
**one** cited answer. **Risk:** a fused answer that reads as a lean — *"trades at a
discount to peers, GMP is strong, margins improving"* — steers a subscribe decision
**even with zero banned tokens**. **Enforcement re-applied:** the synthesis node
re-runs the **same** `compliance/scrubber.py` + the extended deterministic cite-check
(every fused number must trace to its source record via `source_tool`/`source_record_id`)
before emit — the fused surface inherits the identical Phase-1 guardrails.

### 4.2 Conversational forecast / peer / GMP (D-04)
Chat can now surface the calibrated forecast range and the GMP-vs-model gap
conversationally. **Risk:** GMP anchoring — the answer's sentiment tilts toward the
grey-market premium, an indirect future-price suggestion (the precise thing §16A
targets). **Enforcement:** GMP stays hard-isolated (P5 above); the forecast is framed
as a range-not-a-price-call with its coverage caveat; the "describe-never-conclude"
synthesis prompt is the framing control.

### 4.3 Public live chat (D-12 public exposure)
Public users (retail investors who can act financially) can type real questions,
including adversarial ones. **Risk:** jailbreak strips the disclaimer / reveals the
system prompt; advice-bait elicits a lean. **Enforcement:** system/user prompt
separation (raw question never interpolated into the system prompt, T-1-01) is the
structural jailbreak block; the deploy-layer rate-limit + daily cap + graceful
fallback (Plan 06.3-09) bound abuse; the D-09 stress categories (a) and (b) are the
regression guard.

### 4.4 The residual risk the scrubber CANNOT catch — **advice by implication**
> **This is the launch-critical residual risk and it is named honestly here.**
> A regex passes a clean-token answer whose subscribe/avoid conclusion is
> nonetheless unmistakable. The deterministic scrubber **cannot** catch this — it is
> a posture breach, not a token breach.
> - **Mitigation (honest, partial):** a **REPORTED** advice-by-implication LLM-judge
>   lane (DeepEval, sampled) + the describe-never-conclude synthesis prompt + the
>   Langfuse smart-sampling of advice-adjacent traces.
> - **Honest limitation:** this judge lane stays **REPORTED, not gated**, and the
>   faithfulness surface stays the honest **`-1` "not measured"** until the ≥50-example,
>   ≥0.7 judge-vs-human calibration passes (D-14 HITL — pending; UAT item H-4). Until
>   then, advice-by-implication is mitigated by prompt + human sampling, **not** by an
>   automated gate. This gap is disclosed, not hidden.

---

## 5. Honesty Flags Still Open (verbatim from AI-SPEC §1b — the human reviewer must close or honestly leave these)

These are the three regulatory claims the domain research could **NOT** independently
verify against primary sources. They are carried forward **verbatim** and are the
specific items the human SEBI-literate sign-off (Section 0 / UAT H-1) must close
against the actual gazette/circular text, or honestly leave marked
*"unverified — prudent self-imposed posture."*

> **Flag 1 (RA Regs amendment + finfluencer framework — clause text unverified).**
> "I confirmed the RA Regs were *last amended Dec 16, 2024* and that a *Jan-2025 SEBI
> finfluencer framework* exists (Intermediaries Amendment 2024, Section 16A; SEBI
> action late Jan 2025) drawing the education-vs-advice line + three-month data lag. I
> did **not** independently verify the exact clause text, nor that every detail (e.g.
> the precise scope of the three-month lag) applies to a *non-registered,
> public-filing-based* tool like DRHPLens. The self-audit should cite the actual
> gazette/circular, not this section."
> **Status: unverified — prudent self-imposed posture.** Cite the gazette/circular on sign-off.

> **Flag 2 (AI-disclosure + 10pt font mandate — unverified for an unregistered tool).**
> "`compliance/disclaimer_text.py` cites 'SEBI Jan-2025 RA requirements' for a
> ~10pt-equivalent minimum font and an 'AI / large language models' disclosure. I could
> **not** independently confirm a specific SEBI mandate requiring an AI-model disclosure
> or that exact font size *for an unregistered informational tool*. SEBI did tighten
> standardised advertisement/disclaimer + prominence norms for RAs/IAs around 2024–25,
> but treat the AI-disclosure + 10pt specifics as a **prudent self-imposed posture**
> unless the self-audit locates the exact provision."
> **Status: unverified — prudent self-imposed posture** (the AI-disclosure + 10pt font
> are retained as good practice regardless).

> **Flag 3 (whether the fused behaviour is wholly outside RA/IA scope = a legal determination).**
> "Whether DRHPLens's specific *fused-answer* behaviour falls entirely outside RA/IA
> scope is ultimately a **legal determination**. Nothing in this research substitutes
> for one; D-10 must remain honestly labelled a self-audit."
> **Status: open legal determination — NOT closed by this self-audit.** This is the
> reason the document is labelled a self-audit and the reason a human sign-off is a
> blocking launch gate.

---

## 6. What This Audit Does NOT Establish

- **It is not a legal opinion.** No securities lawyer reviewed DRHPLens against the SEBI
  regulations. A self-audit by the product owner cannot and does not substitute for one.
- **It does not close the three §1b flags** (Section 5) — those remain the human
  reviewer's job, and Flag 3 is an open legal determination no self-audit can resolve.
- **It does not guarantee the advice-by-implication surface is clean** — that residual
  risk (Section 4.4) is mitigated by prompt + a REPORTED judge + human sampling, not by
  an automated gate, until the ≥0.7 calibration passes (pending, UAT H-4).
- **The enforceable proxy for the review that does not exist** is the committed
  deterministic adversarial-compliance stress suite (`tests/eval/test_stress_suite.py`,
  D-09) — a portfolio artifact and a regression guard, honestly offered *in place of*,
  not *as*, a legal review.

---

## 7. Sign-off Record (to be completed by the human reviewer — currently PENDING)

| Field | Value |
|-------|-------|
| **Reviewer (name / role)** | _pending — SEBI-compliance-literate reviewer, or operator explicitly standing in per D-10_ |
| **Date of review** | _pending_ |
| **Outcome** | _pending — `signed-off` / `signed-off-with-edits` / `changes-requested`_ |
| **Flag 1 disposition** | _pending — gazette/circular cited, or left "unverified — prudent self-imposed posture"_ |
| **Flag 2 disposition** | _pending_ |
| **Flag 3 disposition** | _pending — acknowledged as an open legal determination_ |
| **Notes / required edits** | _pending_ |

**Until every row above is filled and the outcome is `signed-off`, DRHPLens does not
ship publicly** (Section 0 blocking status; UAT item H-1).

---

*Self-audit authored 2026-08-13 (Plan 06.3-10). Honest label per D-10; re-audit scope
per D-11; §1b flags carried forward verbatim. Enforceable proxy: `tests/eval/test_stress_suite.py`.*
