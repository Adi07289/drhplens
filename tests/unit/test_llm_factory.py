"""Unit tests for the LLM provider switch (agent/policies model registry + agent/llm factory)."""
import os

import pytest

from agent.policies import (
    GEMINI_MODELS,
    GROQ_LITE_MODELS,
    GROQ_MAIN_MODELS,
    PROVIDER_MODELS,
)


# --- Task 1: provider model registry ---------------------------------------


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
