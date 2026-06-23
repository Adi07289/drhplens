# DRHPLens — Migration & Continuation Handoff

> Written 2026-05-28 because Claude Code subscription access was disabled mid-build.
> This document lets you continue on **Codex CLI, Cursor, Windsurf, or Claude API** with zero context loss.
> Everything is committed to git. Nothing is lost.

---

## 0. Your subscription status

Your Claude Code subscription access is **disabled right now** (the `/compact` command failed with
"organization has disabled Claude subscription access"). To keep using Claude Code specifically, you'd need an
**Anthropic API key** (set `ANTHROPIC_API_KEY` env var) or an admin to re-enable subscription access.
But you do NOT need Claude Code to continue this project — see §5 for platform migration.

---

## 1. What this project is

**DRHPLens** — an Indian-IPO DRHP-decoder web app. A retail investor asks plain-English questions about an IPO
prospectus (the Swiggy Nov-2024 DRHP is the hand-loaded Phase 1 corpus) and gets an honest, **cited** answer with
clickable `[1]` superscript citations + a hard-refusal-with-reformulation when the DRHP doesn't cover the question.
Built as a **Data Scientist portfolio piece**. Honesty-first, SEBI-compliant (informational only, never advice).

Full vision, requirements, and 6-phase roadmap: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`.

---

## 2. What is BUILT (Phase 1 — code complete)

**46 git commits. 219 unit tests passing. 43 Python source files.** Phase 1 (Foundation + MVP-A: Cited Q&A on one IPO)
is **code-complete**. Five waves shipped:

| Wave | What shipped | Files |
|------|--------------|-------|
| 0 | Scaffolding, pinned deps, Swiggy DRHP (9.86MB, SHA-pinned), 17 test stubs | `pyproject.toml`, `data/swiggy_drhp/`, `tests/` |
| 1 | Pydantic schemas (the `claim_id` contract), banned-token scrubber (16 tokens), 3-surface disclaimer | `agent/schemas.py`, `agent/state.py`, `compliance/` |
| 2 | DRHP parser (PyMuPDF fallback), section-aware chunker (1,311 chunks), bge-m3 embedder, Qdrant client, ingest pipeline | `pipelines/ingest_swiggy.py`, `tools/`, `storage/vector.py` |
| 3 | 10 LangGraph nodes + graph wiring + Walking-Skeleton CLI (`agent/demo.py`) | `agent/nodes/*.py`, `agent/graph.py` |
| 4 | Streamlit UI (`app.py` boots without .env), citation chips, refusal banner, `/methodology` stub, mobile CSS, smoke test | `app.py`, `ui/`, `pages/`, `app/static/` |
| 5 | HF Spaces deploy config, Langfuse instrumentation (claim_id propagation), eval suite + Gate-1 calibration script | `README.md` (HF YAML), `app/observability/`, `scripts/` |

**The LangGraph agent flow** (`agent/graph.py`):
`intake → retrieve → rerank → gate1_check → decompose → generate → scrub → cite_check → emit`
with refusal branches to `refuse_with_reformulation` at gate1 (low retrieval score), gate2 (cite-check fail), and
scrubber (banned token after 1 regenerate). The **cite-check node is deterministic non-LLM** (token_set_ratio ≥80 +
numeric-set subset) — the anti-hallucination guarantee.

---

## 3. What is NOT done (the "user_setup" gap)

Phase 1 code runs end-to-end ONLY after you provide runtime services. Five things remain, all documented in `docs/DEPLOY.md`:

1. **Live Qdrant + real ingest** — code written, never run against a live vector DB (Docker wasn't started during the build)
2. **Real Docling re-parse** — current DRHP cache is a PyMuPDF fallback (34 sections vs ~150-200 with real Docling); torch was blocked on Python 3.13, now fixed (Python 3.11 installed)
3. **Public HF Spaces URL** (OPS-02) — needs an HF account + the 7 secrets
4. **Eval baseline numbers + calibrated Gate-1 threshold** — scripts ready, need live Qdrant + Gemini
5. **Phases 2-6** — fully planned at the roadmap level (`.planning/ROADMAP.md`), not yet built. Phase 2 (multi-IPO catalogue) was about to be planned when the subscription dropped.

---

## 4. RESUME STEPS — get Phase 1 actually running (45-75 min)

Run these on any machine with Python 3.11 (installed at `/usr/local/bin/python3.11`) + Docker:

```bash
cd ~/agentic-rag-app

# --- 4a. Recreate venv on Python 3.11 (3.13 blocks torch) ---
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
pip install torch docling sentence-transformers FlagEmbedding
python -c "import torch, docling, sentence_transformers, langgraph, qdrant_client; print('full stack OK')"

# --- 4b. Confirm tests still green ---
pytest tests/unit -q --timeout=30          # expect 219 passing

# --- 4c. Start Qdrant locally (needs Docker running) ---
docker run -d -p 6333:6333 -p 6334:6334 \
  -v ~/.qdrant/drhplens:/qdrant/storage \
  --name drhplens-qdrant qdrant/qdrant
curl -sf http://localhost:6333/healthz       # expect 200

# --- 4d. API keys (free tiers) ---
cat >> .env <<'EOF'
GEMINI_API_KEY=        # https://aistudio.google.com/apikey  (1500 req/day free)
GROQ_API_KEY=          # https://console.groq.com/keys       (free Llama-3.3-70B fallback)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
LANGFUSE_PUBLIC_KEY=   # https://cloud.langfuse.com          (optional; no-op if blank)
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
EOF
# then paste your real keys into .env

# --- 4e. (Optional) upgrade the DRHP cache to real Docling ---
python -m pipelines.ingest_swiggy --dry-run   # re-parses with real Docling now that torch works

# --- 4f. Ingest Swiggy DRHP into Qdrant for real ---
python -m pipelines.ingest_swiggy
pytest tests/integration/test_qdrant_ingest.py -x   # flip from xfail to green

# --- 4g. Run the Walking Skeleton CLI (the proof it works) ---
python -m agent.demo "what is the use of proceeds?"      # → cited answer with [1] chips
python -m agent.demo "what is the weather in Mumbai?"    # → refusal + reformulation chips

# --- 4h. Run the web app locally ---
streamlit run app.py     # opens localhost:8501

# --- 4i. Eval baseline + Gate-1 calibration ---
python scripts/run_eval.py            # writes eval/reports/<date>-phase1-baseline.md
python scripts/calibrate_gate1.py     # prints recommended GATE1_THRESHOLD → update agent/policies.py
```

**For the public HF Spaces deploy** (OPS-02), follow the 10-step runbook in `docs/DEPLOY.md`.

---

## 5. MIGRATING to Codex / Cursor / API (continue Phases 2-6)

The codebase is **platform-agnostic Python** — none of it depends on Claude Code. Only the *planning workflow*
(GSD skills) was Claude-Code-specific. Here's how to continue elsewhere:

### Option A — OpenAI Codex CLI (closest match)
```bash
# Codex reads the same files. Point it at the repo:
cd ~/agentic-rag-app
codex
# Then prompt it with the Phase 2 brief below (§6).
```
Note: the `agent/nodes/generate.py` LLM call uses **Gemini via Instructor** (not OpenAI). You can keep Gemini, or
swap to OpenAI by editing `agent/nodes/generate.py` + `agent/policies.py`. The stack choice is documented in
`.planning/research/STACK.md`.

### Option B — Cursor / Windsurf (IDE agents)
Open `~/agentic-rag-app` as a workspace. Feed the agent `.planning/ROADMAP.md` + the relevant phase's plan files.
Cursor's "@-mention files" works well with the `.planning/` structure.

### Option C — Claude API directly (keep using Claude models)
Set `ANTHROPIC_API_KEY` and use the Anthropic SDK or `claude` CLI with an API key instead of subscription auth.
This is the *only* way to keep using Claude Code itself.

### What to hand the new agent
Every planning artifact is in `.planning/`. The single most useful onboarding prompt for any new agent:

> "Read `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, and
> `.planning/phases/01-foundation-mvp-a-cited-q-a-on-one-ipo/01-PHASE-CLOSE.md`. Phase 1 is code-complete (46 commits,
> 219 tests). I want to build Phase 2 next. Read the Phase 2 section of ROADMAP.md and propose a plan."

---

## 6. PHASE 2-6 BRIEFS (for the next agent to plan + build)

All six phases are defined in `.planning/ROADMAP.md` with goals, success criteria, and requirement IDs. Summary:

| Phase | Goal | Key reqs |
|-------|------|----------|
| **2** | Multi-IPO catalogue + per-IPO DRHP snapshot page (metadata, business summary, financials, risks, use-of-proceeds, promoter — all cited) | SNAP-01..07, OPS-01 |
| **3** | Structured red-flag extraction table (RPT%, OFS%, pledge%, etc.) + per-field F1 gold set + **"Show your work" methodology pane (METHOD-01)** + numeric-faithfulness ≥0.95 gate | EXTRACT-01..03, EVAL-03, METHOD-01 |
| **4** | Historical IPO dataset (survivorship-corrected) + peer multiples + GMP read-only display + Indian formatting | PEER-01/02, GMP-01/02, UI-04 |
| **5** | Calibrated listing-day forecaster (XGBoost + MAPIE conformal intervals) + walk-forward backtest + model card — **the headline DS artifact** | FCAST-01..05, GMP-03, UI-03 |
| **6** | Full eval dashboards inline + recruiter landing page (LAND-01) + live failure gallery (FAILGAL-01) + SEBI legal review | EVAL-01/02/04/05, OPS-03, LAND-01, FAILGAL-01 |

**Phase 2 build pattern** (replicate Phase 1's wave structure): the multi-IPO catalogue needs the ingestion pipeline
extended from one `drhp_id` to many (the schema already uses `drhp_id` everywhere — designed for this, see
`.planning/TODOS.md` E5 note). Snapshot fields are NLP extractions over the same Qdrant chunks. Reuse the citation
infrastructure from Phase 1.

---

## 7. Key architecture decisions (so the new agent doesn't re-litigate)

- **Stack:** LangGraph + LlamaIndex + Docling + Qdrant + bge-m3 + Instructor/Gemini + Streamlit + HF Spaces. Full rationale: `.planning/research/STACK.md`.
- **claim_id is the load-bearing contract** — Phase 3's methodology pane consumes the exact `GroundedAnswer`/`Claim`/`RetrievedChunkRef` schema in `agent/schemas.py`. Do NOT rename those fields.
- **Cite-check is deterministic non-LLM** — never replace it with an LLM judge (defeats the anti-hallucination guarantee).
- **GMP display ≠ GMP feature** — Phase 4 shows GMP read-only; it must never enter the Phase 5 forecast model (circular).
- **Walking-Skeleton-first vertical-slice MVP** — every phase ships an end-to-end demoable slice, not a horizontal layer.
- **5 critical pitfalls** (SEBI advice boundary, hallucinated numbers, survivorship bias, GMP lookahead, citation drift): `.planning/research/PITFALLS.md`.
- **Deferred to v2** (`.planning/TODOS.md`): user-uploadable DRHP, Hindi mode, multi-IPO compare, pre/post retrospectives.

---

## 8. The full document map

| Want to know... | Read |
|-----------------|------|
| The vision + core value | `.planning/PROJECT.md` |
| All 45 requirements | `.planning/REQUIREMENTS.md` |
| The 6-phase roadmap | `.planning/ROADMAP.md` |
| Why these tech choices | `.planning/research/STACK.md`, `SUMMARY.md`, `ARCHITECTURE.md` |
| What can go wrong | `.planning/research/PITFALLS.md` |
| Phase 1 decisions | `.planning/phases/01-*/01-CONTEXT.md` |
| Phase 1 technical research | `.planning/phases/01-*/01-RESEARCH.md` |
| Phase 1 UI contract | `.planning/phases/01-*/01-UI-SPEC.md` |
| Phase 1 wave-by-wave plans | `.planning/phases/01-*/01-0[1-6]-PLAN.md` |
| What each wave delivered | `.planning/phases/01-*/01-0[1-6]-SUMMARY.md` |
| Phase 1 close summary | `.planning/phases/01-*/01-PHASE-CLOSE.md` |
| How to deploy | `docs/DEPLOY.md` |
| The CEO strategic review | `/Users/adityasharma/.claude/plans/mighty-noodling-pretzel.md` (Claude-Code-local; copy it into the repo if migrating) |

---

## 9. Immediate next action (pick one)

- **Just want to see it work?** → Run §4a-4h (45 min). Get the Walking Skeleton answering cited questions locally.
- **Want it live for your portfolio?** → §4 + `docs/DEPLOY.md` (public HF Spaces URL).
- **Want to keep building?** → §5 (migrate to Codex/Cursor) + §6 (Phase 2 brief).

Everything is committed. `git log --oneline | head -46` shows the full build history. Good luck — the foundation is solid.
