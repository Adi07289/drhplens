# Phase 4: Historical IPO Dataset + Peer Comparator + GMP Display - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 4-Historical IPO Dataset + Peer Comparator + GMP Display
**Areas discussed:** GMP caveat & provenance, Peer set & missing-data honesty, Formatting & glossary (UI-04)

---

## GMP caveat & provenance

### Q1 — How should the GMP number be SOURCED and shown?
| Option | Description | Selected |
|--------|-------------|----------|
| Multiple sources + spread | 2–3 public aggregators; show disagreement/spread — divergence is the honesty signal | ✓ |
| Single source, one number | One aggregator, one value; simplest but reads as authoritative | |
| Single source + short trend | One aggregator + last-3-days trend to show volatility | |

**User's choice:** Multiple sources + spread

### Q2 — How prominent and caveated should the GMP display be?
| Option | Description | Selected |
|--------|-------------|----------|
| De-emphasized + disclosure | Small, low on page, collapsed behind "What is GMP? Why we don't trust it", persistent caveat | ✓ |
| Visible row + caveat banner | Labeled GMP row with above-the-fold caveat banner | |
| Prominent + caveat line | GMP prominent (mainstream style) with one-line caveat | |

**User's choice:** De-emphasized + disclosure
**Notes:** GMP-02 model-isolation captured as a hard invariant (display-only, never enters a feature pipeline), not debated.

---

## Peer set & missing-data honesty

### Q1 — When a DRHP-disclosed peer is missing some multiples, what shows?
| Option | Description | Selected |
|--------|-------------|----------|
| Keep peer, mark n/a | Keep the row, render missing cells as explicit n/a | |
| Drop incomplete peers | Only show peers with a full multiples set | |
| Backfill + flag source | Fill gap from an alternate source, flag provenance per cell | ✓ |

**User's choice:** Backfill + flag source

### Q2 — When the DRHP discloses NO listed-peer comparison, what shows?
| Option | Description | Selected |
|--------|-------------|----------|
| Honest empty-state | "This DRHP disclosed no listed-peer comparison" — never fabricate | ✓ |
| Labeled sector fallback | Fall back to labeled sector-peer set | |
| Empty-state + optional sector | Honest default with an optional labeled sector expander | |

**User's choice:** Honest empty-state
**Notes:** Backfill implies per-cell provenance tracking + a source-priority order (research item, P15/P16 apply).

---

## Formatting & glossary (UI-04)

### Q1 — How should large rupee amounts render?
| Option | Description | Selected |
|--------|-------------|----------|
| Auto-scale lakh↔crore | ₹ + Indian grouping, auto lakh/crore by magnitude, tabular-nums | ✓ |
| Always crore | Everything in crore | |
| Raw ₹ grouped | Full ₹ with Indian grouping, no scaling | |

**User's choice:** Auto-scale lakh↔crore

### Q2 — Which terms get glossary tooltips?
| Option | Description | Selected |
|--------|-------------|----------|
| Core Indian-IPO set | RPT, QIB, NII, RII + GMP, OFS, DRHP, anchor investor | ✓ |
| Only UI-04's four | RPT, QIB, NII, RII only | |
| Core set + financial ratios | Core set + P/E, P/B, EV/EBITDA, ROE | |

**User's choice:** Core Indian-IPO set

---

## Claude's Discretion

- Peer multiples live-vs-cached + point-in-time-vs-current (user deferred to research).
- Number-format edge cases (negatives, missing → em-dash, sub-lakh) — follow Phase 2/3 conventions.

## Deferred Ideas

- Historical dataset internals (return target, status taxonomy, SEBI-issuer-side sourcing, replace-with-NaN, ~7% sanity check) — P3 territory, researcher/planner.
- Tooltip interaction (hover vs tap) + mechanism — UI-SPEC (run /gsd-ui-phase 4).
- jugaad-data endpoint-validation spike at phase start (ROADMAP research flag).
- Labeled sector-peer fallback when DRHP names no peers — considered, deferred.
- Financial-ratio glossary tooltips — add only if it doesn't clutter the peer table.
