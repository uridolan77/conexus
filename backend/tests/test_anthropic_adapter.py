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
from app.llm.errors import ProviderError, ProviderRateLimitError, ProviderUnavailableError
from app.llm.types import ChatStreamChunk, TokenUsage


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


# ── Streaming ───────────────────────────────────────────────────────────


class _FakeAnthropicStream:
    def __init__(self, events: list[Any], final_message: Any | None = None):
        self._events = list(events)
        self._final = final_message

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        async def _gen():
            for ev in self._events:
                if isinstance(ev, BaseException):
                    raise ev
                yield ev

        return _gen()

    async def get_final_message(self) -> Any:
        if isinstance(self._final, BaseException):
            raise self._final
        return self._final


class _FakeMessagesWithStream(_FakeMessages):
    def __init__(
        self,
        *,
        stream: _FakeAnthropicStream | None = None,
        stream_raises: BaseException | None = None,
        stream_enter_sequence: list[Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._stream = stream
        self._stream_raises = stream_raises
        self._stream_enter_sequence = (
            list(stream_enter_sequence) if stream_enter_sequence is not None else None
        )
        self.stream_calls: list[dict[str, Any]] = []

    def stream(self, **kwargs: Any) -> Any:
        self.stream_calls.append(kwargs)
        if self._stream_enter_sequence is not None:
            item = self._stream_enter_sequence.pop(0)
            if isinstance(item, BaseException):

                class _EnterRaises:
                    async def __aenter__(self_inner) -> None:
                        raise item

                    async def __aexit__(self_inner, *args: Any) -> bool:
                        return False

                return _EnterRaises()
            return item
        if self._stream_raises is not None:
            exc = self._stream_raises

            class _EnterRaisesSingle:
                async def __aenter__(self_inner) -> None:
                    raise exc

                async def __aexit__(self_inner, *args: Any) -> bool:
                    return False

            return _EnterRaisesSingle()
        assert self._stream is not None
        return self._stream


def _content_delta_event(text: str) -> Any:
    return SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text=text))


def _message_delta_event(stop_reason: str | None) -> Any:
    return SimpleNamespace(type="message_delta", delta=SimpleNamespace(stop_reason=stop_reason))


@pytest.mark.asyncio
async def test_anthropic_stream_happy_path_maps_text_deltas_and_role_once() -> None:
    stream = _FakeAnthropicStream(
        events=[
            _content_delta_event("hel"),
            _content_delta_event("lo"),
            _message_delta_event("end_turn"),
        ],
        final_message=SimpleNamespace(
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=3, output_tokens=2),
        ),
    )
    messages = _FakeMessagesWithStream(stream=stream, response=_ok_response("ignored", 0, 0))
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    chunks: list[ChatStreamChunk] = []
    async for chunk in provider.stream_chat(
        [{"role": "user", "content": "hi"}],
        model="claude-haiku-4-5-20251001",
    ):
        chunks.append(chunk)

    assert chunks[0].provider == "anthropic"
    assert chunks[0].model == "claude-haiku-4-5-20251001"
    assert chunks[0].role_delta == "assistant"
    assert chunks[0].content_delta == "hel"
    assert chunks[1].role_delta is None
    assert chunks[1].content_delta == "lo"
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage == TokenUsage(input_tokens=3, output_tokens=2)
    assert messages.stream_calls and messages.stream_calls[0]["model"] == "claude-haiku-4-5-20251001"


@pytest.mark.asyncio
async def test_anthropic_stream_usage_optional_when_not_available() -> None:
    stream = _FakeAnthropicStream(
        events=[_content_delta_event("hi"), _message_delta_event("end_turn")],
        final_message=SimpleNamespace(stop_reason="end_turn", usage=None),
    )
    messages = _FakeMessagesWithStream(stream=stream, response=_ok_response("ignored", 0, 0))
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    chunks = [c async for c in provider.stream_chat([{"role": "user", "content": "hi"}], model="claude-haiku-4-5-20251001")]
    assert any(c.content_delta for c in chunks)
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage is None


@pytest.mark.asyncio
async def test_anthropic_stream_rate_limit_error_is_normalized() -> None:
    messages = _FakeMessagesWithStream(stream_raises=_rate_limit_error(), response=_ok_response("ignored", 0, 0))
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    with pytest.raises(ProviderRateLimitError):
        async for _ in provider.stream_chat([{"role": "user", "content": "hi"}], model="claude-haiku-4-5-20251001"):
            pass


@pytest.mark.asyncio
async def test_anthropic_stream_connection_or_server_error_is_normalized() -> None:
    # InternalServerError is mapped to ProviderUnavailableError.
    messages = _FakeMessagesWithStream(stream_raises=_server_error(), response=_ok_response("ignored", 0, 0))
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    with pytest.raises(ProviderUnavailableError):
        async for _ in provider.stream_chat([{"role": "user", "content": "hi"}], model="claude-haiku-4-5-20251001"):
            pass


@pytest.mark.asyncio
async def test_anthropic_stream_generic_error_is_normalized_to_provider_error() -> None:
    messages = _FakeMessagesWithStream(
        stream_raises=anthropic.BadRequestError("bad", response=_http_response(400), body=None),
        response=_ok_response("ignored", 0, 0),
    )
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    with pytest.raises(ProviderError):
        async for _ in provider.stream_chat([{"role": "user", "content": "hi"}], model="claude-haiku-4-5-20251001"):
            pass


@pytest.mark.asyncio
async def test_anthropic_stream_transient_429_on_enter_then_success_yields_chunks() -> None:
    ok_stream = _FakeAnthropicStream(
        events=[_content_delta_event("x"), _message_delta_event("end_turn")],
        final_message=SimpleNamespace(stop_reason="end_turn", usage=None),
    )
    messages = _FakeMessagesWithStream(
        stream_enter_sequence=[
            _rate_limit_error(),
            _rate_limit_error(),
            ok_stream,
        ],
        response=_ok_response("ignored", 0, 0),
    )
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    chunks: list[ChatStreamChunk] = []
    async for chunk in provider.stream_chat(
        [{"role": "user", "content": "hi"}],
        model="claude-haiku-4-5-20251001",
    ):
        chunks.append(chunk)

    assert chunks[0].content_delta == "x"
    assert len(messages.stream_calls) == 3


@pytest.mark.asyncio
async def test_anthropic_stream_persistent_429_on_enter_retries_then_raises_normalized() -> None:
    messages = _FakeMessagesWithStream(
        stream_enter_sequence=[_rate_limit_error() for _ in range(ANTHROPIC_RETRY_ATTEMPTS)],
        response=_ok_response("ignored", 0, 0),
    )
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    with pytest.raises(ProviderRateLimitError):
        async for _ in provider.stream_chat(
            [{"role": "user", "content": "hi"}],
            model="claude-haiku-4-5-20251001",
        ):
            pass

    assert len(messages.stream_calls) == ANTHROPIC_RETRY_ATTEMPTS


# ── M2: retryable flag ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anthropic_rate_limit_error_is_retryable() -> None:
    """ProviderRateLimitError.retryable must be True (M2 requirement)."""
    messages = _FakeMessages(raises=_rate_limit_error())
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    with pytest.raises(ProviderRateLimitError) as exc_info:
        await provider.chat([{"role": "user", "content": "x"}], model="claude-haiku-4-5-20251001")

    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_anthropic_server_error_is_retryable() -> None:
    """ProviderUnavailableError.retryable must be True (M2 requirement)."""
    messages = _FakeMessages(raises=_server_error())
    provider = AnthropicProvider(client=_FakeAnthropic(messages))  # type: ignore[arg-type]

    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.chat([{"role": "user", "content": "x"}], model="claude-haiku-4-5-20251001")

    assert exc_info.value.retryable is True


# ── M2: aclose ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anthropic_aclose_calls_underlying_client_close() -> None:
    """aclose() must close the underlying SDK client (M2 requirement)."""
    closed: list[bool] = []

    class _TrackingAnthropic:
        messages = _FakeMessages()

        async def close(self) -> None:
            closed.append(True)

    provider = AnthropicProvider(client=_TrackingAnthropic())  # type: ignore[arg-type]
    await provider.aclose()

    assert closed == [True]


@pytest.mark.asyncio
async def test_anthropic_context_manager_closes_on_exit() -> None:
    """Using ``async with`` must call aclose() on exit (M2 requirement)."""
    closed: list[bool] = []

    class _TrackingAnthropic:
        messages = _FakeMessages()

        async def close(self) -> None:
            closed.append(True)

    async with AnthropicProvider(client=_TrackingAnthropic()):  # type: ignore[arg-type]
        pass

    assert closed == [True]
