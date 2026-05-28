# Phase 1: Foundation + MVP-A (Cited Q&A on One IPO) - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

A publicly-deployed, mobile-responsive web app on Hugging Face Spaces where a user can pick one hand-loaded Indian mainboard IPO, ask plain-English questions about its DRHP, and receive grounded answers with clickable span-level citations — framed informational/educational only. Ships full SEBI-compliance posture, span-level citation infrastructure, agent traces carrying `claim_id` references from day one, and a stub `/methodology` page so resume deep-links don't 404 before Phase 6's recruiter landing page (LAND-01) replaces it.

**In scope:** One hand-loaded DRHP ingested + parsed + indexed; plain-English Q&A with span-level cited answers; refusal posture for un-grounded questions; compliance UI (modal + persistent footer + per-answer footer); banned-token scrubber; non-LLM cite-check node; `claim_id` trace persistence; mobile-responsive Streamlit UI; public HF Spaces deployment; `/methodology` stub link.

**Out of scope (other phases own these):** Multi-IPO catalogue (Phase 2); structured red-flag extraction (Phase 3); methodology pane UI (Phase 3, METHOD-01 — Phase 1 only persists the underlying trace data); peer comparison (Phase 4); historical IPO dataset (Phase 4); GMP display (Phase 4); listing-day forecaster (Phase 5); full eval dashboards inline (Phase 6); recruiter landing page (Phase 6, LAND-01); live failure gallery (Phase 6, FAILGAL-01); agentic multi-step Q&A (v1.x); user-uploadable DRHP (TODOS.md, E5).

</domain>

<decisions>
## Implementation Decisions

### Citation Chip Behavior

- **D-01:** Citation chips render as **superscript numbered chips `[1] [2] [3]`** in the answer text, anchored to a citation list at the bottom of the answer. Numbers reset per answer (no global counter).
- **D-02:** Clicking a chip **expands inline to show the cited DRHP source-text snippet** (Streamlit `st.expander` or equivalent), plus an external link to the SEBI/BSE/NSE-hosted DRHP PDF at the cited page. No side PDF viewer in Phase 1 — that's Phase 3 polish if at all.
- **D-03:** **Deduplicate chips at the answer surface**: if 3 sentences cite the same DRHP span, render ONE `[1]` chip after the cluster. The underlying `claim_id` traces still record each individual claim→source link separately so the Phase 3 methodology pane has full per-claim data.

### Refusal Posture (RAG-03)

- **D-04:** When the DRHP doesn't address the user's question, the system **hard-refuses AND suggests reformulation**: "This DRHP does not address X. Try asking about Y or Z, which the prospectus does cover." Reformulation suggestions come from the top retrieved sections (even when low-confidence for the original question).
- **D-05:** **Dual gate** triggers the refusal:
  - **Gate 1 (pre-LLM):** Max retrieval score (post-rerank) below a tuned threshold → refuse before any LLM generation call. Threshold tuned during Phase 1 against a small held-out eval set.
  - **Gate 2 (post-LLM):** Non-LLM cite-check node finds any claim in the generated answer without supporting retrieved evidence → block the answer, route to refusal copy.
  - Belt-and-suspenders; aligns with the cross-cutting invariant "non-LLM cite-check node validates every claim against the retrieved evidence set before emit."
- **D-06:** **Multi-part questions** where the DRHP addresses some parts but not others: **answer the grounded parts and explicitly flag the ungrounded ones**. E.g., "The DRHP addresses parts A and B — [cited answer]. It does not address part C; consider asking that separately." This requires the agent to decompose the question into sub-questions before retrieval — small added complexity, big honesty win.

### Disclaimer Copy + Style

- **D-07:** **Voice: honesty-first prose**, not lawyer template, not SEBI verbatim. Anchor copy (subject to legal-review polish before Phase 6 public launch):
  > "DRHPLens reads prospectuses for you. It cites what the document says and shows historical context. Decisions about investing are yours. This is not investment advice."
  Plain, declarative, on-brand. Still covers SEBI's required "not advice + informational only" ground.
- **D-08:** **Three surfaces** for prominence (matches SEBI Jan-2025 RA prominence requirement):
  - **First-use modal** on first visit (with "I understand" button persisted in localStorage / session state)
  - **Persistent slim footer** on every page (minimum 10pt equivalent in Streamlit's typography)
  - **Short per-answer footer** appended below every generated answer ("Informational only — not advice")
- **D-09:** Banned-token scrubber behavior is **planner discretion** — the cross-cutting invariant requires it; exact implementation (hard block + regenerate vs. soft rewrite) is the planner's call, with a strong default of hard-block-and-regenerate for honesty-first posture.

### Claude's Discretion

- **MVP-A IPO pick** — User let me decide. **Recommendation: Swiggy IPO (listed Nov 2024)** as the Phase 1 hand-loaded IPO. Rationale:
  - Globally and locally recognized brand → instant recruiter recognition.
  - DTC/tech sector with profitability concerns → rich risk-factor discussion in the DRHP, exactly the kind of document a retail investor would skim.
  - Listed Nov 2024 → public listing-day data + months of post-listing performance for later eval / Phase 5 calibration backtests.
  - The product's mission ("don't subscribe on hype") aligns perfectly with the Swiggy IPO narrative — there was substantial retail hype + plenty of legitimate caveats in the prospectus.
  - DRHP is publicly available on SEBI/BSE/NSE.
  - **Fallback candidates** if Swiggy doesn't work out for any reason: **Hyundai Motor India** (Oct 2024, biggest-ever Indian IPO, cleanest brand) or **Ola Electric** (Aug 2024, controversial EV with public discussion of risks). Lock the final pick at the start of the Phase 1 plan-phase.
- **Banned-token scrubber implementation strategy** (planner picks: hard-block-and-regenerate vs soft rewrite, exact banned-token list beyond the obvious subscribe/avoid/buy/sell/target/recommend).
- **Exact retrieval-score floor threshold** (D-05 Gate 1) — tuned empirically during Phase 1 with a small held-out eval set; planner specifies the calibration procedure.
- **Empty / loading / error UI states** (DRHP still indexing, LLM API timeout, Qdrant unavailable, rate limit hit) — standard patterns; planner specifies the copy and visual treatment.
- **`/methodology` stub page content** — placeholder until Phase 6 fills it. Planner default: brief project overview + "Methodology page coming with full eval dashboards in Phase 6" + link to the GitHub README. Final copy at planner's discretion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing Phase 1.**

### Project context
- `.planning/PROJECT.md` — Project core value, constraints, audience, key decisions, evolution rules
- `.planning/REQUIREMENTS.md` — 45 v1 requirements (13 in scope for Phase 1); see Traceability table for the exact subset
- `.planning/STATE.md` — Current project state + accumulated context + open TODOs
- `.planning/ROADMAP.md` — Phase 1 phase details, success criteria, cross-cutting invariants (especially the `claim_id` and span-level-citation invariants)
- `TODOS.md` — Deferred items (E5 user-upload threat-model requirements should be considered when designing the ingestion API even though E5 itself is out of scope)
- `/Users/adityasharma/.claude/plans/mighty-noodling-pretzel.md` — CEO review plan: implementation tasks T1-T7, Phase 1 specific notes (HF Spaces cold-start cron pinger, Qdrant 1GB index sizing)

### Research (read before researcher spawns)
- `.planning/research/SUMMARY.md` — Headline findings + roadmap implications + cross-cutting decisions
- `.planning/research/STACK.md` — Locked stack: LangGraph 1.2 + LlamaIndex 0.14 + Docling 2.95 + Qdrant + bge-m3 + Streamlit + HF Spaces. Versions, rationale, anti-patterns. India-specific data-source notes.
- `.planning/research/FEATURES.md` — Phase 1 in-scope features: table-stakes RAG + citations + anti-hallucination. v1 feature dependency graph.
- `.planning/research/ARCHITECTURE.md` — Component map; MVP-A vertical slice (which subset of the 19 components Phase 1 needs); batch-vs-on-demand split; cite-check node placement; storage-bus integration.
- `.planning/research/PITFALLS.md` — 5 CRITICAL pitfalls (SEBI advice boundary, hallucinated numbers, survivorship bias, GMP lookahead, citation drift). Phase 1 owns P1 (SEBI), P5 (citation drift), P19 (demo fragility), P20 (scope creep). Read warning signs + prevention strategies for each.

### External / regulatory
- **SEBI Jan-2025 Research Analyst guidelines** — Source: https://www.sebi.gov.in/legal/circulars/jan-2025/guidelines-for-research-analysts_90634.html — disclaimer prominence/font-size requirements, prohibited language. Referenced in PROJECT.md compliance constraints and PITFALLS.md P1.
- **Docling library docs** — current API for DRHP PDF parsing, table extraction. Verify against STACK.md versions during research phase.
- **Streamlit `st.expander` + `st.dialog` docs** — used for inline citation expansion and first-use modal respectively. Verify against STACK.md versions.

### Codebase
- No existing code (greenfield project). Codebase scout produced no maps.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. First phase establishes the patterns the rest of the project will build on.

### Established Patterns
- **Patterns to ESTABLISH in Phase 1** (these become the baseline for Phases 2-6):
  - Span-level citation data model: each generated claim emits a `claim_id` referencing the retrieval object; renderer resolves to the source text span and DRHP page anchor. This is the schema every downstream phase consumes.
  - Cite-check node: a deterministic (non-LLM) code node that runs AFTER LLM generation and BEFORE the answer is emitted to the user. It validates that every claim in the answer has a `claim_id` mapping to retrieved evidence; refuses the whole answer if not.
  - Storage bus: vector store (Qdrant Cloud, since HF Spaces is `/tmp`-only), relational store (SQLite or Postgres free tier), object store (HF Spaces dataset or similar for DRHP PDFs), run-log (Langfuse), feature store (deferred until Phase 5).
  - Disclaimer infrastructure: a `DisclaimerSurface` abstraction that renders the modal + footer + per-answer footer from a single source-of-truth copy block, so future copy edits don't require touching three call sites.
  - Banned-token scrubber: a deterministic filter run on every LLM output before cite-check (output → scrubber → cite-check → emit). Phase 1 lays this in even if the token list is small to start.

### Integration Points
- All Phase 1 components write to the storage bus; Phase 2+ on-demand tools read from it. Phase 1 must NOT introduce direct pipeline-to-pipeline calls (per ARCHITECTURE.md invariant).
- HF Spaces deployment surface — Phase 1 establishes the deployment pattern (Spaces config, secret management for Gemini/Groq/Qdrant Cloud keys, cold-start handling via cron pinger).

</code_context>

<specifics>
## Specific Ideas

- **Citation chip visual: superscript `[1] [2]`** matching the Perplexity / academic citation pattern. Mobile-first responsive.
- **Source-snippet expand: Streamlit `st.expander`** below the answer; each expander shows the verbatim DRHP text span + DRHP page link.
- **First-use modal: Streamlit `st.dialog`** (requires Streamlit 1.32+ per STACK.md; verify version).
- **Disclaimer anchor copy** for Phase 1 v0 (subject to legal-review polish before Phase 6 public launch):
  > "DRHPLens reads prospectuses for you. It cites what the document says and shows historical context. Decisions about investing are yours. This is not investment advice."
- **MVP-A IPO recommended: Swiggy IPO (Nov 2024)** — see Claude's Discretion above for rationale and fallback candidates.

</specifics>

<deferred>
## Deferred Ideas

- **User-uploadable DRHP path (E5)** — already deferred to `TODOS.md`. Re-flagged here because while *out of scope for Phase 1*, the Phase 1 ingestion API design should NOT preclude E5: avoid hard-coding the single-IPO assumption deep into the data model. Use an `drhp_id` foreign key everywhere; index multiple DRHPs in Qdrant from day one even if only one is exposed in Phase 1.
- **Multi-IPO catalogue browsing** — Phase 2 (SNAP-01).
- **Agentic multi-step Q&A** — v1.x trigger: faithfulness > 0.85 on a hand-labeled gold Q&A set.
- **Hindi mode (E4)** — TODOS.md / v2 trajectory.
- **Compare two open IPOs (E3 / MULTI-IPO-COMPARE-01)** — v2.
- **Side PDF viewer for citations (`streamlit-pdf-viewer`)** — deferred from Phase 1 to Phase 3 (alongside the methodology pane); inline expand is sufficient for v1.

### Workflow follow-up (not a phase deferral)
- **Skill-roster optimization**: User requested that after the Phase 1 plan is generated, we evaluate the gsd / gstack / superpowers skill roster and assign each set of tasks to the skill that excels at it before building. To be surfaced once `/gsd-plan-phase 1` completes — not a Phase 1 implementation decision but a session-orchestration follow-up.

</deferred>

---

*Phase: 1-Foundation + MVP-A (Cited Q&A on One IPO)*
*Context gathered: 2026-05-28*
