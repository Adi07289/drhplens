---
spike: 002
name: deepeval-gemini-judge
type: standard
validates: "Given a gold Q+answer+context, when FaithfulnessMetric.measure() runs on a native GeminiModel judge, then a score+reason returns without any OpenAI key and assert_test works opt-in — confirm pin"
verdict: VALIDATED
related: [001]
tags: [deepeval, faithfulness, gemini]
---

# Spike 002: DeepEval Faithfulness on a Native Gemini Judge

## What This Validates

Can DeepEval's `FaithfulnessMetric` run on a native Gemini judge (no OpenAI key), discriminate faithful vs hallucinated answers, and support the opt-in `assert_test` CI lane — and what version/model to pin?

## Research (run live)

| Question | Evidence (measured) |
|----------|---------------------|
| deepeval version | **4.1.4** (`deepeval>=4.1,<5`) |
| Native Gemini judge | `deepeval.models.GeminiModel(model, api_key, temperature, …)` — imports + runs with only `GEMINI_API_KEY` (OpenAI key was **unset**; judge reached Gemini directly). |
| Judge model id | **`gemini-3.5-flash`** — the id the codebase already uses (`agent/`). The AI-SPEC's `gemini-2.5-flash` is **stale**: it returns `404 NOT_FOUND — "no longer available to new users."** |
| Discrimination | Faithful answer → **1.00**; hallucinated ("profitable" vs a real net loss) → **0.50** with a correct reason. Judge separates faithful from fabricated. |
| assert_test | Exists; raises `AssertionError` below threshold — reserved for the opt-in CI lane only (never gates deploy). |
| Free-tier limit | **429 RESOURCE_EXHAUSTED — 5 requests/min** for `gemini-3.5-flash` (`GenerateRequestsPerMinutePerProjectPerModel-FreeTier`, quotaValue 5). Faithfulness fans out (~1 truths-extraction + N per-claim verdicts) per question → exhausts the window inside a single 2-case run. |

## How to Run

```bash
set -a && . ./.env && set +a
.venv/bin/pip install "deepeval"   # 4.1.4
.venv/bin/python - <<'PY'
from deepeval.models import GeminiModel
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase
import os
judge = GeminiModel(model="gemini-3.5-flash", api_key=os.environ["GEMINI_API_KEY"], temperature=0.0)
ctx = ["FY2024 revenue Rs 11,000 crore (FY2023 Rs 8,265 crore); net loss Rs 2,350 crore."]
m = FaithfulnessMetric(threshold=0.95, model=judge, include_reason=True, async_mode=False)
m.measure(LLMTestCase(input="q", actual_output="Revenue Rs 11,000 cr; net loss Rs 2,350 cr.", retrieval_context=ctx))
print(m.score, m.reason)
PY
```

## Investigation Trail

1. Installed deepeval 4.1.4; `GeminiModel` + `FaithfulnessMetric` + `LLMTestCase` import clean.
2. First measure with `gemini-2.5-flash` → **404, model deprecated** ("no longer available to new users"). The wiring reached Gemini (no OpenAI needed) — purely a model-id problem.
3. Grepped the codebase: it already uses **`gemini-3.5-flash`** (agent) / `gemini-3.1-flash-lite` (forecast). Listed live models; usable flash ids include `gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-flash-latest`.
4. Re-ran on `gemini-3.5-flash`: **faithful → 1.00 (11s)**. The second (hallucinated) case hit **429: 5 RPM free-tier**. Faithfulness makes multiple calls/question, so one 2-case run exhausted the window.
5. Backed off 65s, re-measured the hallucinated case → **0.50**, reason correctly cites the profitability claim contradicting the net loss. Discrimination proven.

## Results

**Verdict: VALIDATED.**

- **DECISION — pin `deepeval>=4.1,<5` (4.1.4)**; judge = `deepeval.models.GeminiModel`. No OpenAI dependency: confirmed running with `OPENAI_API_KEY` unset.
- **CORRECTION for the AI-SPEC/CLAUDE.md — judge model = `gemini-3.5-flash`, not `gemini-2.5-flash`** (2.5-flash 404s; 3.5-flash is what the codebase already uses; keeps the judge consistent with the agent's model).
- ✓ Faithful=1.00 / hallucinated=0.50 with a correct contradiction reason → the judge is usable and discriminating for the reported faithfulness dimension.
- **⚠ PLANNER-CRITICAL — free tier is 5 RPM for gemini-3.5-flash.** A 13-Q faithfulness run (multi-call fan-out) will constantly hit the limit. The runner MUST: `async_mode=False`, serial (`-n 1`), `tenacity` backoff on 429 (retry ~30-65s), and DeepEval cache (`-c`). Expect a full faithfulness pass to be minutes, not seconds. This is exactly why faithfulness is **REPORTED, not gated** (deterministic metrics carry the gate) and why ≥0.7 human calibration on a ≥50-example sample is the trust mechanism — you cannot cheaply re-run the judge at scale on free tier.
- Minor: DeepEval's default reason template is sycophantic ("Fantastic job!"); fine for the committed `.md` audit trail, override the template later if desired.
