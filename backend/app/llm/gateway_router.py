"""Conexus gateway router — Anthropic primary with OpenAI failover.

Adapted from ``KGB/backend/app/llm/conexus_router.py``. Drops:

- ``CircuitBreakerRegistry`` (will return when we have multiple replicas).
- ``TokenTelemetry`` and distributed budget Redis reserve.
- ``BudgetContext`` parameter.
- Complexity-tier model selection (``select_anthropic_openai_models``).
- Anthropic prompt cache control blocks.
- ``agent_call`` (tool-calling) and ``batch_submit``.
- ``routing_store`` DB lookup.

What survives: try the primary provider, on a listed retryable error catch
and try the secondary, mark ``fallback_used=True`` on the result.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.llm.anthropic_adapter import (
    ANTHROPIC_FAILOVER_ERRORS,
    AnthropicProvider,
)
from app.llm.base import LLMProvider
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    UnknownModelError,
)
from app.llm.openai_adapter import OPENAI_FAILOVER_ERRORS, OpenAIProvider
from app.llm.types import ChatMessage, ChatResult

logger = logging.getLogger(__name__)

# Default model alias resolution. Can be overridden by passing an explicit
# model name into ``chat()``. Aliases let clients ask for ``conexus-fast``
# without knowing whether Anthropic or OpenAI served it.
DEFAULT_PRIMARY_MODEL = "claude-sonnet-4-20250514"
DEFAULT_FALLBACK_MODEL = "gpt-4o"

_MODEL_ALIASES: dict[str, tuple[str, str]] = {
    # alias -> (anthropic_model, openai_model)
    "conexus-fast": ("claude-haiku-4-5-20251001", "gpt-4o-mini"),
    "conexus-default": (DEFAULT_PRIMARY_MODEL, DEFAULT_FALLBACK_MODEL),
}


_KNOWN_ANTHROPIC_PREFIXES = ("claude-", "anthropic-")
_KNOWN_OPENAI_PREFIXES = ("gpt-", "o1-", "openai-")


def _resolve_models(model: str) -> tuple[str, str]:
    """Resolve a Conexus alias or concrete model name to (anthropic, openai).

    Raises :class:`UnknownModelError` when *model* matches neither a known
    alias nor a recognised provider prefix — typos must not silently fall
    through to default models.
    """
    if model in _MODEL_ALIASES:
        return _MODEL_ALIASES[model]
    if model.startswith(_KNOWN_ANTHROPIC_PREFIXES):
        return model, DEFAULT_FALLBACK_MODEL
    if model.startswith(_KNOWN_OPENAI_PREFIXES):
        return DEFAULT_PRIMARY_MODEL, model
    raise UnknownModelError(model, known_aliases=list(_MODEL_ALIASES))


class GatewayProvider(LLMProvider):
    """Anthropic-primary, OpenAI-fallback gateway provider."""

    provider_name = "gateway"

    def __init__(
        self,
        *,
        primary: LLMProvider | None = None,
        fallback: LLMProvider | None = None,
    ) -> None:
        # Lazily build the underlying providers from settings, but only when
        # the corresponding API key is configured. A missing key disables that
        # provider entirely; if both are missing the first ``chat`` call will
        # raise ``AllProvidersFailedError``.
        if primary is not None:
            self._primary: LLMProvider | None = primary
        elif settings.anthropic_api_key:
            self._primary = AnthropicProvider()
        else:
            self._primary = None

        if fallback is not None:
            self._fallback: LLMProvider | None = fallback
        elif settings.openai_api_key:
            self._fallback = OpenAIProvider()
        else:
            self._fallback = None

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str = "conexus-default",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        anthropic_model, openai_model = _resolve_models(model)

        # ── Primary: Anthropic ───────────────────────────────────────
        if self._primary is not None:
            try:
                return await self._primary.chat(
                    messages,
                    model=anthropic_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except (ProviderRateLimitError, ProviderUnavailableError) as exc:
                logger.warning(
                    "gateway_primary_failed_falling_back provider=anthropic err=%s",
                    exc,
                )
            except ANTHROPIC_FAILOVER_ERRORS as exc:
                # Direct SDK error leaked through — retry budget exhausted.
                logger.warning(
                    "gateway_primary_sdk_error_falling_back provider=anthropic err=%s",
                    exc,
                )

        # ── Fallback: OpenAI ─────────────────────────────────────────
        if self._fallback is not None:
            try:
                result = await self._fallback.chat(
                    messages,
                    model=openai_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                if self._primary is not None:
                    result.fallback_used = True
                return result
            except (ProviderRateLimitError, ProviderUnavailableError) as exc:
                logger.warning(
                    "gateway_fallback_failed provider=openai err=%s", exc
                )
            except OPENAI_FAILOVER_ERRORS as exc:
                logger.warning(
                    "gateway_fallback_sdk_error provider=openai err=%s", exc
                )

        raise AllProvidersFailedError(
            "All configured LLM providers failed or are not configured."
        )

    async def aclose(self) -> None:
        for provider in (self._primary, self._fallback):
            if provider is None:
                continue
            try:
                await provider.aclose()
            except Exception as exc:
                logger.warning("gateway_provider_close_failed: %s", exc)
