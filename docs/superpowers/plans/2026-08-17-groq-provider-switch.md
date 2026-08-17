# Groq Provider Switch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the generation LLM a single env switch (`LLM_PROVIDER`) so the agent runs on Groq (default) or Gemini (fallback), without changing any node's `.create(response_model=…)` call.

**Architecture:** One new `agent/llm.py` factory owns client construction + model selection per provider. The 4 agent nodes drop their inline Gemini client construction and call the factory; their Instructor `.chat.completions.create(...)` calls are unchanged (Instructor's unified interface). Model lists live in `agent/policies.py`.

**Tech Stack:** Python 3.11, `instructor==1.15.1`, `openai==2.38.0` (Groq via OpenAI-compat base_url), `google-genai` (Gemini fallback), `pytest`.

## Global Constraints

- Provider default: `LLM_PROVIDER` unset ⇒ `"groq"`. Values: `groq | gemini`.
- Groq endpoint: `https://api.groq.com/openai/v1`; Instructor mode `Mode.TOOLS`.
- Groq models: main `("llama-3.3-70b-versatile","llama-3.1-8b-instant")`, lite `("llama-3.1-8b-instant",)`. Both verified available on the account (2026-08-17).
- Gemini path unchanged: `instructor.from_genai(..., mode=Mode.GENAI_STRUCTURED_OUTPUTS)`, models `GEMINI_MODELS`.
- Do NOT change any `response_model=`, prompt, embedding, reranker, or Qdrant code.
- Rollback invariant: `LLM_PROVIDER=gemini` must restore today's exact behavior with no code edit.
- Offline unit suite (`pytest tests/unit -q`) must stay green after every task.

---

### Task 1: Provider model registry in policies

**Files:**
- Modify: `agent/policies.py` (add after the existing `GEMINI_MODELS` definition, ~line 76)
- Test: `tests/unit/test_llm_factory.py` (created here, extended in Task 2)

**Interfaces:**
- Produces: `PROVIDER_MODELS: dict[str, dict[str, tuple[str, ...]]]` with keys `"groq"`/`"gemini"`, each having `"main"`/`"lite"` tuples. `GROQ_MAIN_MODELS`, `GROQ_LITE_MODELS` tuples.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_llm_factory.py`:
```python
from agent.policies import PROVIDER_MODELS, GROQ_MAIN_MODELS, GROQ_LITE_MODELS, GEMINI_MODELS


def test_provider_models_registry_shape():
    assert set(PROVIDER_MODELS) == {"groq", "gemini"}
    for prov in PROVIDER_MODELS.values():
        assert set(prov) == {"main", "lite"}
        assert all(isinstance(m, str) and m for m in prov["main"])
        assert prov["lite"]  # non-empty

def test_groq_models_are_the_verified_ids():
    assert GROQ_MAIN_MODELS == ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")
    assert GROQ_LITE_MODELS == ("llama-3.1-8b-instant",)

def test_gemini_tier_reuses_existing_constant():
    assert PROVIDER_MODELS["gemini"]["main"] == GEMINI_MODELS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_llm_factory.py -q`
Expected: FAIL — `ImportError: cannot import name 'PROVIDER_MODELS'`.

- [ ] **Step 3: Add the registry to `agent/policies.py`**

Immediately after the `GEMINI_MODELS: tuple[str, ...] = (...)` line, add:
```python
# --- Provider model tiers (LLM_PROVIDER switch, 2026-08-17) ------------------
# Groq (default): Llama-3.3-70B for faithful synthesis, 8B-instant for the cheap
# high-frequency classify/decompose hops. Both IDs verified live on the account.
GROQ_MAIN_MODELS: tuple[str, ...] = ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")
GROQ_LITE_MODELS: tuple[str, ...] = ("llama-3.1-8b-instant",)

# role tier -> ordered model list, per provider. The Gemini "lite" tier keeps the
# historical "try -lite first" order (reversed GEMINI_MODELS).
PROVIDER_MODELS: dict[str, dict[str, tuple[str, ...]]] = {
    "groq": {"main": GROQ_MAIN_MODELS, "lite": GROQ_LITE_MODELS},
    "gemini": {"main": GEMINI_MODELS, "lite": tuple(reversed(GEMINI_MODELS))},
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/test_llm_factory.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**
```bash
git add agent/policies.py tests/unit/test_llm_factory.py
git commit -m "feat(llm): provider model registry (PROVIDER_MODELS) in policies"
```

---

### Task 2: The provider factory `agent/llm.py`

**Files:**
- Create: `agent/llm.py`
- Test: `tests/unit/test_llm_factory.py` (extend)

**Interfaces:**
- Produces:
  - `active_provider() -> str` — `LLM_PROVIDER` lowercased, default `"groq"`.
  - `required_key_var(provider: str | None = None) -> str` — `"GROQ_API_KEY"` or `"GEMINI_API_KEY"`.
  - `provider_key_present(provider: str | None = None) -> bool`.
  - `models_for(role: str) -> tuple[str, ...]` — reads `PROVIDER_MODELS` via `_ROLE_TIER`; NO client construction.
  - `structured_client() -> instructor client` — provider-scoped Instructor client; raises `RuntimeError` naming the missing key.
- Consumes: `agent.policies.PROVIDER_MODELS`.

- [ ] **Step 1: Write the failing tests** (append to `tests/unit/test_llm_factory.py`)
```python
import os
import pytest
from agent import llm


def test_active_provider_defaults_to_groq(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert llm.active_provider() == "groq"

def test_active_provider_reads_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "Gemini")
    assert llm.active_provider() == "gemini"

def test_models_for_maps_role_to_tier(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert llm.models_for("classify") == ("llama-3.1-8b-instant",)          # lite
    assert llm.models_for("synthesize") == ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")  # main

def test_required_key_var_by_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert llm.required_key_var() == "GROQ_API_KEY"
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    assert llm.required_key_var() == "GEMINI_API_KEY"

def test_structured_client_missing_key_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.structured_client()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/unit/test_llm_factory.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.llm'`.

- [ ] **Step 3: Create `agent/llm.py`**
```python
"""Provider-agnostic structured-LLM factory (LLM_PROVIDER switch, 2026-08-17).

Single seam for (a) choosing the Instructor client and (b) choosing the model
list, so the agent runs on Groq (default) or Gemini (fallback) via one env var.
Node `.chat.completions.create(response_model=...)` calls are unchanged —
Instructor exposes the same interface for every backend.
"""
from __future__ import annotations

import os

# role -> model tier. classify/decompose are high-frequency + cheap (lite);
# generate/synthesize are the faithful main tier.
_ROLE_TIER: dict[str, str] = {
    "classify": "lite",
    "decompose": "lite",
    "generate": "main",
    "synthesize": "main",
}

_KEY_VAR: dict[str, str] = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}


def active_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "groq").strip().lower()


def required_key_var(provider: str | None = None) -> str:
    return _KEY_VAR.get(provider or active_provider(), "GROQ_API_KEY")


def provider_key_present(provider: str | None = None) -> bool:
    return bool(os.environ.get(required_key_var(provider)))


def models_for(role: str) -> tuple[str, ...]:
    from agent.policies import PROVIDER_MODELS

    tier = _ROLE_TIER.get(role, "main")
    return PROVIDER_MODELS[active_provider()][tier]


def structured_client():
    """Construct an Instructor-wrapped client for the active provider.

    Raises RuntimeError naming the missing key for the active provider.
    """
    import instructor

    provider = active_provider()
    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY not set (LLM_PROVIDER=gemini). "
                "Export it, or set LLM_PROVIDER=groq."
            )
        from google import genai

        return instructor.from_genai(
            genai.Client(api_key=key), mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS
        )

    # default: groq via the OpenAI-compatible endpoint
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY not set (LLM_PROVIDER=groq). "
            "Export it, or set LLM_PROVIDER=gemini."
        )
    from openai import OpenAI

    return instructor.from_openai(
        OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key),
        mode=instructor.Mode.TOOLS,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/unit/test_llm_factory.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**
```bash
git add agent/llm.py tests/unit/test_llm_factory.py
git commit -m "feat(llm): provider factory (structured_client/models_for/active_provider)"
```

---

### Task 3: Route `classify.py` through the factory

**Files:**
- Modify: `agent/nodes/classify.py` (`_get_llm_client` body ~L116, `_llm_classify` loop ~L126-148)
- Test: `tests/unit/test_classify.py` (existing — must stay green; mocks `_llm_classify`)

**Interfaces:**
- Consumes: `agent.llm.structured_client`, `agent.llm.models_for`.

- [ ] **Step 1: Replace `_get_llm_client()` body**

Change the client construction (the `api_key = os.environ.get("GEMINI_API_KEY") … return instructor.from_genai(...)` block) to:
```python
def _get_llm_client():
    from agent.llm import structured_client

    return structured_client()
```
Remove the now-unused `genai`/`instructor` imports at the top of the file **only if** nothing else uses them (grep first: `grep -nE "genai|instructor" agent/nodes/classify.py`).

- [ ] **Step 2: Switch the model loop to the factory**

In `_llm_classify`, replace `from agent.policies import GEMINI_MODELS` + `for model in reversed(GEMINI_MODELS):` with:
```python
    from agent.llm import models_for

    client = _get_llm_client()
    ...
    last_exc: Exception | None = None
    for model in models_for("classify"):
        try:
            return client.chat.completions.create(
                model=model,
                response_model=RoutingDecision,
                messages=messages,
                temperature=0,
                max_tokens=256,
                max_retries=2,
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
    raise last_exc if last_exc is not None else RuntimeError("no classify model available")
```
(The `models_for("classify")` list is already lite-first — no `reversed()` needed.)

- [ ] **Step 3: Run the node's tests**

Run: `.venv/bin/python -m pytest tests/unit/test_classify.py -q`
Expected: PASS (tests mock `_llm_classify`, so they are provider-agnostic).

- [ ] **Step 4: Commit**
```bash
git add agent/nodes/classify.py
git commit -m "refactor(classify): use agent.llm factory instead of inline Gemini client"
```

---

### Task 4: Route `decompose.py` through the factory

**Files:**
- Modify: `agent/nodes/decompose.py` (`_get_llm_client` ~L63-86, loop ~L126-139)
- Test: `tests/unit/` decompose coverage (mocks the high-level hop).

- [ ] **Step 1: Replace `_get_llm_client()` body** (same as Task 3 Step 1):
```python
def _get_llm_client():
    from agent.llm import structured_client

    return structured_client()
```

- [ ] **Step 2: Switch the loop**

Replace `from agent.policies import GEMINI_MODELS` + `for model in GEMINI_MODELS:` with:
```python
    from agent.llm import models_for

    for model in models_for("decompose"):
        try:
            return client.chat.completions.create(
                model=model, response_model=SubQuestions, messages=messages
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
```
(Keep the surrounding `client = _get_llm_client()` and `last_exc` handling already present.)

- [ ] **Step 3: Run tests**

Run: `.venv/bin/python -m pytest tests/unit -q -k decompose`
Expected: PASS.

- [ ] **Step 4: Commit**
```bash
git add agent/nodes/decompose.py
git commit -m "refactor(decompose): use agent.llm factory"
```

---

### Task 5: Route `generate.py` through the factory

**Files:**
- Modify: `agent/nodes/generate.py` (inline client ~L84-92, loop ~L169-183)

- [ ] **Step 1: Wrap the inline client in a factory call**

Replace the `api_key = os.environ.get("GEMINI_API_KEY") … return instructor.from_genai(...)` construction with a call to `structured_client()` (introduce a local `_get_llm_client()` mirroring the other nodes if one does not exist):
```python
def _get_llm_client():
    from agent.llm import structured_client

    return structured_client()
```

- [ ] **Step 2: Switch the loop**

Replace `from agent.policies import GEMINI_MODELS` + `for model in GEMINI_MODELS:` with:
```python
    from agent.llm import models_for

    for model in models_for("generate"):
        try:
            return client.chat.completions.create(
                model=model,
                response_model=GroundedAnswer,
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
```
Preserve any existing `temperature`/`max_tokens` kwargs on the original `.create(...)` call verbatim.

- [ ] **Step 3: Run tests**

Run: `.venv/bin/python -m pytest tests/unit -q -k generate`
Expected: PASS.

- [ ] **Step 4: Commit**
```bash
git add agent/nodes/generate.py
git commit -m "refactor(generate): use agent.llm factory"
```

---

### Task 6: Route `synthesize.py` through the factory (preserve the `_get_fusion_client` test seam)

**Files:**
- Modify: `agent/nodes/synthesize.py` (import L53, `_get_fusion_client` ~L139-158, loop ~L211-218)
- Test: `tests/unit/test_synthesize_fusion.py` (existing — patches `_get_fusion_client` AND `_llm_fuse`).

- [ ] **Step 1: Keep `_get_fusion_client()` as the seam, delegating to the factory**
```python
def _get_fusion_client():
    from agent.llm import structured_client

    return structured_client()
```
(The one test that does `patch("agent.nodes.synthesize._get_fusion_client", return_value=client)` keeps working — the name is unchanged.)

- [ ] **Step 2: Switch the loop; remove the top-level `GEMINI_MODELS` import**

Delete `from agent.policies import GEMINI_MODELS` (L53). In `_llm_fuse`, replace `for model in GEMINI_MODELS:` with:
```python
    from agent.llm import models_for

    for model in models_for("synthesize"):
        try:
            return client.chat.completions.create(
                model=model,
                response_model=FusedAnswer,
                messages=messages,
                temperature=0,
                max_tokens=_FUSION_MAX_TOKENS,
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue
```

- [ ] **Step 3: Run tests**

Run: `.venv/bin/python -m pytest tests/unit/test_synthesize_fusion.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**
```bash
git add agent/nodes/synthesize.py
git commit -m "refactor(synthesize): use agent.llm factory; keep _get_fusion_client seam"
```

---

### Task 7: Provider-aware key check in `demo.py`

**Files:**
- Modify: `agent/demo.py` (`_check_env` ~L47-54, the warning copy ~L74-77)

- [ ] **Step 1: Make the required-key check provider-aware**

Replace the body of `_check_env`:
```python
def _check_env():
    """Return a list of missing environment variables required for live operation."""
    from agent.llm import required_key_var

    missing = []
    key_var = required_key_var()
    if not os.environ.get(key_var):
        missing.append(key_var)
    # QDRANT_URL defaults to localhost if not set; flag as a warning, not fatal
    return missing
```

- [ ] **Step 2: Update the guidance copy** (~L76) so it names the active provider's key:
```python
            f"  export {_check_env.__globals__.get('_active_key','GROQ_API_KEY')}=<your-key>\n"
```
Simpler and clearer — replace the whole hard-coded `export GEMINI_API_KEY=...` line with:
```python
            f"  export {__import__('agent.llm', fromlist=['required_key_var']).required_key_var()}=<your-key>\n"
```
(Keep the existing `QDRANT_URL` guidance line as-is.)

- [ ] **Step 3: Run tests**

Run: `.venv/bin/python -m pytest tests/unit -q -k demo`
Expected: PASS (or "no tests ran" if none — then run the smoke import: `.venv/bin/python -c "import agent.demo"`).

- [ ] **Step 4: Commit**
```bash
git add agent/demo.py
git commit -m "refactor(demo): provider-aware required-key check"
```

---

### Task 8: Config — default `LLM_PROVIDER=groq`

**Files:**
- Modify: `.env.example`, `.env`

- [ ] **Step 1: Add the switch to `.env.example`** (near the `GROQ_API_KEY` line):
```
# LLM provider for generation: groq (default, big free tier) | gemini (fallback)
LLM_PROVIDER=groq
```

- [ ] **Step 2: Set it in local `.env`** (append if absent):
```bash
grep -q '^LLM_PROVIDER=' .env || printf '\nLLM_PROVIDER=groq\n' >> .env
```

- [ ] **Step 3: Commit** (`.env` is gitignored — only `.env.example` is tracked)
```bash
git add .env.example
git commit -m "chore(env): document + default LLM_PROVIDER=groq"
```

---

### Task 9: Verification — offline suite, live Groq smoke, cite-check calibration

**Files:**
- Read/verify only; conditional edit to `agent/policies.py` `CITE_CHECK_TOKEN_RATIO` if calibration moves.

- [ ] **Step 1: Full offline unit suite green**

Run: `.venv/bin/python -m pytest tests/unit -q`
Expected: same pass count as the pre-change baseline (741 passed, 1 skipped) + the new `test_llm_factory.py` (≥8). No failures.

- [ ] **Step 2: Live Groq smoke test** (needs `GROQ_API_KEY` in `.env`, `LLM_PROVIDER=groq`)

Run one real classify + fuse round-trip:
```bash
.venv/bin/python -c "
from agent.nodes.classify import _llm_classify
d = _llm_classify('What is the issue size?')
print('classify OK:', type(d).__name__, d)
"
```
Expected: a `RoutingDecision` prints without a provider/auth error — confirms Groq structured output works end-to-end.

- [ ] **Step 3: cite_check calibration check on Groq**

Run: `.venv/bin/python scripts/calibrate_cite_check.py` (if present) OR the cite-check unit tests:
`.venv/bin/python -m pytest tests/unit -q -k cite_check`
Inspect the recommended `CITE_CHECK_TOKEN_RATIO`. **Only if** the labeled grounded/hallucinated classes no longer separate cleanly at `52`, update the constant in `agent/policies.py` with a dated calibration comment (matching the existing style), then commit:
```bash
git add agent/policies.py
git commit -m "chore(policies): recalibrate CITE_CHECK_TOKEN_RATIO for Groq (evidence in commit body)"
```
If the classes still separate at 52, leave it unchanged and note "no recalibration needed" — do NOT edit.

- [ ] **Step 4: Rollback sanity**

Run: `LLM_PROVIDER=gemini .venv/bin/python -m pytest tests/unit/test_llm_factory.py -q`
Expected: PASS — confirms the one-env-var rollback path is intact.

---

## Out of scope (explicit follow-ups, not this plan)

- **Provider-aware `DEPLOY_DAILY_CAP`** — Groq's free tier is far larger than Gemini's ~20 RPD, so the cap can be raised. Deferred to keep this plan's blast radius off `ui/deploy_guard.py` + its tests. Cap stays at the conservative `4` (safe on Groq) until a dedicated change updates `deploy_guard` + `test_deploy_guard.py` together.
- Ollama support (trivial third branch in `structured_client`).
- The Qdrant vector-store swap (separate decision/plan).

## Self-review notes

- Spec coverage: factory (§4) → T2; node refactor (§4) → T3-6; config (§5) → T8; provider-aware key check (§5) → T7; faithfulness guardrail (§6) → T9 Step 3; testing (§7) → T9. The `DEPLOY_DAILY_CAP` item (§5) is explicitly deferred above with rationale.
- Type consistency: `structured_client()` / `models_for(role)` / `active_provider()` / `required_key_var()` names used identically in T2 (def) and T3-7 (call).
- No placeholders: every code step shows real code; the one conditional (T9 Step 3) is gated on an explicit, checkable condition.
