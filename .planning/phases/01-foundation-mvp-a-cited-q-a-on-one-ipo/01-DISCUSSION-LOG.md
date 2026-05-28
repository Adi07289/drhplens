# Phase 1: Foundation + MVP-A (Cited Q&A on One IPO) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 1 — Foundation + MVP-A (Cited Q&A on One IPO)
**Areas discussed:** Citation chip behavior, Refusal posture (RAG-03), Disclaimer copy + style

---

## Citation chip behavior

### Q1: When the user clicks a citation chip, what should happen?

| Option | Description | Selected |
|--------|-------------|----------|
| Expand inline w/ source snippet | Chip expands in place to show cited DRHP text span + link to SEBI-hosted PDF page. Simplest, ships fast in Streamlit (st.expander), no PDF viewer dependency. | ✓ |
| Side PDF viewer scrolls to page | streamlit-pdf-viewer scrolls to cited page with span highlighted. Most "show your work" — great for recruiters. Cost: PDF.js setup + two-column responsive layout. | |
| Modal with source span + PDF link | st.dialog with source text + external PDF link. Perplexity pattern. Modal management on mobile non-trivial. | |
| External link only to SEBI-hosted DRHP | Opens SEBI/BSE/NSE-hosted DRHP PDF in new tab. Cheapest. Breaks flow. | |

**User's choice:** Expand inline w/ source snippet
**Notes:** Defers the side PDF viewer to Phase 3 if at all — inline expand is sufficient for v1.

### Q2: How should the chip itself render visually?

| Option | Description | Selected |
|--------|-------------|----------|
| Superscript numbered chip [1] [2] | Compact Perplexity-style, anchored to citation list at end of answer. Cleanest on mobile. Numbers reset per answer. | ✓ |
| Inline page-number badge (p.47) | More transparent (page visible immediately), visually noisier in text-heavy answers. | |
| Margin annotation (desktop) / footnote (mobile) | Academic style, most rigorous looking, higher complexity for Phase 1. | |

**User's choice:** Superscript numbered chip [1] [2]
**Notes:** Reads as academically grounded; mobile-friendly.

### Q3: If 3 sentences cite the same DRHP span, how should chips render?

| Option | Description | Selected |
|--------|-------------|----------|
| Deduplicate — one [1] chip after all 3 sentences | Cluster claims citing the same span; render one chip at cluster end. Matches Perplexity. claim_id traces still record each link separately for Phase 3 methodology pane. | ✓ |
| One chip per sentence — [1] [1] [1] | Most literal about per-claim provenance, visually noisy. | |
| Cluster + show count [1×3] | Show chip once with count badge. Unusual pattern; might confuse users. | |

**User's choice:** Deduplicate — one [1] chip after all 3 sentences
**Notes:** None — clean call.

---

## Refusal posture (RAG-03)

### Q1: When DRHP doesn't address the question (or retrieval confidence too low), what should the system do?

| Option | Description | Selected |
|--------|-------------|----------|
| Hard refuse + suggest reformulation | "This DRHP does not address X. Try asking about Y or Z, which the prospectus does cover." Reformulation suggestions from top retrieved sections. | ✓ |
| Hard refuse only | "This DRHP does not address X." Period. Cleanest message; can feel stonewalling. | |
| Graceful redirect to related DRHP content | Discusses related topic instead. Risk: feels like dodging the question. | |
| Refuse + link out to investor education | "For general questions, see SEBI investor education at [link]." Honest but breaks flow. | |

**User's choice:** Hard refuse + suggest reformulation
**Notes:** Sets honesty-first tone clearly AND helps the user succeed on their next attempt.

### Q2: What signal triggers the refusal?

| Option | Description | Selected |
|--------|-------------|----------|
| Both: retrieval-score floor AND cite-check node | Gate 1: max retrieval score (post-rerank) < threshold → refuse before LLM call. Gate 2: cite-check finds unsupported claim → block answer. Belt-and-suspenders. | ✓ |
| Retrieval-score floor only | Simpler, faster (no wasted LLM call). Misses confident-retrieval but over-generalized-LLM case. | |
| Cite-check node only | Always run retrieval + LLM; block on unsupported claim. Catches generation failures; wastes LLM on hopeless queries. | |
| LLM self-judge — model decides if it can answer | Convenient; biased toward overconfidence. Not recommended for anti-hallucination product. | |

**User's choice:** Both: retrieval-score floor AND cite-check node
**Notes:** Aligns with the cross-cutting invariant "non-LLM cite-check node validates before emit."

### Q3: Multi-part question where DRHP addresses only some parts — how should the system respond?

| Option | Description | Selected |
|--------|-------------|----------|
| Answer what's grounded + flag what's missing | "The DRHP addresses parts A and B — [cited answer]. It does not address part C; consider asking that separately." Requires agent to decompose. | ✓ |
| Refuse the whole question, ask user to split | Cleanest provenance; user-hostile; adds friction. Maybe right in v1.x multi-step Q&A phase, less right for Phase 1's single-pass RAG. | |
| Answer the grounded part silently, drop the rest | User thinks they got a complete answer when they didn't. Bad for honesty-first product. | |

**User's choice:** Answer what's grounded + flag what's missing
**Notes:** Most helpful AND most honest — partial value without smuggling in ungrounded parts.

---

## Disclaimer copy + style

### Q1: What's the disclaimer's voice?

| Option | Description | Selected |
|--------|-------------|----------|
| Honesty-first prose | "DRHPLens reads prospectuses for you. It cites what the document says and shows historical context. Decisions about investing are yours. This is not investment advice." On-brand, SEBI-covering. | ✓ |
| Lawyer-style template | "This product is for informational and educational purposes only. It does not constitute investment advice..." Safe boilerplate; users skim past. | |
| SEBI-template-verbatim | Maximally-compliant; wooden; ironically gets less reader attention. | |

**User's choice:** Honesty-first prose
**Notes:** Anchor copy subject to legal-review polish before Phase 6 public launch.

### Q2: Where does the disclaimer appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Three surfaces — modal + persistent footer + per-answer | First-use modal with "I understand" button (localStorage) + persistent slim footer + short per-answer footer. Max prominence; SEBI-safe. | ✓ |
| Two surfaces — persistent footer + per-answer footer | Skip first-use modal. Less friction; relies on footer being visible enough on mobile. | |
| Front-load — full block above chat input on first visit + persistent slim footer thereafter | First-visit shows full disclaimer prominently; after first message, collapses to slim footer. No modal friction; can feel imposing. | |

**User's choice:** Three surfaces — modal + persistent footer + per-answer
**Notes:** Banned-token scrubber implementation behavior (hard block + regenerate vs soft rewrite) deferred to planner discretion.

---

## Claude's Discretion

- **MVP-A IPO pick** — User opted to let Claude decide. Recommendation in CONTEXT.md: **Swiggy IPO (Nov 2024)**; fallback candidates Hyundai Motor India or Ola Electric. Locked at start of Phase 1 plan-phase.
- **Banned-token scrubber implementation** — hard-block-and-regenerate (strong default) vs soft rewrite, plus the exact banned-token list beyond subscribe/avoid/buy/sell/target/recommend.
- **Retrieval-score floor threshold** — empirical tuning during Phase 1 against a small held-out eval set.
- **Empty / loading / error UI states** — standard patterns; planner specifies copy + visual treatment.
- **`/methodology` stub page content** — placeholder copy until Phase 6 replaces it.

## Deferred Ideas

- **Side PDF viewer for citations** — out of Phase 1; reconsidered at Phase 3 alongside methodology pane.
- **User-uploadable DRHP (E5)** — already deferred via TODOS.md; Phase 1 design must not preclude it (use `drhp_id` everywhere; don't hard-code single-IPO assumption).
- **Workflow follow-up requested by user:** After Phase 1 plan is generated, evaluate the gsd / gstack / superpowers skill roster and assign each set of tasks to the skill that excels at it before building. Surface once `/gsd-plan-phase 1` completes. NOT a Phase 1 implementation decision — session orchestration question.
