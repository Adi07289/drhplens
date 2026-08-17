"""Provider-agnostic structured-LLM factory (LLM_PROVIDER switch, 2026-08-17).

Single seam for (a) choosing the Instructor client and (b) choosing the model
list, so the agent runs on Groq (default) or Gemini (fallback) via one env var.
Node ``.chat.completions.create(response_model=...)`` calls are unchanged —
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
    """The active generation provider from ``LLM_PROVIDER`` (default ``groq``)."""
    return os.environ.get("LLM_PROVIDER", "groq").strip().lower()


def required_key_var(provider: str | None = None) -> str:
    """The env var name holding the API key for the given (or active) provider."""
    return _KEY_VAR.get(provider or active_provider(), "GROQ_API_KEY")


def provider_key_present(provider: str | None = None) -> bool:
    """True if the active (or given) provider's API key is set + non-empty."""
    return bool(os.environ.get(required_key_var(provider)))


def models_for(role: str) -> tuple[str, ...]:
    """Ordered model list for ``role`` under the active provider. No client build."""
    from agent.policies import PROVIDER_MODELS

    tier = _ROLE_TIER.get(role, "main")
    return PROVIDER_MODELS[active_provider()][tier]


def structured_client():
    """Construct an Instructor-wrapped client for the active provider.

    Raises ``RuntimeError`` naming the missing key for the active provider.
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
