---
phase: "04"
status: passed
verified: 2026-07-27
method: goal-backward (against ROADMAP Phase 4 success criteria) + live-app evidence
---

# Phase 4 Verification — Historical IPO Dataset + Peer Comparator + GMP Display

**Verdict: ACHIEVED (5/5 success criteria).** 04-07 (the survivorship panel + median
sanity-check) was the last open plan; it was built live at the 05-11 crawl and its
SC-5 sanity result is now surfaced on /methodology, closing the phase.

| SC | Requirement | Verdict | Evidence |
|----|-------------|---------|----------|
| 1 | DRHP "Comparison with Listed Peers" set surfaced, anchored to its section (PEER-01) | ✅ | 04-03 PeerRecord + DRHP peer-SET query; 04-05 peer table on the snapshot page |
| 2 | Peer multiples (P/E, P/B, EV/EBITDA, ROE) from screener.in/yfinance/NSE/BSE in a table (PEER-02) | ✅ | 04-01 source spike; 04-03 per-cell source ladder; 04-05 renderer |
| 3 | Read-only GMP with above-the-fold caveat, computationally isolated (GMP-01, GMP-02) | ✅ | 04-04 GmpRecord + GMP-02 import-audit; 04-06 read-only block; verified live on /snapshot ("never use it in any forecast") |
| 4 | Indian conventions (lakh/crore, INR) + RPT/QIB/NII/RII tooltips (UI-04) | ✅ | 04-02 format_inr; 04-05 pure-CSS glossary tooltips |
| 5 | Survivorship-corrected panel committed with status column; median sanity-checked vs ~7%, flagged on /methodology if it diverges (FCAST-03 foundation) | ✅ | data/historical/ipo_panel.parquet (1,378 IPOs, status {listed_alive, withdrawn}); median 10.19% WITHIN the [-5%, 20%] band; sanity result surfaced on /methodology this session |

**Honest notes:** the live panel holds 1,378 IPOs (exceeds the ~800-1000 target) with
only {listed_alive, withdrawn} statuses present — the real universe produced no
delisted/merged/name_changed rows, retained honestly (not fabricated). The median
(10.2%) sits above the narrow 7.19% point estimate but within the plausible band → NOT
survivor-inflated (withdrawn retained as NaN, P3). Full unit suite: 530 passed, 0 failed.
