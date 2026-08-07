"""
agent/cache/ — the in-process semantic tool-result cache (Phase 6.3, D-06).

A best-effort, TTL-bounded, per-IPO semantic cache that protects the free-tier
Gemini quota by deduping the QUOTA-SCARCE LLM hops (classify / DRHP-RAG / synthesis)
keyed by free-text question semantics. It reuses the already-loaded bge-m3 embedder
(no new dependency). See `agent.cache.semantic_cache` for the module contract.
"""
