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

from collections.abc import AsyncIterator
from typing import Literal

from app.core.config import settings
from app.llm.model_alias_config import (
    CONCRETE_ANTHROPIC_PREFIXES,
    CONCRETE_OPENAI_PREFIXES,
    ModelAliasConfig,
    load_model_alias_config,
    match_alias_models,
)
from app.llm.anthropic_adapter import (
    ANTHROPIC_FAILOVER_ERRORS,
    AnthropicProvider,
)
from app.llm.base import LLMProvider
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderError,
    UnknownModelError,
)
from app.llm.openai_adapter import OPENAI_FAILOVER_ERRORS, OpenAIProvider
from app.llm.types import ChatMessage, ChatResult, ChatStreamChunk

logger = logging.getLogger(__name__)

_MODEL_ALIAS_CONFIG: ModelAliasConfig | None = None


_Route = Literal["gateway", "anthropic_only", "openai_only"]


def _get_alias_config() -> ModelAliasConfig:
    global _MODEL_ALIAS_CONFIG
    if _MODEL_ALIAS_CONFIG is None:
        _MODEL_ALIAS_CONFIG = load_model_alias_config(settings.model_aliases_path)
    return _MODEL_ALIAS_CONFIG


def _reset_model_alias_config_for_tests() -> None:
    global _MODEL_ALIAS_CONFIG
    _MODEL_ALIAS_CONFIG = None


def get_model_aliases() -> dict[str, tuple[str, str]]:
    """Return a copy of current alias -> provider model mappings."""
    return dict(_get_alias_config().aliases)


def get_known_provider_prefixes() -> dict[str, tuple[str, ...]]:
    """Return concrete-model prefixes that bypass alias routing."""
    return {
        "anthropic": CONCRETE_ANTHROPIC_PREFIXES,
        "openai": CONCRETE_OPENAI_PREFIXES,
    }


def get_model_alias_config() -> ModelAliasConfig:
    """Shared alias config (same cache as gateway routing)."""
    return _get_alias_config()


def _resolve_models(model: str) -> tuple[_Route, str, str]:
    """Resolve a Conexus alias or concrete model name.

    Raises :class:`UnknownModelError` when *model* matches neither a known
    alias nor a recognised provider prefix — typos must not silently fall
    through to default models.
    """
    cfg = _get_alias_config()
    pair = match_alias_models(cfg, model)
    if pair is not None:
        anthropic_model, openai_model = pair
        return "gateway", anthropic_model, openai_model
    m = model.strip()
    if m.startswith(CONCRETE_ANTHROPIC_PREFIXES):
        # Concrete Anthropic model: do not attempt OpenAI unless the client
        # explicitly asked for a Conexus alias.
        return "anthropic_only", m, cfg.default_fallback_model
    if m.startswith(CONCRETE_OPENAI_PREFIXES):
        # Concrete OpenAI model: bypass Anthropic entirely.
        return "openai_only", cfg.default_primary_model, m
    raise UnknownModelError(
        model,
        known_aliases=list(cfg.aliases),
        provider_prefixes=get_known_provider_prefixes(),
    )


class GatewayProvider(LLMProvider):
    """Anthropic-primary, OpenAI-fallback gateway provider."""

    provider_name = "gateway"

    _UNSET = object()

    def __init__(
        self,
        *,
        primary: LLMProvider | None | object = _UNSET,
        fallback: LLMProvider | None | object = _UNSET,
    ) -> None:
        # Lazily build the underlying providers from settings, but only when
        # the corresponding API key is configured. A missing key disables that
        # provider entirely; if both are missing the first ``chat`` call will
        # raise ``AllProvidersFailedError``.
        if primary is not self._UNSET:
            self._primary = primary  # type: ignore[assignment]
        elif settings.anthropic_api_key:
            self._primary = AnthropicProvider()
        else:
            self._primary = None

        if fallback is not self._UNSET:
            self._fallback = fallback  # type: ignore[assignment]
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
        route, anthropic_model, openai_model = _resolve_models(model)

        if route == "openai_only":
            if self._fallback is None:
                raise AllProvidersFailedError(
                    "All configured LLM providers failed or are not configured."
                )
            return await self._fallback.chat(
                messages,
                model=openai_model,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        if route == "anthropic_only":
            if self._primary is None:
                raise AllProvidersFailedError(
                    "All configured LLM providers failed or are not configured."
                )
            return await self._primary.chat(
                messages,
                model=anthropic_model,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        # ── Primary: Anthropic ───────────────────────────────────────
        if self._primary is not None:
            try:
                return await self._primary.chat(
                    messages,
                    model=anthropic_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except ProviderError as exc:
                if not exc.retryable:
                    # Non-retryable (e.g. bad request, auth failure) — do not
                    # attempt fallback; the same request will fail there too.
                    raise
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
            except ProviderError as exc:
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

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str = "conexus-default",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AsyncIterator[ChatStreamChunk]:
        """Stream from a single selected route (no mid-stream fallback).

        Concrete provider model names bypass alias routing. Conexus aliases
        stream via the Anthropic primary model (matching non-streaming).
        """
        route, anthropic_model, openai_model = _resolve_models(model)

        if route == "openai_only":
            if self._fallback is None:
                raise AllProvidersFailedError(
                    "All configured LLM providers failed or are not configured."
                )
            async for chunk in self._fallback.stream_chat(
                messages,
                model=openai_model,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                yield chunk
            return

        if route == "anthropic_only":
            if self._primary is None:
                raise AllProvidersFailedError(
                    "All configured LLM providers failed or are not configured."
                )
            async for chunk in self._primary.stream_chat(
                messages,
                model=anthropic_model,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                yield chunk
            return

        # Alias routing: stream via Anthropic primary (no streaming fallback).
        if self._primary is None:
            raise AllProvidersFailedError(
                "All configured LLM providers failed or are not configured."
            )
        async for chunk in self._primary.stream_chat(
            messages,
            model=anthropic_model,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield chunk

    async def aclose(self) -> None:
        for provider in (self._primary, self._fallback):
            if provider is None:
                continue
            try:
                await provider.aclose()
            except Exception as exc:
                logger.warning("gateway_provider_close_failed: %s", exc)
