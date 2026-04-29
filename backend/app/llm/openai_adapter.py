"""OpenAI provider adapter.

Adapted from ``KGB/backend/app/llm/openai_router.py``. Drops:

- Redis prompt cache + circuit breaker mixin (KGB v1 only).
- Distributed budget reserve (``try_reserve_daily_llm_spend``).
- ``stage_name``-keyed routing table — replaced with a request-time ``model``.
- Semantic cache lookup/upsert.
- KGB Prometheus metrics (``LLM_TOKEN_USAGE`` / ``CACHE_REQUESTS``).
- ``BudgetContext`` parameter.

What survives: the OpenAI SDK call shape, retry-on-429/5xx via ``tenacity``,
and the prompt/completion → input/output token mapping.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
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

_OPENAI_RETRY_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
)

# Errors that the gateway should treat as failover candidates.
OPENAI_FAILOVER_ERRORS: tuple[type[BaseException], ...] = (
    openai.RateLimitError,
    openai.InternalServerError,
)

OPENAI_RETRY_ATTEMPTS = 3

_openai_retry = retry(
    retry=retry_if_exception_type(_OPENAI_RETRY_ERRORS),
    wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
    stop=stop_after_attempt(OPENAI_RETRY_ATTEMPTS),
    reraise=True,
)


@_openai_retry
async def _retried_openai_create(
    client: openai.AsyncOpenAI, **kwargs: Any
) -> Any:
    """Retry OpenAI chat completion creation on raw SDK 429/connection/5xx.

    Tenacity retries against the *raw* SDK exception types so the retry
    condition can match. ``OpenAIProvider.chat`` translates whatever escapes
    after retries are exhausted into the provider-shaped errors used by the
    rest of Conexus.
    """
    return await client.chat.completions.create(**kwargs)


@_openai_retry
async def _retried_openai_stream(client: openai.AsyncOpenAI, **kwargs: Any) -> Any:
    """Same retry policy as ``_retried_openai_create``, for stream creation only."""
    return await client.chat.completions.create(**kwargs)


class OpenAIProvider(LLMProvider):
    """Async OpenAI provider with retry on 429/5xx."""

    provider_name = "openai"

    def __init__(
        self,
        *,
        client: openai.AsyncOpenAI | None = None,
        api_key: str | None = None,
    ) -> None:
        self._client = client or openai.AsyncOpenAI(
            api_key=api_key or settings.openai_api_key
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        try:
            response = await _retried_openai_create(
                self._client,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=list(messages),
            )
        except openai.RateLimitError as exc:
            raise ProviderRateLimitError(str(exc), provider=self.provider_name) from exc
        except (openai.APIConnectionError, openai.InternalServerError) as exc:
            raise ProviderUnavailableError(str(exc), provider=self.provider_name) from exc
        except openai.OpenAIError as exc:
            raise ProviderError(str(exc), provider=self.provider_name) from exc

        choice = response.choices[0] if response.choices else None
        content = (choice.message.content if choice and choice.message else "") or ""
        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
        return ChatResult(
            content=content,
            model=model,
            provider="openai",
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
        try:
            stream = await _retried_openai_stream(
                self._client,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=list(messages),
                stream=True,
                stream_options={"include_usage": True},
            )
        except openai.RateLimitError as exc:
            raise ProviderRateLimitError(str(exc), provider=self.provider_name) from exc
        except (openai.APIConnectionError, openai.InternalServerError) as exc:
            raise ProviderUnavailableError(str(exc), provider=self.provider_name) from exc
        except openai.OpenAIError as exc:
            raise ProviderError(str(exc), provider=self.provider_name) from exc

        async for event in stream:
            choice = event.choices[0] if event.choices else None
            delta = choice.delta if choice else None

            role_delta = None
            if delta is not None and getattr(delta, "role", None):
                # OpenAI emits role only at the start.
                role_delta = "assistant"

            content_delta = ""
            if delta is not None and getattr(delta, "content", None):
                content_delta = delta.content or ""

            finish_reason = choice.finish_reason if choice else None

            usage = None
            if getattr(event, "usage", None) is not None:
                usage = TokenUsage(
                    input_tokens=getattr(event.usage, "prompt_tokens", 0) or 0,
                    output_tokens=getattr(event.usage, "completion_tokens", 0) or 0,
                )

            yield ChatStreamChunk(
                provider="openai",
                model=model,
                role_delta=role_delta,
                content_delta=content_delta,
                finish_reason=finish_reason,
                usage=usage,
            )

    async def aclose(self) -> None:
        try:
            await self._client.close()
        except Exception as exc:
            logger.warning("openai_client_close_failed: %s", exc)
