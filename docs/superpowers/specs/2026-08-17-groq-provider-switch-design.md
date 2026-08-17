# Design — LLM Provider Switch (Gemini → Groq via an env-configurable factory)

**Date:** 2026-08-17
**Status:** Awaiting approval
**Author:** paired session
**Scope:** one focused refactor — no new features

---

## 1. Problem

The generation LLM is hard-wired to **Gemini** (`google.genai` + Instructor's Gemini
structured-output mode) in four agent nodes. Gemini's free tier is ~**20 requests/day**
on the synthesis model, so local testing and the public demo both hit the wall quickly.
There is **no way to switch providers** without editing every node.

Goal: make the provider a **single config switch** so we can run on **Groq**
(Llama-3.3-70B, OpenAI-compatible, a far larger free tier) for both local dev and the
public deploy — while keeping Gemini available as a fallback and **not regressing
citation faithfulness**, which is the project's core promise.

Non-goal: Ollama (an 8 GB M2 can't run a local LLM alongside the bge-m3 + reranker
stack); streaming changes; prompt rewrites.

## 2. Current state (verified)

Four nodes each construct their own Gemini client and loop over `GEMINI_MODELS`:

| Node | Client fn | Call site |
|------|-----------|-----------|
| `agent/nodes/classify.py` | `_get_llm_client()` | `_llm_classify()` |
| `agent/nodes/decompose.py` | (inline) | `_llm_decompose()` |
| `agent/nodes/generate.py` | (inline) | generate hop |
| `agent/nodes/synthesize.py` | `_get_fusion_client()` | `_llm_fuse()` |

Every node already calls through Instructor's **unified interface**:
`client.chat.completions.create(model=…, response_model=<Pydantic>, messages=…)`.
So only three things are provider-specific: **client construction**, **structured-output
mode**, and **model names**. The `.create(response_model=…)` calls do not change.

Key facts:
- `agent/policies.py` → `GEMINI_MODELS = ("gemini-3.5-flash", "gemini-3.1-flash-lite")`.
- Embeddings (bge-m3) + reranker are **local, key-free** — untouched by this change.
- `instructor==1.15.1` and `openai==2.38.0` are installed; `groq` lib is **not** needed
  (we use the OpenAI-compatible endpoint via `base_url`).
- Tests mostly mock the **high-level** hop (`_llm_classify`, `_llm_fuse`) returning fake
  Pydantic objects → provider-agnostic, unaffected. One test patches `_get_fusion_client`.
- `.env.example` already has a `GROQ_API_KEY` slot.

## 3. Approach (chosen: A — thin factory, keep per-node seams)

Extract client construction into one module. Each node keeps its `_get_*_client()`
name as a one-line delegate to the factory, preserving existing mocks and each node's
calibrated retry/fallback loop. (Rejected: B — a single `call_llm()` that rewrites every
node's control flow, higher risk, no functional gain; C — a provider class hierarchy,
YAGNI for two providers.)

## 4. Architecture

### New module: `agent/llm.py`

```
get_structured_client(role: str) -> tuple[InstructorClient, tuple[str, ...]]
```

- Reads `LLM_PROVIDER` env (default `"groq"`).
- `role` ∈ {`"classify"`, `"decompose"`, `"generate"`, `"synthesize"`} → maps to a
  **tier** (`lite` for classify/decompose, `main` for generate/synthesize).
- Returns the Instructor client **and** the ordered model list for that tier, so each
  node's existing "try models in order" loop keeps working.
- Raises a clear `RuntimeError` naming the missing key for the active provider.

| Provider | Client construction | Mode | main models | lite models |
|----------|--------------------|------|-------------|-------------|
| `groq` (default) | `instructor.from_openai(OpenAI(base_url="https://api.groq.com/openai/v1", api_key=$GROQ_API_KEY))` | `Mode.TOOLS` | `("llama-3.3-70b-versatile","llama-3.1-8b-instant")` | `("llama-3.1-8b-instant",)` |
| `gemini` (fallback) | `instructor.from_genai(genai.Client(api_key=$GEMINI_API_KEY))` | `GENAI_STRUCTURED_OUTPUTS` | `GEMINI_MODELS` | `reversed(GEMINI_MODELS)` |

Model lists live in `agent/policies.py` as `PROVIDER_MODELS[provider][tier]` (Gemini
constants stay; add Groq constants) so all tuning stays in one calibrated file.

### Node change (same shape ×4)

```python
# before: genai.Client(...) + instructor.from_genai(...) ; loop over GEMINI_MODELS
# after:
client, models = get_structured_client("classify")
for model in models:
    try:
        return client.chat.completions.create(model=model, response_model=…, messages=…)
    except Exception: ...
```

`_get_fusion_client()` / `_get_llm_client()` stay as thin delegates → the one test that
patches `_get_fusion_client` is unaffected.

## 5. Config & keys

- `.env` / `.env.example`: add `LLM_PROVIDER=groq`; `GROQ_API_KEY` (slot exists).
- `agent/demo.py` + `ui/deploy_guard.py`: the key-presence check becomes **provider-aware**
  (require `GROQ_API_KEY` when `LLM_PROVIDER=groq`, `GEMINI_API_KEY` when `gemini`).
- `policies.DEPLOY_DAILY_CAP` (=4, sized to Gemini's ~20 RPD) + the C4 quota-fallback copy
  become provider-aware: a higher cap for Groq's larger free tier. The graceful-degrade
  fallback UI is preserved; only the threshold + wording change.

## 6. Faithfulness guardrail (the real risk)

`cite_check` is **mechanism-agnostic** (a token-overlap ratio between the answer and the
retrieved context), but its threshold `CITE_CHECK_TOKEN_RATIO = 52` was calibrated to
**Gemini's** paraphrasing style. A different model can shift grounded-vs-hallucinated
overlap. Plan:

1. After the switch, re-run `scripts/calibrate_cite_check.py` against **Groq** on the
   labeled grounded/hallucinated set; adjust the constant **only if it moved** (with the
   same calibration comment style already used in `policies.py`).
2. Do **not** pre-guess a new value — the labeled set + the eval suite decide it.

This keeps the "no number faked / no silent citation regression" invariant intact.

## 7. Testing & verification

- **Offline unit suite** (`pytest tests/unit -q`) must stay green — high-level mocks make
  most tests provider-agnostic; expect no changes needed beyond the model-list assertions.
- **New** `tests/unit/test_llm_factory.py`: provider selection (`LLM_PROVIDER=groq|gemini`),
  correct tier→models mapping, and the clear missing-key error.
- **Live smoke test** (needs `GROQ_API_KEY`): run one real cited question end-to-end on
  Groq and confirm a grounded answer with a `[1]` citation chip and a passing `cite_check`.
- **Acceptance gates:** offline suite green + one live cited answer on Groq + `cite_check`
  pass-rate on the labeled set unchanged (or the constant re-calibrated with evidence).

## 8. Files touched (estimate)

- **New:** `agent/llm.py`, `tests/unit/test_llm_factory.py`.
- **Edit:** `agent/nodes/{classify,decompose,generate,synthesize}.py` (delegate + model
  source), `agent/policies.py` (`PROVIDER_MODELS`, provider-aware `DEPLOY_DAILY_CAP`),
  `agent/demo.py`, `ui/deploy_guard.py`, `.env.example`, `.env`.
- **Conditional:** `agent/policies.py` `CITE_CHECK_TOKEN_RATIO` (only if calibration moves it).

## 9. Risks & rollback

| Risk | Mitigation |
|------|------------|
| Citation faithfulness shifts on Llama-3.3-70B | cite_check recalibration step (§6) + eval suite gate |
| Groq structured-output (`Mode.TOOLS`) less reliable than Gemini's native mode | Instructor's `max_retries` re-prompt on ValidationError (already used); 70B handles tool-use well; 8B fallback in the model list |
| Groq rate-limit / 5xx | ordered model list (70B → 8B) + tenacity retry, mirroring the current Gemini 503 handling |
| Hidden Gemini assumption elsewhere | provider-aware key checks in `demo.py` + `deploy_guard.py`; grep sweep for `GEMINI_API_KEY` |

**Rollback:** set `LLM_PROVIDER=gemini` in `.env` — reverts to the exact current path with
no code change. The switch is one env var in both directions.

## 10. Out of scope (YAGNI)

Ollama support (a trivial future branch in the factory), streaming, prompt edits, any
change to embeddings/reranker/Qdrant, and the deploy itself (separate track).
