"""
app/observability/langfuse_client.py — Langfuse SDK init with no-op fallback.

Per D-04 / SKELETON cross-cutting invariant: every claim_id propagated through
the trace from Phase 1 day one; consumed by Phase 3 METHOD-01.

When LANGFUSE_PUBLIC_KEY is unset (local dev, CI without secrets), all helpers
return no-op objects so the agent runs unmodified without any Langfuse account.
"""
from __future__ import annotations

import functools
import os
from typing import Any


def is_enabled() -> bool:
    """Return True iff both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set."""
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")
    )


@functools.lru_cache(maxsize=1)
def get_client():
    """Return a langfuse.Langfuse instance if enabled, else None.

    Cached for the lifetime of the process — one client per deployment.

    Returns:
        langfuse.Langfuse instance or None.
    """
    if not is_enabled():
        return None
    try:
        from langfuse import Langfuse  # type: ignore[import]
    except ImportError:
        return None

    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    return Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=host,
    )


class _NoOpCallbackHandler:
    """Drop-in replacement for langfuse.callback.CallbackHandler when disabled.

    Every .on_*() method is a no-op so LangGraph callback plumbing works
    without any Langfuse credentials being present.
    """

    def __getattr__(self, name: str):
        """Return a no-op callable for any attribute access."""
        def _noop(*args: Any, **kwargs: Any) -> None:
            pass
        return _noop


def get_callback_handler():
    """Return a Langfuse CallbackHandler (or no-op) for LangGraph callback config.

    When is_enabled() is False, returns a _NoOpCallbackHandler that satisfies the
    LangGraph callbacks interface without making any HTTP calls.  This is the
    primary local-dev compatibility guarantee: the agent is fully runnable without
    a Langfuse account.

    Returns:
        langfuse.callback.CallbackHandler instance or _NoOpCallbackHandler.
    """
    if not is_enabled():
        return _NoOpCallbackHandler()
    try:
        from langfuse.callback import CallbackHandler  # type: ignore[import]
    except ImportError:
        return _NoOpCallbackHandler()

    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    return CallbackHandler(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=host,
    )
