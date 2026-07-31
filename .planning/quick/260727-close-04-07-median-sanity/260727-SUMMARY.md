---
quick_id: "260727-close-04-07-median-sanity"
status: complete
completed: 2026-07-27
---

# Summary: close 04-07 — surface the ~7% median MAAR sanity-check on /methodology

## What changed
The SC-5 survivorship median sanity-check existed in `validate.py` but was not
surfaced on `/methodology`. Added a render-only note showing the committed panel's
median sanity RESULT. Marked 04-07 done in ROADMAP.

## Corrected premise (honest)
The prompt assumed the median "materially diverges" and wanted a divergence WARNING.
`sanity_check_median`'s band is `[-5%, +20%]`; it flags only > 20% (survivor
inflation) or < -5%. The committed panel median is **10.19%** (n=1245) — above the
narrow 7.19% Shah & Mehta point estimate but WITHIN the band → `flag is None`. So the
honest surfacing is the within-band confirmation (the panel is NOT survivor-inflated —
withdrawn/delisted retained as NaN, P3), not a fabricated alarm.

## Deliverables
- `pipelines/historical/validate.py::panel_sanity_summary(df) -> dict` (TDD) —
  render-ready dict (median_pct, n_scored, baseline, band, within_band, flag|None,
  methodology).
- `scripts/write_panel_sanity.py` → committed `data/historical/panel_sanity.json`
  (median 10.19%, n 1245, within_band true, flag null). Deterministic, no network.
- `pages/01_methodology.py` — reads `panel_sanity.json` (json ONLY, no pipelines
  import — T-05-10-ISO render-only isolation preserved) and renders the
  "Survivorship sanity" note; the divergence flag text is shown VERBATIM only if it
  ever fires.
- Tests: `test_panel_sanity_summary.py` (+3, incl. survivor-inflation firing the flag +
  the committed panel passing), `test_methodology_render.py` (+2, page surfaces the
  note + artifact exists).
- ROADMAP: 04-07 marked `[x]`.

## Verification (fresh)
- Full unit suite: **530 passed, 1 skipped, 0 failed** (render-only isolation green).
- Live app `/methodology`: renders "Survivorship sanity … median 10.19% over 1245
  scored IPOs … WITHIN the [-5%, 20%] sanity band, no survivorship-inflation flag …
  P3." No false divergence alarm. Screenshot: `/tmp/meth_survivorship_sanity.png`.

## Out of scope
- Phase-4 header checkbox + STATE.md progress reconciliation → prompt #6.
