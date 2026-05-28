# Citation Interaction Manual Test Script

Wave 4 manual verification for `01-VALIDATION.md` manual-only rows:
- Citation chip click + inline expand (UI-02)
- First-use modal session-state (TRUST-01)
- Mobile responsive at 375/640/1024 (UI-01)
- Methodology stub link resolves (L-7)

**Instructions:** Run `streamlit run app.py` from the repo root. Fill in PASS/FAIL at the end of each step.

---

## Section 1: Setup

1. Run `streamlit run app.py` from the repo root on a fresh terminal.
2. Wait for the URL to appear (typically `http://localhost:8501`). Open in a fresh browser tab (or an incognito window to ensure no prior session state).

---

## Section 2: First-use modal (UI-VALIDATION row TRUST-01)

- Step 1: On first visit, the modal `Read this once.` appears immediately, the rest of the page is non-interactive (greyed out). — PASS / FAIL
- Step 2: Modal contains the anchor disclaimer copy (`DRHPLens reads prospectuses for you...`) AND the AI-disclosure sentence beginning `The system uses large language models…`. — PASS / FAIL
- Step 3: Modal contains ONE button labelled `I understand — open DRHPLens` (no Decline button, no close X). — PASS / FAIL
- Step 4: Click the button. Modal closes. The hero, DRHP metadata header, empty state, chat input, and persistent footer all become visible. — PASS / FAIL
- Step 5: Press F5 to refresh. Modal does NOT re-appear (session-state persisted within the same browser tab). — PASS / FAIL
- Step 6: Close the tab. Open a new tab to the same URL. Modal RE-appears (session-state is tab-scoped per Wave 1 known limitation — see RESEARCH.md). — PASS / FAIL

---

## Section 3: Citation chip click + inline expand (UI-VALIDATION row UI-02)

*Requires a live GEMINI_API_KEY + Qdrant connection. Skip if running in code-now-defer mode.*

- Step 1: Ask: `What is the use of proceeds breakdown?` — PASS / FAIL
- Step 2: Wait for the answer to render (the `st.status` container shows `Reading Swiggy's DRHP…` while LLM is in flight). — PASS / FAIL
- Step 3: The answer prose contains one or more superscript chips like `[1]` styled as small white-on-slate-indigo pills. — PASS / FAIL
- Step 4: Hover the `[1]` chip — background darkens to a slightly darker indigo + the bracketed number gains an underline. — PASS / FAIL
- Step 5: Click the `[1]` chip — its corresponding `st.expander` below the answer opens, revealing the verbatim DRHP source-text snippet (italic, 14px) + a link `View DRHP page N on SEBI →`. — PASS / FAIL
- Step 6: Click the `View DRHP page N on SEBI →` link — a new browser tab opens at the SEBI Swiggy Prospectus URL. The PDF should scroll to (or be deep-linkable via `#page=N`) the cited page. — PASS / FAIL
- Step 7: Per-answer disclaimer `Informational only — not advice.` appears at the bottom of the answer block, italic, muted. — PASS / FAIL

---

## Section 4: Refusal flow + reformulation chips (UI-VALIDATION row RAG-03)

*Requires live agent.*

- Step 1: Ask: `What does Swiggy say about Mars colonization?` (off-topic — Gate 1 triggers). — PASS / FAIL
- Step 2: Expect: the refusal banner renders in place of an answer. Background is amber (`#FEF3C7`), 4px left border in amber-600 (`#D97706`), heading `This isn't in the DRHP.` in amber-900. — PASS / FAIL
- Step 3: Up to 2 reformulation chips appear below the body, styled as light-grey rounded buttons (`#F4F5F7` background). — PASS / FAIL
- Step 4: Click one chip — the suggested question pre-fills the chat-input area as a `Suggested: "…"` helper line. The chat input is NOT auto-submitted (user retains agency). — PASS / FAIL
- Step 5: Ask: `Should I subscribe to Swiggy?` — banned token triggers post-LLM scrubber. Expect: refusal banner with banned-token copy `Couldn't return that answer.`. NO reformulation chips (UI-SPEC anti-pattern). — PASS / FAIL

---

## Section 5: Mobile responsive (UI-VALIDATION row UI-01)

Open Chrome DevTools (`Cmd+Option+I` on macOS, `Ctrl+Shift+I` on Windows/Linux), toggle device emulation (`Cmd+Shift+M` or `Ctrl+Shift+M`).

- Step 1: Set viewport to 375 x 667 (iPhone SE). Verify: hero stacks; DRHP metadata header wraps to multi-line; chat input stays sticky at bottom; persistent footer stays sticky at bottom (above device home indicator); citation chips remain tappable (44x44px tap target). — PASS / FAIL
- Step 2: Set viewport to 640 x 800 (tablet portrait). Verify: DRHP metadata header now single-row; horizontal padding visible on sides. — PASS / FAIL
- Step 3: Set viewport to 1024 x 768. Verify: content max-width 720px, centered; persistent footer is `position: relative` (scrolls with content) not sticky. — PASS / FAIL

---

## Section 6: Methodology stub (UI-VALIDATION L-7)

- Step 1: Click the `methodology` link in the persistent footer. — PASS / FAIL
- Step 2: URL becomes `http://localhost:8501/methodology`. Page does NOT 404. — PASS / FAIL
- Step 3: Page shows: Display 28px heading `Methodology`; body paragraph from `METHODOLOGY_STUB_BODY`; a `GitHub repository →` link; a `← Back to DRHPLens` link; same persistent footer at bottom. — PASS / FAIL
- Step 4: Click `← Back to DRHPLens`. URL returns to `/`. Chat history is preserved (session-scoped). — PASS / FAIL

---

## Section 7: Accessibility quick-check (UI-VALIDATION WCAG AAA)

- Step 1: On the home page, press `Tab` repeatedly. Focus indicators (2px slate-indigo ring) appear on: chat input (when focused), citation chips (when an answer is present), suggestion buttons, persistent-footer methodology link. — PASS / FAIL
- Step 2: On a focused citation chip, press `Enter` — the corresponding expander opens. Press `Tab` — focus moves to the next interactive element in document order. — PASS / FAIL
- Step 3: If you have a screen reader (VoiceOver on macOS: `Cmd+F5`), navigate to a citation chip — it should announce `link, citation 1, opens source-text panel` (per UI-SPEC Accessibility §Screen reader). — PASS / FAIL

---

*Note any deviations and link to the relevant UI-SPEC section. This script is read by the gsd-checker before Wave 4 sign-off.*
