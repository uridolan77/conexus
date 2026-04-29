"""Anthropic provider adapter.

Adapted from ``KGB/backend/app/llm/router.py``. Drops:

- Redis prompt cache, in-flight call coalescing, semantic cache.
- Shadow rollout (``shadow_model`` / ``shadow_percent``).
- ``BudgetContext`` parameter and distributed budget reserve.
- ``stage_name``-keyed routing table — replaced with explicit ``model`` arg.
- KGB Prometheus metrics and OTel shadow span.

What survives: the Anthropic ``messages.create`` call shape, retry-on-429/5xx
via ``tenacity``, and the input/output token usage mapping.

The ``messages`` parameter follows the OpenAI shape, so the system message is
extracted and passed via Anthropic's separate ``system=`` argument.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.errors import (
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.llm.types import ChatMessage, ChatResult, TokenUsage

logger = logging.getLogger(__name__)

_ANTHROPIC_RETRY_ERRORS = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
)

# Errors that the gateway should treat as failover candidates.
ANTHROPIC_FAILOVER_ERRORS: tuple[type[BaseException], ...] = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

ANTHROPIC_RETRY_ATTEMPTS = 3

_anthropic_retry = retry(
    retry=retry_if_exception_type(_ANTHROPIC_RETRY_ERRORS),
    wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
    stop=stop_after_attempt(ANTHROPIC_RETRY_ATTEMPTS),
    reraise=True,
)


@_anthropic_retry
async def _retried_anthropic_create(
    client: anthropic.AsyncAnthropic, **kwargs: Any
) -> Any:
    """Retry Anthropic ``messages.create`` on raw SDK 429/connection/5xx.

    Tenacity retries against the *raw* SDK exception types so the retry
    condition can match. ``AnthropicProvider.chat`` translates whatever
    escapes after retries are exhausted into provider-shaped errors.
    """
    return await client.messages.create(**kwargs)


def _split_system(messages: list[ChatMessage]) -> tuple[str, list[ChatMessage]]:
    """Pull leading system messages out for Anthropic's ``system=`` argument."""
    system_parts: list[str] = []
    rest: list[ChatMessage] = []
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content") or ""
            if content:
                system_parts.append(content)
        else:
            rest.append(msg)
    return "\n\n".join(system_parts), rest


class AnthropicProvider(LLMProvider):
    """Async Anthropic provider with retry on 429/5xx."""

    provider_name = "anthropic"

    def __init__(
        self,
        *,
        client: anthropic.AsyncAnthropic | None = None,
        api_key: str | None = None,
    ) -> None:
        self._client = client or anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        system_text, conversation = _split_system(messages)

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": list(conversation),
        }
        if system_text:
            kwargs["system"] = system_text

        try:
            response = await _retried_anthropic_create(self._client, **kwargs)
        except anthropic.RateLimitError as exc:
            raise ProviderRateLimitError(str(exc), provider=self.provider_name) from exc
        except (anthropic.APIConnectionError, anthropic.InternalServerError) as exc:
            raise ProviderUnavailableError(str(exc), provider=self.provider_name) from exc
        except anthropic.AnthropicError as exc:
            raise ProviderError(str(exc), provider=self.provider_name) from exc

        first_block = response.content[0] if response.content else None
        content = (
            first_block.text
            if first_block is not None and hasattr(first_block, "text")
            else ""
        )
        usage = TokenUsage(
            input_tokens=getattr(response.usage, "input_tokens", 0) or 0,
            output_tokens=getattr(response.usage, "output_tokens", 0) or 0,
        )
        return ChatResult(
            content=content,
            model=model,
            provider="anthropic",
            usage=usage,
        )

    async def aclose(self) -> None:
        try:
            await self._client.close()
        except Exception as exc:
            logger.warning("anthropic_client_close_failed: %s", exc)
