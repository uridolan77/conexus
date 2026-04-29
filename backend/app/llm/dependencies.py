"""FastAPI dependency that yields an LLM provider for the request.

Lives in its own module so the test suite can override it without importing
the heavy SDK clients.

The provider is constructed once and cached at process scope. ``aclose`` is
called by the app shutdown hook in :mod:`app.main`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.config import settings
from app.llm import LLMProvider, make_provider

_provider: LLMProvider | None = None


def get_default_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = make_provider(settings.llm_provider)
    return _provider


def set_default_provider(provider: LLMProvider | None) -> None:
    """Override (or clear) the cached provider — used in tests."""
    global _provider
    _provider = provider


async def get_provider() -> AsyncIterator[LLMProvider]:
    """FastAPI dependency. Does not close the provider here — its lifetime
    matches the app, not the request, so ``aclose`` runs at shutdown.
    """
    yield get_default_provider()


async def shutdown_provider() -> None:
    global _provider
    if _provider is not None:
        try:
            await _provider.aclose()
        finally:
            _provider = None
