"""Gateway failover behaviour — KGB ConexusRouter parity test (simplified).

The KGB tests we mirror live in the KGB repo around ``ConexusRouter`` and
exercise the Anthropic→OpenAI failover path on retryable errors. We
re-state the same behaviour at the Conexus level: when the primary provider
raises ``ProviderRateLimitError`` or ``ProviderUnavailableError``, the
gateway should call the fallback and stamp ``fallback_used=True``.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.llm.base import LLMProvider
from app.llm.errors import ProviderError
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    UnknownModelError,
)
from app.llm.gateway_router import GatewayProvider
from app.llm.types import ChatMessage, ChatResult, ChatStreamChunk, TokenUsage


class _StubProvider(LLMProvider):
    def __init__(
        self,
        *,
        provider: str,
        result: ChatResult | None = None,
        raises: BaseException | None = None,
        stream_chunks: list[ChatStreamChunk] | None = None,
        stream_raises: BaseException | None = None,
    ) -> None:
        self._provider = provider
        self._result = result
        self._raises = raises
        self.calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []
        self._stream_chunks = stream_chunks or []
        self._stream_raises = stream_raises

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        self.calls.append({"messages": list(messages), "model": model})
        if self._raises is not None:
            raise self._raises
        assert self._result is not None
        return self._result

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        self.stream_calls.append({"messages": list(messages), "model": model})
        yielded = False
        for chunk in self._stream_chunks:
            yielded = True
            yield chunk
        if self._stream_raises is not None:
            raise self._stream_raises
        if not yielded:
            raise ProviderError(
                "streaming not configured in this stub",
                provider=self._provider,
            )

    async def aclose(self) -> None:
        pass


def _result(provider: str, model: str, content: str = "ok") -> ChatResult:
    return ChatResult(
        content=content,
        model=model,
        provider=provider,  # type: ignore[arg-type]
        usage=TokenUsage(input_tokens=1, output_tokens=2),
    )


@pytest.mark.asyncio
async def test_primary_success_no_fallback() -> None:
    primary = _StubProvider(
        provider="anthropic",
        result=_result("anthropic", "claude-sonnet-4-20250514"),
    )
    fallback = _StubProvider(
        provider="openai", result=_result("openai", "gpt-4o")
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    result = await gateway.chat(
        [{"role": "user", "content": "hi"}],
        model="conexus-default",
    )

    assert result.provider == "anthropic"
    assert result.fallback_used is False
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 0


@pytest.mark.asyncio
async def test_primary_rate_limit_falls_back_to_openai() -> None:
    primary = _StubProvider(
        provider="anthropic",
        raises=ProviderRateLimitError("429", provider="anthropic"),
    )
    fallback = _StubProvider(
        provider="openai", result=_result("openai", "gpt-4o")
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    result = await gateway.chat(
        [{"role": "user", "content": "hi"}],
        model="conexus-default",
    )

    assert result.provider == "openai"
    assert result.fallback_used is True
    assert primary.calls and fallback.calls


@pytest.mark.asyncio
async def test_primary_5xx_falls_back_to_openai() -> None:
    primary = _StubProvider(
        provider="anthropic",
        raises=ProviderUnavailableError("503", provider="anthropic"),
    )
    fallback = _StubProvider(
        provider="openai", result=_result("openai", "gpt-4o")
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    result = await gateway.chat(
        [{"role": "user", "content": "hi"}],
        model="conexus-default",
    )

    assert result.provider == "openai"
    assert result.fallback_used is True


@pytest.mark.asyncio
async def test_alias_resolves_to_provider_models() -> None:
    primary = _StubProvider(
        provider="anthropic",
        result=_result("anthropic", "claude-haiku-4-5-20251001"),
    )
    fallback = _StubProvider(
        provider="openai", result=_result("openai", "gpt-4o-mini")
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    await gateway.chat(
        [{"role": "user", "content": "hi"}],
        model="conexus-fast",
    )

    assert primary.calls[0]["model"] == "claude-haiku-4-5-20251001"


@pytest.mark.asyncio
async def test_conexus_fast_falls_back_to_openai_and_uses_alias_openai_model() -> None:
    primary = _StubProvider(
        provider="anthropic",
        raises=ProviderRateLimitError("429", provider="anthropic"),
    )
    fallback = _StubProvider(
        provider="openai", result=_result("openai", "gpt-4o-mini")
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    result = await gateway.chat(
        [{"role": "user", "content": "hi"}],
        model="conexus-fast",
    )

    assert result.provider == "openai"
    assert result.fallback_used is True
    assert primary.calls and fallback.calls
    assert fallback.calls[0]["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_both_providers_fail_raises_all_providers_failed() -> None:
    primary = _StubProvider(
        provider="anthropic",
        raises=ProviderRateLimitError("429", provider="anthropic"),
    )
    fallback = _StubProvider(
        provider="openai",
        raises=ProviderUnavailableError("503", provider="openai"),
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    with pytest.raises(AllProvidersFailedError):
        await gateway.chat(
            [{"role": "user", "content": "hi"}],
            model="conexus-default",
        )


@pytest.mark.asyncio
async def test_no_providers_configured_raises() -> None:
    gateway = GatewayProvider(primary=None, fallback=None)

    with pytest.raises(AllProvidersFailedError):
        await gateway.chat(
            [{"role": "user", "content": "hi"}],
            model="conexus-default",
        )


@pytest.mark.asyncio
async def test_unknown_model_raises_unknown_model_error() -> None:
    primary = _StubProvider(
        provider="anthropic",
        result=_result("anthropic", "claude-sonnet-4-20250514"),
    )
    fallback = _StubProvider(
        provider="openai", result=_result("openai", "gpt-4o")
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    # Typo: "gp-4o" instead of "gpt-4o" must not silently route to defaults.
    with pytest.raises(UnknownModelError) as excinfo:
        await gateway.chat(
            [{"role": "user", "content": "hi"}],
            model="gp-4o",
        )

    assert "gp-4o" in str(excinfo.value)
    # Neither provider should have been called.
    assert primary.calls == []
    assert fallback.calls == []


@pytest.mark.asyncio
async def test_concrete_anthropic_model_name_is_accepted() -> None:
    primary = _StubProvider(
        provider="anthropic",
        result=_result("anthropic", "claude-sonnet-4-20250514"),
    )
    fallback = _StubProvider(
        provider="openai", result=_result("openai", "gpt-4o")
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    result = await gateway.chat(
        [{"role": "user", "content": "hi"}],
        model="claude-sonnet-4-20250514",
    )
    assert result.provider == "anthropic"
    assert primary.calls[0]["model"] == "claude-sonnet-4-20250514"
    assert fallback.calls == []


@pytest.mark.asyncio
async def test_concrete_openai_model_routes_to_openai_only() -> None:
    primary = _StubProvider(
        provider="anthropic",
        result=_result("anthropic", "claude-sonnet-4-20250514"),
    )
    fallback = _StubProvider(
        provider="openai", result=_result("openai", "gpt-4o-mini")
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    result = await gateway.chat(
        [{"role": "user", "content": "hi"}],
        model="gpt-4o-mini",
    )

    assert result.provider == "openai"
    assert result.fallback_used is False
    assert primary.calls == []
    assert len(fallback.calls) == 1
    assert fallback.calls[0]["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_alias_streaming_routes_to_openai_until_anthropic_streaming_exists() -> None:
    primary = _StubProvider(
        provider="anthropic",
        stream_raises=ProviderError("anthropic streaming not supported", provider="anthropic"),
        result=_result("anthropic", "claude-haiku-4-5-20251001"),
    )
    fallback = _StubProvider(
        provider="openai",
        stream_chunks=[
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", content_delta="hi"),
        ],
        result=_result("openai", "gpt-4o-mini"),
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)

    chunks: list[ChatStreamChunk] = []
    async for chunk in gateway.stream_chat(
        [{"role": "user", "content": "hello"}],
        model="conexus-fast",
    ):
        chunks.append(chunk)

    # Primary shouldn't be used for alias streaming yet.
    assert primary.stream_calls == []
    assert fallback.stream_calls and fallback.stream_calls[0]["model"] == "gpt-4o-mini"
    assert chunks and chunks[0].provider == "openai"
