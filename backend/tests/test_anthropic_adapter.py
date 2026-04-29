"""AnthropicProvider tests using a fake AsyncAnthropic client."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import pytest

from app.llm.anthropic_adapter import (
    ANTHROPIC_RETRY_ATTEMPTS,
    AnthropicProvider,
)
from app.llm.errors import ProviderRateLimitError, ProviderUnavailableError


class _FakeMessages:
    def __init__(
        self,
        response: Any | None = None,
        raises: BaseException | None = None,
        sequence: list[Any] | None = None,
    ):
        self._response = response
        self._raises = raises
        self._sequence = list(sequence) if sequence is not None else None
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._sequence is not None:
            item = self._sequence.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        if self._raises is not None:
            raise self._raises
        return self._response


class _FakeAnthropic:
    def __init__(self, messages: _FakeMessages):
        self.messages = messages

    async def close(self) -> None:
        pass


def _ok_response(content: str = "hi", inp: int = 7, out: int = 4) -> Any:
    return SimpleNamespace(
        content=[SimpleNamespace(text=content)],
        usage=SimpleNamespace(input_tokens=inp, output_tokens=out),
    )


@pytest.mark.asyncio
async def test_anthropic_happy_path() -> None:
    messages = _FakeMessages(response=_ok_response("hi from claude", 3, 8))
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    result = await provider.chat(
        [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "hi"},
        ],
        model="claude-haiku-4-5-20251001",
    )

    assert result.content == "hi from claude"
    assert result.provider == "anthropic"
    assert result.usage.input_tokens == 3
    assert result.usage.output_tokens == 8

    sent = messages.calls[0]
    assert sent["model"] == "claude-haiku-4-5-20251001"
    assert sent["system"] == "be brief"
    assert sent["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_anthropic_no_system_message_omits_system_kwarg() -> None:
    messages = _FakeMessages(response=_ok_response("ok", 1, 1))
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    await provider.chat(
        [{"role": "user", "content": "hi"}],
        model="claude-haiku-4-5-20251001",
    )

    assert "system" not in messages.calls[0]


@pytest.mark.asyncio
async def test_anthropic_empty_content_block() -> None:
    messages = _FakeMessages(
        response=SimpleNamespace(
            content=[],
            usage=SimpleNamespace(input_tokens=0, output_tokens=0),
        )
    )
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    result = await provider.chat(
        [{"role": "user", "content": "hi"}],
        model="claude-haiku-4-5-20251001",
    )
    assert result.content == ""


def _http_response(status: int) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )


def _rate_limit_error() -> anthropic.RateLimitError:
    return anthropic.RateLimitError(
        "slow down", response=_http_response(429), body=None
    )


def _server_error() -> anthropic.InternalServerError:
    return anthropic.InternalServerError(
        "boom", response=_http_response(500), body=None
    )


@pytest.mark.asyncio
async def test_anthropic_persistent_429_retries_then_raises_normalized() -> None:
    messages = _FakeMessages(
        sequence=[_rate_limit_error() for _ in range(ANTHROPIC_RETRY_ATTEMPTS)]
    )
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    with pytest.raises(ProviderRateLimitError):
        await provider.chat(
            [{"role": "user", "content": "x"}],
            model="claude-haiku-4-5-20251001",
        )

    assert len(messages.calls) == ANTHROPIC_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_anthropic_persistent_5xx_retries_then_raises_normalized() -> None:
    messages = _FakeMessages(
        sequence=[_server_error() for _ in range(ANTHROPIC_RETRY_ATTEMPTS)]
    )
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    with pytest.raises(ProviderUnavailableError):
        await provider.chat(
            [{"role": "user", "content": "x"}],
            model="claude-haiku-4-5-20251001",
        )

    assert len(messages.calls) == ANTHROPIC_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_anthropic_transient_429_then_success_returns_chat_result() -> None:
    messages = _FakeMessages(
        sequence=[
            _rate_limit_error(),
            _rate_limit_error(),
            _ok_response("recovered", 2, 3),
        ]
    )
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    result = await provider.chat(
        [{"role": "user", "content": "x"}],
        model="claude-haiku-4-5-20251001",
    )

    assert result.content == "recovered"
    assert result.provider == "anthropic"
    assert result.usage.input_tokens == 2
    assert result.usage.output_tokens == 3
    assert len(messages.calls) == 3


@pytest.mark.asyncio
async def test_anthropic_transient_5xx_then_success_returns_chat_result() -> None:
    messages = _FakeMessages(
        sequence=[_server_error(), _ok_response("ok", 1, 1)]
    )
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    result = await provider.chat(
        [{"role": "user", "content": "x"}],
        model="claude-haiku-4-5-20251001",
    )

    assert result.content == "ok"
    assert len(messages.calls) == 2
