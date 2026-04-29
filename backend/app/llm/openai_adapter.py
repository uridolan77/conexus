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

import openai
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

_openai_retry = retry(
    retry=retry_if_exception_type(_OPENAI_RETRY_ERRORS),
    wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
    stop=stop_after_attempt(3),
    reraise=True,
)


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

    @_openai_retry
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        try:
            response = await self._client.chat.completions.create(
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

    async def aclose(self) -> None:
        try:
            await self._client.close()
        except Exception as exc:
            logger.warning("openai_client_close_failed: %s", exc)
