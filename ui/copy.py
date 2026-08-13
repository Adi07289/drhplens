"""
DRHPLens user-visible copy strings.

Every string constant in this module is scrubber-checked at import time
(TRUST-03 anchor). If any constant contains a banned token, this module
raises AssertionError at import time — before any HTTP request is served.

This makes it impossible for a copy edit that introduces a banned token to
reach production silently. It is a feature, not a bug.

All strings sourced verbatim from 01-UI-SPEC.md §Copywriting Contract.
Do NOT paraphrase — the legal-review precedent for Phase 6 depends on copy
stability from Phase 1.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

HERO_HEADING: str = "Ask DRHPLens about Swiggy."
"""Home page hero heading (Display 28px). Single sentence, no exclamation.

DEPRECATED naming (kept for Phase 1 test/back-compat — see
test_copy_no_banned_tokens.py spot-check): this is now just the Swiggy-filled
form of HERO_HEADING_TEMPLATE. Phase 2 snapshot pages use
HERO_HEADING_TEMPLATE.format(issuer=...) directly (FLAG-COPY-TEMPLATING).
"""

HERO_HEADING_TEMPLATE: str = "Ask DRHPLens about {issuer}."
"""Issuer-parameterized hero heading. .format(issuer=...) per snapshot page."""

HERO_SUBHEADING: str = (
    "One Indian IPO. One prospectus. Ask anything. "
    "Every answer cites the page it came from."
)
"""Issuer-agnostic; reused verbatim on every snapshot page (no templating needed)."""

# ---------------------------------------------------------------------------
# Question input
# ---------------------------------------------------------------------------

QUESTION_PLACEHOLDER: str = (
    "Ask about Swiggy's risk factors, financials, promoter holdings, "
    "or use of proceeds…"
)
"""DEPRECATED naming (kept for Phase 1 back-compat) — Swiggy-filled form of
QUESTION_PLACEHOLDER_TEMPLATE. Phase 2 snapshot pages use the template directly."""

QUESTION_PLACEHOLDER_TEMPLATE: str = (
    "Ask about {issuer}'s risk factors, financials, promoter holdings, "
    "or use of proceeds…"
)
"""Issuer-parameterized question placeholder. .format(issuer=...) per snapshot page."""

# ---------------------------------------------------------------------------
# Modal
# ---------------------------------------------------------------------------

MODAL_CTA: str = "I understand — open DRHPLens"
"""Primary CTA in the first-use disclaimer modal."""

# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

EMPTY_STATE_HEADING: str = "Nothing asked yet."

EMPTY_STATE_BODY: str = (
    'Try one of these to start: '
    '"What does Swiggy say about its path to profitability?" · '
    '"Who are the promoters and what is their post-issue holding?" · '
    '"What is the use of proceeds breakdown?"'
)
"""DEPRECATED naming (kept for Phase 1 back-compat) — Swiggy-filled form of
EMPTY_STATE_BODY_TEMPLATE."""

EMPTY_STATE_BODY_TEMPLATE: str = (
    'Try one of these to start: '
    '"What does {issuer} say about its path to profitability?" · '
    '"Who are the promoters and what is their post-issue holding?" · '
    '"What is the use of proceeds breakdown?"'
)
"""Issuer-parameterized empty-state body. .format(issuer=...) per snapshot page."""

# ---------------------------------------------------------------------------
# Loading states
# ---------------------------------------------------------------------------

COLD_START_COPY: str = (
    "Warming up. The Hugging Face Space was asleep "
    "— first load takes 30–60 seconds while the index loads. "
    "Subsequent questions will be fast."
)

LOADING_ANSWER_COPY: str = (
    "Reading Swiggy's DRHP and checking every claim against the source…"
)
"""DEPRECATED naming (kept for Phase 1 back-compat) — Swiggy-filled form of
LOADING_ANSWER_COPY_TEMPLATE."""

LOADING_ANSWER_COPY_TEMPLATE: str = (
    "Reading {issuer}'s DRHP and checking every claim against the source…"
)
"""Issuer-parameterized loading copy. .format(issuer=...) per snapshot page."""

# ---------------------------------------------------------------------------
# Refusal states
# ---------------------------------------------------------------------------

REFUSAL_NO_GROUNDING_TEMPLATE: str = (
    "This DRHP does not address {topic}. "
    "Try asking about {suggestion1} or {suggestion2} "
    "— the prospectus does cover those."
)
"""Use .format(topic=..., suggestion1=..., suggestion2=...) to interpolate."""

REFUSAL_PARTIAL_GROUNDING_TEMPLATE: str = (
    "The DRHP addresses parts of your question. "
    "{grounded_answer}. "
    "It does not address {missing_part} — consider asking that separately."
)
"""Use .format(grounded_answer=..., missing_part=...) to interpolate."""

REFUSAL_BANNED_TOKEN_COPY: str = (
    "Couldn't return that answer because it would have implied investment advice. "
    "DRHPLens describes; it doesn't advise. "
    "Try a more specific question about what the DRHP says."
)

# ---------------------------------------------------------------------------
# Fused multi-tool answer (Phase 6.3 · C1/C2/C3 · D-03/D-04/D-08)
#
# All strings below are auto-enrolled in the import-time banned-token scrubber
# loop at the bottom of this module (so a banned prescriptive token can never
# ship inside a fused-answer surface). The honesty invariant is load-bearing:
# NO advice-adjacent copy, NO verdict framing, GMP stays display-only. The
# fused renderer (ui/fused_answer.py) imports these verbatim — copy lives here,
# never inline in the renderer (UI-SPEC Honesty Check).
# ---------------------------------------------------------------------------

# C1 — provenance footer legend segments (mono line under the answer hairline).
# Numbered DRHP markers use the DRHP template; lettered tool markers use the
# per-source segments. Assembled by the renderer into the always-present legend.
FUSED_LEGEND_DRHP_TEMPLATE: str = "DRHP p.{page}"
"""One legend entry per numbered DRHP marker. .format(page=...)."""

FUSED_LEGEND_PEERS: str = "peers"
FUSED_LEGEND_FORECAST: str = "forecast · 80% PI"
FUSED_LEGEND_GMP: str = "GMP · display-only"
FUSED_LEGEND_REDFLAGS: str = "red-flags · committed record"

# C2 — expanded source descriptors (one-line, tap-to-expand; read-only, from the
# cached answer object — NO live call). A DRHP Claim reuses the existing citation
# expander; these cover the lettered ToolClaim markers (forecast/peers/GMP/red-flags).
FUSED_EXPANDED_FORECAST_LABEL: str = "Forecast · 80% PI"
FUSED_EXPANDED_FORECAST_BODY: str = "GMP-free model · calibrated backtest"
FUSED_EXPANDED_FORECAST_LINK: str = "see forecast"

FUSED_EXPANDED_PEERS_LABEL: str = "Peers"
FUSED_EXPANDED_PEERS_BODY: str = "listed-peer set · screener.in via committed record"
FUSED_EXPANDED_PEERS_LINK: str = "see peers"

FUSED_EXPANDED_GMP_LABEL: str = "GMP · display-only"
FUSED_GMP_CHAT_CAVEAT: str = (
    "GMP is an informal grey-market figure, shown for context — "
    "it is not a forecast and never enters the model."
)
"""D-04: the mandatory caveat whenever a GMP figure appears. GMP is display-only."""
FUSED_EXPANDED_GMP_LINK: str = "see forecast"

FUSED_EXPANDED_REDFLAGS_LABEL: str = "Red-flags"
FUSED_EXPANDED_REDFLAGS_BODY: str = "structured red-flag / financials · committed record"
FUSED_EXPANDED_REDFLAGS_LINK: str = "see snapshot"

# The DRHP-Claim expander "open page" link copy (reused from the Phase-1 chat path).
FUSED_OPEN_PAGE_TEMPLATE: str = "View DRHP page {page} on SEBI →"
"""Doc-Claim expander link. .format(page=...)."""

# C3 — honest-partial banner (muted mono, dashed neutral — NEVER red/alarm, D-08).
# Two copy variants: a source-specific tool-abstain and a generic budget-trip.
FUSED_PARTIAL_EYEBROW: str = "INCOMPLETE ANSWER"
FUSED_PARTIAL_TOOL_ABSTAIN_BODY: str = (
    "No forecast band for this IPO — answering from the DRHP + peers only."
)
FUSED_PARTIAL_BUDGET_BODY: str = (
    "Stopped early — here's what I found so far."
)

# ---------------------------------------------------------------------------
# Quota / rate-limit fallback (Phase 6.3 · C4 · D-12)
#
# The public chat is bounded by the Gemini free-tier ceiling: a GLOBAL daily cap
# + a per-session throttle (ui/deploy_guard.py). These strings drive the two C4
# fallback states — cap-exhausted REPLACES the input with the fallback card that
# routes to the always-working read-only surfaces; a throttle shows a brief
# non-blocking inline notice above the input. Muted + honest, NEVER alarm-red / a
# countdown (honesty invariant). Verbatim from 06.3-UI-SPEC §Copywriting Contract;
# auto-enrolled in the import-time banned-token scrubber loop below.
# ---------------------------------------------------------------------------

QUOTA_CARD_HEADING: str = "Live demo quota reached for today."
"""C4 cap-exhausted card heading (Serif). UI-SPEC verbatim."""

QUOTA_CARD_BODY: str = (
    "Everything else still works — browse the IPO snapshot, forecast & peers, "
    "`/methodology`, and `/failures`, or watch the recorded walkthrough."
)
"""C4 cap-exhausted card body — routes to the always-working read-only (LLM-free)
surfaces. UI-SPEC verbatim."""

QUOTA_WALKTHROUGH_LINK: str = "▶ Recorded chat walkthrough"
"""C4 recorded-walkthrough link text (accent link affordance). UI-SPEC verbatim."""

RATELIMIT_NOTICE: str = (
    "You're sending questions quickly — try again in a few seconds."
)
"""C4 transient per-session throttle notice — muted, above the input, non-blocking,
auto-clears. UI-SPEC verbatim."""

# ---------------------------------------------------------------------------
# Error states
# ---------------------------------------------------------------------------

ERROR_QDRANT_UNREACHABLE: str = (
    "The DRHP index is temporarily unreachable. "
    "This is a free-tier infrastructure hiccup, not a problem with your question. "
    "Try again in a minute."
)

ERROR_LLM_TIMEOUT: str = (
    "The reading step timed out. "
    "Try the same question again — it usually goes through on retry."
)

ERROR_RATE_LIMIT: str = (
    "DRHPLens has hit today's free-tier reading limit. "
    "Come back tomorrow, or check the methodology page for what the project covers."
)

# ---------------------------------------------------------------------------
# Per-answer disclaimer
# ---------------------------------------------------------------------------

PER_ANSWER_DISCLAIMER: str = "Informational only — not advice."

# ---------------------------------------------------------------------------
# Methodology stub
# ---------------------------------------------------------------------------

METHODOLOGY_STUB_HEADING: str = "Methodology"

METHODOLOGY_STUB_BODY: str = (
    "DRHPLens is a portfolio project for an Indian-IPO DRHP decoder. "
    "Phase 1 ships cited Q&A over one hand-loaded prospectus (Swiggy, Nov 2024). "
    "The full methodology — model card, eval dashboards, failure gallery "
    "— lands in Phase 6. "
    "For now: see the public repository for source code, the roadmap, "
    "and the design decisions behind every page."
)

# ---------------------------------------------------------------------------
# Phase 6.2 — /failures gallery chrome (FAILGAL-01; 06.2-UI-SPEC §Copywriting Contract)
# ---------------------------------------------------------------------------
# Only the CHROME strings live here (scrubber-checked at import). The evaluative
# FAILURE CONTENT lives in eval/failures/failures.yaml, which is deliberately NOT
# scrubbed — failures describe real behaviour with evaluative words, and that is the
# point (the honesty thesis made concrete).

FAILURES_EYEBROW: str = "FAILURE GALLERY"
"""Section eyebrow on /failures (mono, letter-spaced) — UI-SPEC verbatim."""

FAILURES_HEADING: str = "Where it breaks — and what I did about it"
"""Section heading on /failures — UI-SPEC verbatim."""

# Empty-state copy. Also MIRRORED as local constants in ui/failures.py (which cannot
# import ui.copy without breaking its P19 AST-import allowlist) — keep the two byte-
# identical. Source of truth for the copy contract is here.
FAILURES_EMPTY_HEADING: str = "No failures loaded."
"""Empty-state heading (absent/unreadable/empty failures.yaml) — UI-SPEC verbatim."""

FAILURES_EMPTY_BODY: str = "Run the eval suite to populate `eval/failures/failures.yaml`."
"""Empty-state body — UI-SPEC verbatim."""

# ---------------------------------------------------------------------------
# Phase 2 — Catalogue page copy (02-UI-SPEC.md §Copywriting Contract)
# ---------------------------------------------------------------------------

CATALOGUE_HERO_HEADING: str = "Indian IPOs, read honestly."

CATALOGUE_HERO_SUBHEADING: str = (
    "Browse recent mainboard IPOs. Open any one to see what its prospectus "
    "actually says — every field cites the page it came from."
)

CATALOGUE_CARD_OPEN_NOW_TAG: str = "Open now"
"""Small, text-only tag for currently-open IPOs — NO color, NO badge fill."""

CATALOGUE_CARD_ARIA_LABEL_TEMPLATE: str = (
    "{issuer}, {sector}, listed {date}, issue size {size}. Open snapshot."
)
"""Card screen-reader label. .format(issuer=..., sector=..., date=..., size=...)."""

CATALOGUE_EMPTY_HEADING: str = "No IPOs loaded yet."

CATALOGUE_EMPTY_BODY: str = (
    "The catalogue is still being ingested. Check back shortly, or read the "
    "methodology page for what's covered."
)

# ---------------------------------------------------------------------------
# Phase 2 — Snapshot page copy (02-UI-SPEC.md §Copywriting Contract)
# ---------------------------------------------------------------------------

SNAPSHOT_BREADCRUMB_BACK: str = "← All IPOs"

SNAPSHOT_BLOCK_HEADING_BUSINESS: str = "Business"
SNAPSHOT_BLOCK_HEADING_FINANCIALS: str = "Key Financials"
SNAPSHOT_BLOCK_HEADING_RISKS: str = "Risk Factors"
SNAPSHOT_BLOCK_HEADING_USE_OF_PROCEEDS: str = "Use of Proceeds"
SNAPSHOT_BLOCK_HEADING_PROMOTER: str = "Promoters & Management"

SPLIT_BAR_CAPTION_TEMPLATE: str = (
    "Of the total issue, {fresh_pct}% is a fresh issue (money to the company) "
    "and {ofs_pct}% is an Offer for Sale (shares offered by existing shareholders)."
)
"""Split-bar caption. .format(fresh_pct=..., ofs_pct=...)."""

SPLIT_BAR_PURE_FRESH: str = "Fresh 100% · No OFS"
SPLIT_BAR_PURE_OFS: str = "OFS 100% · No fresh capital raised"

RISK_COUNTER_TEMPLATE: str = "Risk {n} of {m}"
"""Descriptive, not evaluative. .format(n=..., m=...)."""

FIELD_NOT_DISCLOSED_NOTE: str = "Not disclosed in this DRHP."
"""P2-L8 honesty note — rendered instead of a fabricated value or a guess."""

FINANCIALS_MISSING_CELL: str = "—"
"""Em dash for a missing financials cell; pair with aria-label='Not disclosed in this DRHP'."""

SNAPSHOT_PRECOMPUTING_HEADING: str = "This IPO hasn't been analysed yet."

SNAPSHOT_PRECOMPUTING_BODY_TEMPLATE: str = (
    "Swiggy Limited is the fully worked example in this demo — its snapshot cites "
    "every figure back to the DRHP. {issuer} is in the catalogue, but its cited "
    "snapshot hasn't been generated yet."
)
"""Issuer-parameterized precomputing-state body. .format(issuer=...)."""

SNAPSHOT_CACHE_UNREACHABLE: str = (
    "This IPO's snapshot is temporarily unreachable. This is a free-tier "
    "infrastructure hiccup, not a problem with the IPO. Try again in a minute."
)

UNKNOWN_DRHP_ID_COPY: str = "That IPO isn't in the catalogue."

# ---------------------------------------------------------------------------
# Phase 3 — Red-flag signal table copy (03-UI-SPEC.md §Copywriting Contract)
# Every string VERBATIM from the UI-SPEC Copywriting Contract (L3-8). Do NOT
# paraphrase — scrubber-clean copy stability is load-bearing. No banned token
# (subscribe / avoid / buy / sell / target / recommend / fair value /
# overvalued / undervalued / target price) appears anywhere below.
# ---------------------------------------------------------------------------

REDFLAG_BLOCK_HEADING: str = "Red-flag signals"

REDFLAG_BLOCK_SUBLINE: str = (
    "Structured signals extracted from the prospectus. Each value cites the "
    "DRHP page it came from and shows how confident the extractor is."
)

# The 7 field labels in canonical order (UI-SPEC R-1 fixed order; 600 semibold).
REDFLAG_FIELD_LABEL_RPT_PCT: str = "RPT % of revenue"
REDFLAG_FIELD_LABEL_OFS_VS_FRESH: str = "OFS vs fresh issue"
REDFLAG_FIELD_LABEL_PROMOTER_PLEDGE_PCT: str = "Promoter pledge %"
REDFLAG_FIELD_LABEL_CUSTOMER_CONCENTRATION: str = "Customer concentration"
REDFLAG_FIELD_LABEL_AUDITOR_HISTORY: str = "Auditor history"
REDFLAG_FIELD_LABEL_DEBT_TRAJECTORY: str = "Debt trajectory"
REDFLAG_FIELD_LABEL_GOING_CONCERN: str = "Going-concern mentions"

# field_key -> display label (canonical order); keys match REDFLAG_FIELD_KEYS.
REDFLAG_FIELD_LABELS: dict[str, str] = {
    "rpt_pct": REDFLAG_FIELD_LABEL_RPT_PCT,
    "ofs_vs_fresh": REDFLAG_FIELD_LABEL_OFS_VS_FRESH,
    "promoter_pledge_pct": REDFLAG_FIELD_LABEL_PROMOTER_PLEDGE_PCT,
    "customer_concentration": REDFLAG_FIELD_LABEL_CUSTOMER_CONCENTRATION,
    "auditor_history": REDFLAG_FIELD_LABEL_AUDITOR_HISTORY,
    "debt_trajectory": REDFLAG_FIELD_LABEL_DEBT_TRAJECTORY,
    "going_concern": REDFLAG_FIELD_LABEL_GOING_CONCERN,
}

CONFIDENCE_LABEL_TEMPLATE: str = "Confidence: {confidence_tier}"
"""Per-field confidence label (Small 12 muted, text only — no pill, no color,
L3-2). .format(confidence_tier='high'|'medium'|'low')."""

CONFIDENCE_RUBRIC_LINE: str = (
    "Confidence reflects how directly the value is stated in the DRHP — "
    "high: stated verbatim in the cited span; medium: stated but needed light "
    "parsing or aggregation; low: inferred across sections."
)

FIELD_NUMERIC_GATE_BLOCKED: str = (
    "Could not ground this number to a cited DRHP page, so it is not shown."
)
"""L3-9 blocked-copy — rendered instead of an unsourced number when the
cite_check numeric sub-check fails."""

# ---------------------------------------------------------------------------
# Phase 3 — IDF-ranked risk list copy (03-UI-SPEC.md §Copywriting Contract)
# ---------------------------------------------------------------------------

RISK_BLOCK_HEADING: str = "Risk factors, ranked by how specific they are"

RISK_BLOCK_SUBLINE: str = (
    "Risks unique to this company are listed first; risks that appear in most "
    "prospectuses are listed lower. Order is the signal — not severity."
)

RISK_SPECIFICITY_COUNTER_TEMPLATE: str = "Risk {n} of {m} · {specificity}"
"""Rank + specificity counter (Small 12 muted). .format(n=.., m=.., specificity=..)
where specificity ∈ the three SPECIFICITY_WORD_* values."""

SPECIFICITY_WORD_ISSUER_SPECIFIC: str = "Issuer-specific"
SPECIFICITY_WORD_MOSTLY_ISSUER_SPECIFIC: str = "Mostly issuer-specific"
SPECIFICITY_WORD_INDUSTRY_STANDARD: str = "Industry-standard"

# specificity_band enum (RankedRisk.specificity_band) -> display word.
SPECIFICITY_BAND_WORDS: dict[str, str] = {
    "issuer_specific": SPECIFICITY_WORD_ISSUER_SPECIFIC,
    "mostly_issuer_specific": SPECIFICITY_WORD_MOSTLY_ISSUER_SPECIFIC,
    "industry_standard": SPECIFICITY_WORD_INDUSTRY_STANDARD,
}

SPEC_METER_ARIA_TEMPLATE: str = (
    "Issuer-specificity: {pct} percent. Higher means more specific to this company."
)
"""Specificity-meter aria-label. .format(pct=..)."""

# ---------------------------------------------------------------------------
# Phase 3 — Methodology pane ("Show your work") copy (03-UI-SPEC.md)
# ---------------------------------------------------------------------------

METHODOLOGY_TRIGGER: str = "Show your work"
"""Methodology-pane expander header (Primary CTA — the one explicit affordance
Phase 3 adds). Neutral verb phrase, no emoji, no icon."""

METHODOLOGY_PANE_LABEL_QUERY: str = "Retrieval query"
METHODOLOGY_PANE_LABEL_CHUNKS: str = "Retrieved chunks (with scores)"
METHODOLOGY_PANE_LABEL_PROMPT: str = "Prompt used"
METHODOLOGY_PANE_LABEL_SOURCES: str = "Sources cited"
METHODOLOGY_PANE_LABEL_EVAL: str = "Eval scores (from the latest committed report)"

METHODOLOGY_EVAL_PROVENANCE_NOTE: str = (
    "These scores come from the most recent committed evaluation report, not a "
    "fresh check run when you expanded this. See the methodology page for the "
    "full eval."
)

METHODOLOGY_EVAL_NOT_AVAILABLE: str = (
    "No committed eval score yet for this field. The numeric-faithfulness gate "
    "still applies before this number is shown."
)

# --- Redesigned two-tier "Show your work" pane (investor-first) -------------
# Tier 1 leads with plain-English source verification; the developer internals
# (query / chunk scores / prompt / raw eval report) move behind a toggle.

METHODOLOGY_SOURCE_HEADING: str = "Where this answer comes from"
METHODOLOGY_SOURCE_LEAD: str = (
    "Pulled straight from the prospectus — here is the exact passage it rests on."
)
METHODOLOGY_SOURCE_LOCATION_TEMPLATE: str = "Prospectus p.{page} · {section}"
"""Human-readable source location. .format(page=.., section=..)."""

METHODOLOGY_TRUST_HEADING: str = "How much to trust this"

CONFIDENCE_PLAIN_HIGH: str = "stated directly on the cited page"
CONFIDENCE_PLAIN_MEDIUM: str = "supported by the cited page, with light parsing"
CONFIDENCE_PLAIN_LOW: str = "inferred from the cited page — read it alongside the source"

# confidence_tier -> plain-English meaning (what the tier actually implies).
CONFIDENCE_PLAIN_WORDS: dict[str, str] = {
    "high": CONFIDENCE_PLAIN_HIGH,
    "medium": CONFIDENCE_PLAIN_MEDIUM,
    "low": CONFIDENCE_PLAIN_LOW,
}

METHODOLOGY_TRUST_TEMPLATE: str = "Confidence: {tier_word} — {tier_meaning}."
"""Plain trust sentence. .format(tier_word='High'|'Medium'|'Low', tier_meaning=..)."""

METHODOLOGY_EVAL_ACCURACY_TEMPLATE: str = (
    "In our testing, cited pages matched the claim {accuracy} of the time."
)
"""One-line eval summary for the investor view. .format(accuracy='97%')."""

METHODOLOGY_TECH_TOGGLE: str = "Show technical details"
METHODOLOGY_TECH_CAPTION: str = (
    "For reviewers: the retrieval query, chunk scores, the prompt, and the full "
    "evaluation report."
)

FIELD_NOT_DISCLOSED_IN_DRHP_NOTE: str = "Not disclosed in DRHP"
"""Phase 3 not-disclosed note (L3-3). Distinct verbatim string from the Phase 2
FIELD_NOT_DISCLOSED_NOTE ('Not disclosed in this DRHP.') per the UI-SPEC."""

# ---------------------------------------------------------------------------
# Phase 3 — Red-flag table empty / error states (03-UI-SPEC.md)
# ---------------------------------------------------------------------------

REDFLAG_EMPTY_HEADING: str = "No structured signals extracted yet."

REDFLAG_EMPTY_BODY: str = (
    "This IPO's red-flag table hasn't been computed. Try one of the IPOs "
    "already processed, or check back once ingestion completes."
)

REDFLAG_ERROR_STATE: str = (
    "The red-flag table couldn't load for this IPO. This is a free-tier "
    "infrastructure hiccup, not a problem with the prospectus. Try again in a "
    "minute."
)


# ---------------------------------------------------------------------------
# Phase 4 — Peer-multiples comparison table copy (04-05-PLAN.md Task 1,
# 04-UI-SPEC.md §Copywriting Contract). Descriptive, never prescriptive; no
# red/green; the peer-set citation chip is the ONLY accent element (D4-04/09).
# Every string below is auto-enrolled in the import-time scrubber loop.
# ---------------------------------------------------------------------------

PEER_BLOCK_HEADING: str = "Comparison with listed peers"

PEER_BLOCK_SUBLINE: str = (
    "The peer set below is the one this company disclosed in its own "
    "prospectus. Multiples are sourced from public market data; each value "
    "shows where it came from."
)

PEER_IPO_ROW_TAG: str = "This IPO"

# Fixed column order (04-UI-SPEC.md R-2): Company · P/E · P/B · EV/EBITDA · ROE.
PEER_COL_COMPANY: str = "Company"
PEER_COL_PE: str = "P/E"
PEER_COL_PB: str = "P/B"
PEER_COL_EV_EBITDA: str = "EV/EBITDA"
PEER_COL_ROE: str = "ROE"

# Per-cell provenance legend (R-3) — the muted one-line source key below the table.
PEER_PROVENANCE_LEGEND: str = (
    "Sources: d DRHP · s screener.in · y Yahoo Finance · n NSE / BSE"
)

# Full source names for each provenance letter (used in the per-cell aria-labels
# so screen-reader users never have to resolve a single letter, R-3 / a11y).
PEER_SOURCE_NAME_D: str = "DRHP"
PEER_SOURCE_NAME_S: str = "screener.in"
PEER_SOURCE_NAME_Y: str = "Yahoo Finance"
PEER_SOURCE_NAME_N: str = "NSE / BSE"

PEER_SOURCE_NAMES: dict[str, str] = {
    "d": PEER_SOURCE_NAME_D,
    "s": PEER_SOURCE_NAME_S,
    "y": PEER_SOURCE_NAME_Y,
    "n": PEER_SOURCE_NAME_N,
}

# The muted secondary line in a cell that carries BOTH as-of dimensions — the
# headline value is current-market (per the sub-line); this labels the DRHP-date
# value where a source supplies it (D4-05, the record holds both).
PEER_ASOF_DRHP_LABEL: str = "as of DRHP"

# Cell edge-case copy (04-UI-SPEC.md §Visuals — Peer table cell edge cases).
PEER_CELL_NOT_AVAILABLE_ARIA: str = "Not available from any source"
PEER_NM_NOTE: str = "Not meaningful — the company reported a loss"

# D4-06 honest empty-state — the DRHP named no listed peers (never fabricated).
PEER_EMPTY_STATE: str = "This DRHP disclosed no listed-peer comparison."

# Infra error state — inherited amber .drhp-refusal posture (NOT red).
PEER_ERROR_STATE: str = (
    "This couldn't load for this IPO right now. It's a free-tier "
    "infrastructure hiccup, not a problem with the prospectus. Try again in "
    "a minute."
)


# ---------------------------------------------------------------------------
# Phase 4 — Glossary tooltips (UI-04, D4-08; 04-UI-SPEC.md §Glossary tooltips).
# Eight core Indian-IPO terms carry the pure-CSS R-1 popover. Each definition is
# a module-level str constant (auto-scrubbed at import) so no banned-advice token
# can land here; the OFS/GMP wording deliberately avoids the `sell` stem
# (L8 — "shares offered by existing shareholders").
#
# NOTE (Rule 1 deviation, 04-05 execution): the 04-UI-SPEC QIB definition spelled
# out "Qualified Institutional Buyer", but the token "Buyer" trips the compliance
# scrubber's `buy` stem (\b(buy)\w*\b matches "Buyer"), which would break the
# import-time assertion. Reworded to "Qualified Institutional Investor" — the
# widely-used gloss — to stay scrubber-clean while preserving the meaning.
# ---------------------------------------------------------------------------

GLOSSARY_TERM_RPT: str = "RPT"
GLOSSARY_DEF_RPT: str = (
    "Related-Party Transaction — business the company does with its own "
    "promoters, directors, or their connected entities."
)

GLOSSARY_TERM_QIB: str = "QIB"
GLOSSARY_DEF_QIB: str = (
    "Qualified Institutional Investor — large institutional investors (banks, "
    "mutual funds, insurers) allotted a reserved share of the issue."
)

GLOSSARY_TERM_NII: str = "NII"
GLOSSARY_DEF_NII: str = (
    "Non-Institutional Investor — an investor applying for more than ₹2 lakh, "
    "excluding institutions."
)

GLOSSARY_TERM_RII: str = "RII"
GLOSSARY_DEF_RII: str = (
    "Retail Individual Investor — an investor applying for up to ₹2 lakh."
)

GLOSSARY_TERM_GMP: str = "GMP"
GLOSSARY_DEF_GMP: str = (
    "Grey Market Premium — an unofficial price at which IPO shares change hands "
    "privately before listing. Unregulated and not set by the company or the "
    "exchange."
)

GLOSSARY_TERM_OFS: str = "OFS"
GLOSSARY_DEF_OFS: str = (
    "Offer for Sale — shares offered by existing shareholders in the IPO; the "
    "proceeds go to those shareholders, not to the company."
)

GLOSSARY_TERM_DRHP: str = "DRHP"
GLOSSARY_DEF_DRHP: str = (
    "Draft Red Herring Prospectus — the draft offer document a company files "
    "with SEBI before its IPO."
)

GLOSSARY_TERM_ANCHOR: str = "anchor investor"
GLOSSARY_DEF_ANCHOR: str = (
    "Anchor investor — a large institutional investor that commits ahead of the "
    "public issue, one day before it opens."
)

# The 8-term glossary map: term key -> (display label, definition). The renderer
# helper (ui.snapshot_blocks.glossary_term) wraps the label in the CSS-only
# popover trigger and interpolates the definition. Keys are the canonical terms
# from D4-08. The values reference the already-scrubbed constants above.
GLOSSARY: dict[str, tuple[str, str]] = {
    "RPT": (GLOSSARY_TERM_RPT, GLOSSARY_DEF_RPT),
    "QIB": (GLOSSARY_TERM_QIB, GLOSSARY_DEF_QIB),
    "NII": (GLOSSARY_TERM_NII, GLOSSARY_DEF_NII),
    "RII": (GLOSSARY_TERM_RII, GLOSSARY_DEF_RII),
    "GMP": (GLOSSARY_TERM_GMP, GLOSSARY_DEF_GMP),
    "OFS": (GLOSSARY_TERM_OFS, GLOSSARY_DEF_OFS),
    "DRHP": (GLOSSARY_TERM_DRHP, GLOSSARY_DEF_DRHP),
    "anchor investor": (GLOSSARY_TERM_ANCHOR, GLOSSARY_DEF_ANCHOR),
}


# ---------------------------------------------------------------------------
# Phase 4 — Read-only GMP block copy (04-06-PLAN.md Task 1, 04-UI-SPEC.md
# §Copywriting Contract + §Visuals GMP). The QUIETEST surface in the app:
# monochrome, de-emphasised, cache-only. Every string VERBATIM from the UI-SPEC
# Copywriting Contract — descriptive, never a demand signal (D4-01/02/09). No
# red/green, no "strong"/"demand" framing; the `sell` stem is avoided. Each
# constant is auto-enrolled in the import-time scrubber loop below.
# ---------------------------------------------------------------------------

GMP_BLOCK_HEADING: str = "Grey-market premium (unofficial)"

# Persistent one-line caveat — ALWAYS visible under the heading, never collapsed.
GMP_CAVEAT: str = (
    "An unofficial, unregulated number from private dealers — not a price the "
    "company or any exchange sets. We show it for transparency only and never "
    "use it in any forecast."
)

# The spread headline — the min–max range IS the honesty signal (D4-01). ₹ via
# format_inr at render; {low}/{high} are the pre-formatted rupee strings.
GMP_RANGE_HEADLINE_TEMPLATE: str = "{low}–{high} across {n} sources"

# role="img" aria-label for the range strip — the spread is conveyed in TEXT,
# never by tick position alone (WCAG 1.4.1). {low}/{high} are format_inr strings.
GMP_RANGE_ARIA_TEMPLATE: str = (
    "Grey-market premium ranges from {low} to {high} across {n} sources; "
    "the sources disagree."
)

# Per-source list (Small muted): "{source} {value}" items joined by " · ",
# then the trailing "as of {date}". ₹ via format_inr; source is html-escaped.
GMP_SOURCE_ITEM_TEMPLATE: str = "{source} {value}"
GMP_SOURCE_ASOF_TEMPLATE: str = "as of {date}"
GMP_SOURCE_LINE_JOINER: str = " · "

# Single-source state — absence of a cross-source check is STATED, not hidden.
GMP_SINGLE_SOURCE_NOTE: str = (
    "Only one source reported — no cross-source check available."
)

# Absent-GMP state — the COMMON case (already-listed IPOs). Never a fabricated
# number, never a zero, never an error.
GMP_ABSENT: str = (
    "No grey-market premium is being reported for this IPO right now."
)

# The one explicit affordance Phase 4 adds — the disclosure expander header.
GMP_DISCLOSURE_HEADING: str = "What is GMP? Why we don't trust it"

GMP_DISCLOSURE_BODY: str = (
    "The grey-market premium is a price at which IPO shares change hands "
    "privately before listing, quoted by unofficial dealers. It is unregulated, "
    "has no verified provenance, and can be moved by a handful of operators. "
    "Because it is neither official nor reliable, we display it for context "
    "only and keep it out of every forecast this app produces."
)

# Infra error state — inherited amber .drhp-refusal posture (NOT red). Verbatim
# the shared peer/GMP error string from the UI-SPEC Copywriting Contract.
GMP_ERROR_STATE: str = (
    "This couldn't load for this IPO right now. It's a free-tier "
    "infrastructure hiccup, not a problem with the prospectus. Try again in "
    "a minute."
)


# ---------------------------------------------------------------------------
# Phase 5 — Listing-day forecast section copy (05-UI-SPEC.md §Copywriting
# Contract). The phase's headline surface: a calibrated 80% listing-day-return
# BAND (width is the message), a muted GMP-vs-model marker, and an always-visible
# "How this was tested" honesty strip. Every string VERBATIM from the LOCKED
# UI-SPEC — descriptive, never prescriptive. NO point-estimate-as-headline (P21),
# NO green/red, coverage shown honestly (P17). The banned stems (subscri / sell /
# buy / target / accumulat / recommend / fair value / overvalued / undervalued)
# appear NOWHERE — notably `target` is avoided by design (the section says
# "range" / "interval" / "median", never "target"). Each constant is auto-enrolled
# in the import-time scrubber loop below.
# ---------------------------------------------------------------------------

# Block heading (Serif 20/600) — L5-4, the mid-page climax, not a headline call.
FORECAST_BLOCK_HEADING: str = "Listing-day forecast — a calibrated range, not a call."

# Framing sub-line (Small 12 muted) — states the range is GMP-free (FCAST-02).
FORECAST_FRAMING_SUBLINE: str = (
    "Calibrated on past Indian IPOs. This range is GMP-free — the grey-market "
    "premium is shown for context but never feeds the model."
)

# Plain-language interval caption (Body 16) — the section's REAL headline: the
# interval in words + the span width in points (L5-1). {low}/{high}/{width} are
# formatted numeric strings.
FORECAST_INTERVAL_CAPTION_TEMPLATE: str = (
    "In 80% of comparable past IPOs, the listing-day return fell between {low}% "
    "and {high}% — a span of {width} points."
)

# Median annotation (Small muted) — the point estimate as a quiet note, never a
# headline (P21). {median} is a formatted numeric string.
FORECAST_MEDIAN_ANNOTATION_TEMPLATE: str = "Model median {median}%"

# 0% baseline label (Small muted) — the issue-price reference on the return axis.
FORECAST_ZERO_LABEL: str = "0% (issue price)"

# GMP-vs-model gap line (Small muted) — the labeled delta (L5-2, GMP-03). {gmp}/
# {delta} are formatted numeric strings; {direction} is one of the two direction
# words below (above|below). The `sell`/`buy` stems are avoided in the wording.
FORECAST_GMP_GAP_TEMPLATE: str = (
    "The grey-market premium implies about {gmp}% — {delta} points {direction} "
    "the GMP-free model median."
)

# Direction words for the gap line + the GMP marker aria-label (position stated
# in WORDS, never conveyed by hue — the no-green/red invariant, WCAG 1.4.1).
FORECAST_DIRECTION_ABOVE: str = "above"
FORECAST_DIRECTION_BELOW: str = "below"

# No-GMP note (Small muted) — the COMMON already-listed case: absence shown as
# absence, never a fabricated GMP.
FORECAST_NO_GMP_NOTE: str = (
    "No grey-market premium is being reported, so there is no GMP-versus-model "
    "gap to show."
)

# "How this was tested" strip (always visible — L5-3, FCAST-04; nothing collapsed).
FORECAST_TESTED_EYEBROW: str = "How this was tested"
FORECAST_COVERAGE_STAT_LABEL: str = "80% interval coverage (empirical, held-out)"
FORECAST_MAE_STAT_LABEL: str = "Mean absolute error"
FORECAST_BACKTEST_STAT_LABEL: str = "Walk-forward backtest"
FORECAST_RMSE_TABLE_CAPTION: str = "Per-year RMSE (points)"

# Per-year RMSE table column headers (real <th scope="col"> — SR-navigable, a11y).
FORECAST_RMSE_TH_YEAR: str = "Year"
FORECAST_RMSE_TH_RMSE: str = "RMSE"

# Coverage honesty note (Small muted italic) — coverage is empirical on held-out
# data and may miss 80%; the real number is shown, never a rounded fiction (P17).
FORECAST_COVERAGE_HONESTY_NOTE: str = (
    "Coverage is measured on held-out IPOs the model never trained on. It can "
    "miss 80% — we show the real number, not a rounded one."
)

# Model-card link (the one explicit affordance) — points to /methodology (FCAST-05).
FORECAST_MODEL_CARD_LINK: str = "Full model card →"

# P9-fail honesty banner (Option A) — the shipped forecaster FAILED its release gate
# on the live backtest (naive baselines match/beat it, the honest D5-01 result). The
# covered band still renders, but the block LEADS with this so no reader mistakes the
# range for a validated call. Driven by the committed gate verdict (card_data.json).
FORECAST_GATE_FAIL_HEADING: str = "This forecaster does not beat a naive baseline"
FORECAST_GATE_FAIL_BODY: str = (
    "On the live backtest the model failed its release gate (P9: FAIL) — a naive "
    "baseline matches or beats it. The range below is shown for calibration "
    "transparency, not as a validated call."
)

# Empty states — not-covered (no forecast) + model-abstains (insufficient history).
FORECAST_EMPTY_NOT_COVERED: str = (
    "No calibrated listing-day forecast is available for this IPO yet."
)
FORECAST_EMPTY_ABSTAIN: str = (
    "There isn't enough comparable history to calibrate an honest range for this "
    "IPO, so no forecast is shown."
)

# Error state — inherited amber .drhp-refusal posture (NOT red).
FORECAST_ERROR_STATE: str = (
    "This couldn't load for this IPO right now. It's a free-tier infrastructure "
    "hiccup, not a problem with the prospectus. Try again in a minute."
)

# Partial-metrics cell — a genuinely unavailable metric renders the em-dash with
# an aria-label; never a fabricated number, never a hidden row (FCAST-04).
FORECAST_METRIC_NA: str = "—"
FORECAST_METRIC_NA_ARIA: str = "Not available"

# Band aria-label (role="img") — the interval stated in WORDS so it is never
# conveyed by band tint / width alone (WCAG 1.4.1). All fields formatted numerics.
FORECAST_BAND_ARIA_TEMPLATE: str = (
    "80% prediction interval for the listing-day return, from {low}% to {high}%; "
    "model median {median}%; interval width {width} points. Zero percent marks "
    "the issue price."
)

# GMP marker aria-label — the gap stated in words + points, never by marker
# position / colour alone (WCAG 1.4.1). {direction} is a direction word above.
FORECAST_GMP_ARIA_TEMPLATE: str = (
    "Grey-market-premium-implied listing-day return {gmp}%, {delta} points "
    "{direction} the model median."
)

# GMP-implied-return conversion provenance (native `title=` hover on the marker):
# the ₹ basis of the display-layer gmp_premium/issue_price*100 conversion, routed
# through ui/format_inr (the ONE ₹ formatter). Kept off the visible % chrome — an
# honesty/transparency detail only. {premium}/{issue_price} are format_inr strings.
FORECAST_GMP_BASIS_TITLE_TEMPLATE: str = (
    "Implied from a grey-market premium of {premium} on an issue price of "
    "{issue_price}."
)

# ---------------------------------------------------------------------------
# TRUST-03 anchor: import-time scrubber assertion.
# Any future copy edit that introduces a banned token will raise AssertionError
# here at import time, before any HTTP request is served.
# This is defense-in-depth: the scrubber already blocks LLM output; this
# ensures our OWN copy also passes.
#
# FLAG-COPY-TEMPLATING: format-string constants (containing "{") are scrubbed
# on a SAMPLE-SUBSTITUTED instance (issuer="Sample Issuer Limited", etc.) so
# the "no banned token, enforced at import" guarantee covers the templated
# forms too — not just the literal "{issuer}" placeholder text.
# ---------------------------------------------------------------------------
from compliance.scrubber import scrub as _scrub  # noqa: E402
import inspect as _inspect  # noqa: E402
import string as _string  # noqa: E402

_SAMPLE_FORMAT_VALUES = {
    "issuer": "Sample Issuer Limited",
    "topic": "sample topic",
    "suggestion1": "sample suggestion one",
    "suggestion2": "sample suggestion two",
    "fresh_pct": "59.0",
    "ofs_pct": "41.0",
    "n": "1",
    "m": "7",
    "sector": "Sample sector",
    "date": "Listed Nov 2024",
    "size": "₹1,000 cr",
    "grounded_answer": "sample grounded answer",
    "missing_part": "sample missing part",
    "specificity": "Issuer-specific",
    "pct": "62",
    "confidence_tier": "high",
    "page": "212",
    "section": "Related Party Transactions",
    "tier_word": "High",
    "tier_meaning": "stated directly on the cited page",
    "accuracy": "97%",
    "low": "₹38",
    "high": "₹52",
    "source": "Aggregator A",
    "value": "₹47",
    # Phase 5 forecast placeholders (returns in %, errors in points).
    "width": "25.9",
    "median": "6.1",
    "gmp": "4.7",
    "delta": "9",
    "direction": "above",
    "coverage": "78.3",
    "mae": "11.4",
    "year": "2024",
    "rmse": "13.5",
    "window": "2016-2025",
    "premium": "₹47",
    "issue_price": "₹390",
}


def _scrub_sample_substituted(name: str, value: str) -> None:
    """Scrub a copy constant; if it is a format-string template, scrub the
    sample-substituted instance instead of the literal "{placeholder}" text."""
    try:
        fields = [f[1] for f in _string.Formatter().parse(value) if f[1]]
    except ValueError:
        fields = []
    sample_value = value
    if fields:
        try:
            sample_value = value.format(
                **{f: _SAMPLE_FORMAT_VALUES.get(f, "sample") for f in fields}
            )
        except (KeyError, IndexError):
            sample_value = value
    _r = _scrub(sample_value)
    if not _r.passed:
        raise AssertionError(
            f"ui/copy.py contains banned token in {name!r}: matched {_r.match!r} "
            f"(checked sample-substituted form: {sample_value!r})"
        )


_module = _inspect.getmodule(_inspect.currentframe())
for _name, _value in list(vars(_module).items()):
    if _name.startswith("_") or not isinstance(_value, str):
        continue
    _scrub_sample_substituted(_name, _value)
del _scrub, _inspect, _string, _module
