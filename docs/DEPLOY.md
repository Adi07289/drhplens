# DRHPLens — Phase 1 Deploy Runbook

Step-by-step manual deployment guide. Follow each numbered step in order.
This runbook closes OPS-02 (publicly deployed on free-tier host).

---

## Prerequisites

Before starting:

1. GitHub repo is **public** (HF Spaces linked-repo feature requires a public repo).
2. All Phase 1 waves 0-4 are merged to `main` — this runbook ships Wave 5 code too.
3. **Qdrant Cloud** free 1GB cluster is live (provisioned in Wave 2). The Swiggy DRHP
   is already ingested (~1,500-2,500 chunks, ~10 MB raw vector data + payload —
   verified in Wave 2). Qdrant free 1GB is sufficient for Phase 1 single-IPO scope;
   Phase 2 multi-IPO catalogue will re-evaluate sizing before adding the 5th-10th DRHP.
4. Local `.env` is filled with all 7 keys from `.env.example`.
5. `pytest tests/unit -x -q --timeout=30` passes (all 219+ unit tests green).

---

## Step 1 — Push to GitHub

```bash
git push origin main
```

Confirm all Wave 0-5 commits are upstream. The `README.md` at the root contains the HF
Spaces YAML frontmatter (sdk: streamlit, sleep_time: 1800) — HF reads this on every push
to configure the Space runtime.

---

## Step 2 — Create Langfuse Cloud account + project

1. Visit <https://cloud.langfuse.com/auth/sign-up> and sign up for the free tier.
2. Create a project named **`drhplens-phase1`**.
3. Navigate to project **Settings → API Keys**.
4. Copy the **Public Key** (starts `pk-lf-...`) and **Secret Key** (starts `sk-lf-...`).
   You will paste these into HF Spaces secrets in Step 4.

---

## Step 3 — Create HF Space

1. Visit <https://huggingface.co/join> if you don't have an account.
2. Visit <https://huggingface.co/new-space>.
3. Configure:
   - **Space name**: `drhplens` (or your preferred slug)
   - **SDK**: Streamlit
   - **Hardware**: CPU basic (FREE)
   - **Visibility**: Public
4. After creation, link to your GitHub repo:
   - Space → **Settings → Linked Repositories** → add your repo → branch `main`
   - Alternatively: add the HF git remote (`git remote add hf https://huggingface.co/spaces/<user>/drhplens`) and `git push hf main`.

---

## Step 4 — Configure Secrets

Navigate to **Space → Settings → Variables and secrets → Secrets**. Add one secret per
line from `.env.example` — **NEVER paste real values into source code or README**:

| Secret name | Where to get the value |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio → API keys: <https://aistudio.google.com/app/apikey> |
| `GROQ_API_KEY` | Groq Console → API Keys: <https://console.groq.com/keys> |
| `QDRANT_URL` | Qdrant Cloud → Cluster → Endpoint URL (Wave 2 provisioned) |
| `QDRANT_API_KEY` | Qdrant Cloud → Cluster → API Keys (Wave 2 provisioned) |
| `LANGFUSE_PUBLIC_KEY` | Langfuse Cloud → Project Settings → API Keys (Step 2) |
| `LANGFUSE_SECRET_KEY` | Langfuse Cloud → Project Settings → API Keys (Step 2) |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` (EU) or `https://us.cloud.langfuse.com` (US) |

---

## Step 5 — Wait for First Build

HF Spaces builds automatically on linked-repo push. The **first build is slow (3-10 min)**:
bge-m3 + bge-reranker-v2-m3 weights download (~1.7 GB total), then Streamlit cold-boots.
Watch the build log in Space → **Logs**. If the build fails, paste the exact error for
diagnosis before proceeding.

After build: the Space enters "Running" state. The `sleep_time: 1800` in the README YAML
frontmatter sets HF's cold-start hibernation threshold to 30 minutes (the maximum free-tier
value). This is the PITFALL 6 mitigation documented in RESEARCH §Pitfall 6.

---

## Step 6 — Smoke Test the Live URL

Visit `https://huggingface.co/spaces/<your-username>/drhplens` in an **incognito window**.
Verify each item:

- [ ] First-use modal appears with the D-07 anchor copy ("DRHPLens reads prospectuses for you...")
- [ ] Click "I understand" → home page renders with chat input + persistent footer disclaimer
- [ ] Ask: **"What is Swiggy's issue size?"** → expect a cited answer with at least one `[1]` chip
- [ ] Click the `[1]` chip → expect inline source span expansion showing DRHP text + SEBI link
- [ ] Ask: **"What does Swiggy say about Mars colonization?"** → expect refusal banner + reformulation chips
- [ ] Ask: **"Should I subscribe to Swiggy?"** → expect Gate 2 refusal (banned advisory token)
- [ ] Open DevTools → 375px width → verify mobile-responsive (chips tappable, footer readable)
- [ ] Visit `/methodology` URL → verify the methodology stub page renders (no 404)

---

## Step 7 — Verify Langfuse Traces

1. Open <https://cloud.langfuse.com> → **drhplens-phase1** project → **Traces**.
2. Verify each smoke-test question produced a trace.
3. For a grounded-answer trace: verify **9 spans** — `intake`, `retrieve`, `rerank`,
   `gate1_check`, `decompose`, `generate`, `scrub`, `cite_check`, `emit`.
4. Verify each `Claim` span carries `claim_id` in metadata (Phase 3 METHOD-01 consumer contract).
5. Verify the `faithfulness_via_cite_check` custom score is logged on grounded-answer traces.
6. Verify refusal traces carry `refusal_reason` metadata at the trace level.

---

## Step 8 — Configure Cron Pinger (PICK ONE)

HF Spaces free tier hibernates after ~48h idle (and sooner under load). Keep it warm during
demo hours to prevent a recruiter from hitting a cold-start spinner.

**Option A — cron-job.org (recommended — more punctual per RESEARCH §Pitfall 6):**

1. Create a free account at <https://cron-job.org/en/>.
2. New cronjob:
   - **URL**: `https://huggingface.co/spaces/<your-username>/drhplens`
   - **Schedule**: every 8 minutes (`*/8 * * * *`)
   - **Active hours**: 06:00–23:00 IST (to save quota during off-hours)
3. Enable the job and verify the first execution in the dashboard.

**Option B — GitHub Actions (no extra account; ±5-15 min skew acceptable):**

1. Copy `scripts/cron_pinger.yml` to `.github/workflows/ping.yml`.
2. Edit the `URL` variable inside the file: replace `<user>` with your HF username.
3. Commit and push.
4. Enable Actions: repo **Settings → Actions → General → Allow all actions**.
5. Verify the workflow appears in the **Actions** tab and runs on schedule.

Note: GitHub Actions schedule cron has documented 5-15 min scheduling skew; Option A
(cron-job.org) fires more precisely at the 8-minute mark.

---

## Step 9 — Verify Cold-Start UX (PITFALL 6 closure)

1. Wait **at least 35 minutes** without any traffic to the Space.
2. Visit the public URL in a fresh incognito window.
3. Verify:
   - "Warming up..." copy renders within **5 seconds** of page load.
   - Home page renders within **60 seconds** of cold start (OPS-02 acceptance criterion).
4. If the Space does not wake within 60s, check that `sleep_time: 1800` is present in `README.md`
   frontmatter and that the cron pinger from Step 8 is active.

---

## Step 10 — Run the First Eval Suite

With your local `.env` filled in:

```bash
python scripts/run_eval.py
```

This invokes live Qdrant + live Gemini + live Langfuse and writes the baseline report to
`eval/reports/<YYYY-MM-DD>-phase1-baseline.md`. Commit the report:

```bash
git add eval/reports/
git commit -m "eval: phase 1 baseline report — first run against gold set"
git push origin main
```

Verify the report has three sections: **Summary**, **Per-Entry Results**, **Gold Set Statistics**.

---

## Step 11 — Gate 1 Calibration

```bash
python scripts/calibrate_gate1.py
```

The script sweeps `GATE1_THRESHOLD` from -2.0 to +2.0 in 0.5 steps against the gold set.
It prints the recommended value and the exact line to paste into `agent/policies.py`.

After calibration:

1. Update `agent/policies.py` line `GATE1_THRESHOLD` with the recommended value + inline comment.
2. Push and let the Space rebuild:

```bash
git add agent/policies.py
git commit -m "chore: calibrate GATE1_THRESHOLD against phase 1 gold set"
git push origin main
```

---

## Step 12 — Phase 1 Close

1. Flip `01-VALIDATION.md` frontmatter: `nyquist_compliant: false` → `nyquist_compliant: true`.
2. Walk the Per-Task Verification Map in `01-VALIDATION.md` — update every row to ✅ green.
3. Commit `01-06-SUMMARY.md` referencing the public URL + eval baseline numbers.

```bash
git add .planning/phases/01-foundation-mvp-a-cited-q-a-on-one-ipo/
git commit -m "docs(01): close phase 1 — public URL live + first eval baseline + claim_id traces"
git push origin main
```

---

## Cost Monitoring

Phase 1 should cost **\$0 across all services**:

| Service | Free quota | Phase 1 usage |
|---|---|---|
| Gemini 2.5 Flash | 1,500 req/day | ~13 eval calls + smoke tests |
| Groq (Llama-3.3-70B) | Generous free tier | Fallback only |
| Qdrant Cloud | 1 GB free cluster | ~10 MB used (single DRHP) |
| Langfuse Cloud | Free tier | All traces |
| HF Spaces | CPU basic free | Always-on |

If any service shows charges, file a cost item **before the next user demo**.
