"""FastAPI dependency that yields an LLM provider for the request.

Lives in its own module so the test suite can override it without importing
the heavy SDK clients.

The default provider is still cached at process scope. For gateway requests,
we first attempt request-scoped BO-config resolution and fall back to the
cached default provider when no BO-backed provider is available.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.llm import LLMProvider, make_provider
from app.services.gateway_runtime_config_service import resolve_request_provider

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


async def get_provider(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[LLMProvider]:
    """FastAPI dependency.

    BO-configured providers are request scoped and closed after the request.
    The cached process-wide provider is used as fallback and is closed on
    application shutdown.
    """
    resolved = await resolve_request_provider(session)
    if resolved is None:
        yield get_default_provider()
        return

    try:
        yield resolved
    finally:
        await resolved.aclose()


async def shutdown_provider() -> None:
    global _provider
    if _provider is not None:
        try:
            await _provider.aclose()
        finally:
            _provider = None
