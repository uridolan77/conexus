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
from collections.abc import AsyncIterator
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
from app.llm.types import ChatMessage, ChatResult, ChatStreamChunk, TokenUsage

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

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AsyncIterator[ChatStreamChunk]:
        system_text, conversation = _split_system(messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": list(conversation),
        }
        if system_text:
            kwargs["system"] = system_text

        def _map_finish_reason(stop_reason: str | None) -> str | None:
            if stop_reason is None:
                return None
            # Anthropic stop reasons differ from OpenAI; map to OpenAI-ish values.
            if stop_reason in ("end_turn", "stop_sequence"):
                return "stop"
            if stop_reason == "max_tokens":
                return "length"
            # TODO(Mxx): Preserve "tool_use" once tool calling is supported.
            return "stop"

        def _safe_message(prefix: str) -> str:
            # Do not risk leaking secrets / headers from upstream error strings.
            return prefix

        sent_role = False
        last_stop_reason: str | None = None

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    event_type = getattr(event, "type", None)

                    if event_type == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        text = getattr(delta, "text", None)
                        if not text:
                            continue
                        role_delta = None
                        if not sent_role:
                            role_delta = "assistant"
                            sent_role = True
                        yield ChatStreamChunk(
                            provider="anthropic",
                            model=model,
                            role_delta=role_delta,
                            content_delta=text,
                        )
                        continue

                    if event_type == "message_delta":
                        delta = getattr(event, "delta", None)
                        stop_reason = getattr(delta, "stop_reason", None)
                        if stop_reason:
                            last_stop_reason = stop_reason
                        continue

                # Emit a final chunk with usage/finish reason if available.
                try:
                    final_message = await stream.get_final_message()
                except Exception as exc:
                    logger.debug(
                        "anthropic_stream_final_message_unavailable error_type=%s",
                        type(exc).__name__,
                    )
                    final_message = None

                finish_reason = _map_finish_reason(
                    getattr(final_message, "stop_reason", None) or last_stop_reason
                )
                usage = None
                if final_message is not None and getattr(final_message, "usage", None) is not None:
                    final_usage = getattr(final_message, "usage", None)
                    usage = TokenUsage(
                        input_tokens=getattr(final_usage, "input_tokens", 0) or 0,
                        output_tokens=getattr(final_usage, "output_tokens", 0) or 0,
                    )

                if finish_reason is not None or usage is not None:
                    yield ChatStreamChunk(
                        provider="anthropic",
                        model=model,
                        finish_reason=finish_reason,
                        usage=usage,
                    )
        except anthropic.RateLimitError as exc:
            raise ProviderRateLimitError(
                _safe_message("Anthropic rate limit exceeded."),
                provider=self.provider_name,
            ) from exc
        except (anthropic.APIConnectionError, anthropic.InternalServerError) as exc:
            raise ProviderUnavailableError(
                _safe_message("Anthropic is temporarily unavailable."),
                provider=self.provider_name,
            ) from exc
        except anthropic.AnthropicError as exc:
            raise ProviderError(
                _safe_message("Anthropic request failed."),
                provider=self.provider_name,
            ) from exc

    async def aclose(self) -> None:
        try:
            await self._client.close()
        except Exception as exc:
            logger.warning("anthropic_client_close_failed: %s", exc)
