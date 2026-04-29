"""Conexus LLM gateway core.

Provider factory pattern adapted from ``KGB/backend/app/llm/__init__.py``.
KGB's ``stage_name`` indirection is replaced with a request-time ``model``
argument; provider selection happens at the gateway layer instead of the
router constructor.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.llm.anthropic_adapter import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    UnknownModelError,
)
from app.llm.gateway_router import GatewayProvider
from app.llm.openai_adapter import OpenAIProvider
from app.llm.pricing import get_cost
from app.llm.types import ChatMessage, ChatResult, TokenUsage

logger = logging.getLogger(__name__)


def make_provider(name: str | None = None) -> LLMProvider:
    """Return the configured provider.

    Selection order:
      ``"openai"``    → :class:`OpenAIProvider`
      ``"anthropic"`` → :class:`AnthropicProvider`
      ``"gateway"``   → :class:`GatewayProvider` (Anthropic primary, OpenAI fallback)

    The default is taken from ``LLM_PROVIDER`` (settings) when *name* is None.
    """
    chosen = (name or settings.llm_provider).lower()
    match chosen:
        case "openai":
            logger.info("llm_provider_selected provider=openai")
            return OpenAIProvider()
        case "anthropic":
            logger.info("llm_provider_selected provider=anthropic")
            return AnthropicProvider()
        case "gateway":
            logger.info("llm_provider_selected provider=gateway")
            return GatewayProvider()
        case other:
            raise ValueError(f"unknown LLM provider: {other!r}")


__all__ = [
    "AllProvidersFailedError",
    "AnthropicProvider",
    "ChatMessage",
    "ChatResult",
    "GatewayProvider",
    "LLMProvider",
    "OpenAIProvider",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderUnavailableError",
    "TokenUsage",
    "UnknownModelError",
    "get_cost",
    "make_provider",
]
