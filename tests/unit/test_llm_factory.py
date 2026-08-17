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


# --- Task 2: the provider factory ------------------------------------------

from agent import llm  # noqa: E402


def test_active_provider_defaults_to_groq(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert llm.active_provider() == "groq"


def test_active_provider_reads_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "Gemini")
    assert llm.active_provider() == "gemini"


def test_models_for_maps_role_to_tier(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert llm.models_for("classify") == ("llama-3.1-8b-instant",)  # lite
    assert llm.models_for("synthesize") == (
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    )  # main


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
