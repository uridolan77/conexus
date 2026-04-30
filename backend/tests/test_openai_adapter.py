"""OpenAIProvider tests using a fake AsyncOpenAI client.

Mirrors the behaviour KGB tested in ``OpenAIRouter`` but limited to the M1
non-streaming surface.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import openai
import pytest

from app.llm.errors import ProviderRateLimitError, ProviderUnavailableError
from app.llm.openai_adapter import OPENAI_RETRY_ATTEMPTS, OpenAIProvider


class _FakeAsyncStream:
    """Minimal async iterator returned as ``stream=True`` result."""

    def __init__(self) -> None:
        self._done = False

    def __aiter__(self) -> "_FakeAsyncStream":
        return self

    async def __anext__(self) -> Any:
        if self._done:
            raise StopAsyncIteration
        self._done = True
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(role=None, content="x"),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )


class _FakeChatCompletions:
    """Fake ``client.chat.completions`` whose ``create`` either returns a single
    response, raises a single exception, or replays a scripted sequence of
    results/exceptions in order — used to exercise retry behaviour.
    """

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


class _FakeChat:
    def __init__(self, completions: _FakeChatCompletions):
        self.completions = completions


class _FakeOpenAI:
    def __init__(self, completions: _FakeChatCompletions):
        self.chat = _FakeChat(completions)

    async def close(self) -> None:
        pass


def _ok_response(content: str = "hi", prompt: int = 7, completion: int = 4) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion),
    )


@pytest.mark.asyncio
async def test_openai_happy_path() -> None:
    completions = _FakeChatCompletions(response=_ok_response("hello there", 5, 11))
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    result = await provider.chat(
        [{"role": "user", "content": "hello"}],
        model="gpt-4o-mini",
    )

    assert result.content == "hello there"
    assert result.model == "gpt-4o-mini"
    assert result.provider == "openai"
    assert result.usage.input_tokens == 5
    assert result.usage.output_tokens == 11
    assert completions.calls[0]["model"] == "gpt-4o-mini"
    assert completions.calls[0]["messages"] == [{"role": "user", "content": "hello"}]


def _make_response_with_request_obj() -> Any:
    """OpenAI's APIError requires a ``request`` and ``body`` argument."""
    import httpx

    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


@pytest.mark.asyncio
async def test_openai_rate_limit_normalised() -> None:
    err = openai.RateLimitError(
        "slow down",
        response=_FakeHTTPResponse(429),
        body=None,
    )
    completions = _FakeChatCompletions(raises=err)
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    with pytest.raises(ProviderRateLimitError):
        await provider.chat(
            [{"role": "user", "content": "x"}],
            model="gpt-4o-mini",
        )


@pytest.mark.asyncio
async def test_openai_5xx_normalised() -> None:
    err = openai.InternalServerError(
        "server is sad",
        response=_FakeHTTPResponse(500),
        body=None,
    )
    completions = _FakeChatCompletions(raises=err)
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    with pytest.raises(ProviderUnavailableError):
        await provider.chat(
            [{"role": "user", "content": "x"}],
            model="gpt-4o-mini",
        )


class _FakeHTTPResponse:
    """Minimal stand-in for httpx.Response that openai SDK errors accept."""

    def __init__(self, status_code: int):
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        import httpx

        self.request = httpx.Request("POST", "https://api.openai.com/")


def _rate_limit_error() -> openai.RateLimitError:
    return openai.RateLimitError(
        "slow down", response=_FakeHTTPResponse(429), body=None
    )


def _server_error() -> openai.InternalServerError:
    return openai.InternalServerError(
        "boom", response=_FakeHTTPResponse(500), body=None
    )


@pytest.mark.asyncio
async def test_openai_persistent_429_retries_then_raises_normalized() -> None:
    completions = _FakeChatCompletions(
        sequence=[_rate_limit_error() for _ in range(OPENAI_RETRY_ATTEMPTS)]
    )
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    with pytest.raises(ProviderRateLimitError):
        await provider.chat(
            [{"role": "user", "content": "x"}],
            model="gpt-4o-mini",
        )

    assert len(completions.calls) == OPENAI_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_openai_persistent_5xx_retries_then_raises_normalized() -> None:
    completions = _FakeChatCompletions(
        sequence=[_server_error() for _ in range(OPENAI_RETRY_ATTEMPTS)]
    )
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    with pytest.raises(ProviderUnavailableError):
        await provider.chat(
            [{"role": "user", "content": "x"}],
            model="gpt-4o-mini",
        )

    assert len(completions.calls) == OPENAI_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_openai_transient_429_then_success_returns_chat_result() -> None:
    completions = _FakeChatCompletions(
        sequence=[
            _rate_limit_error(),
            _rate_limit_error(),
            _ok_response("recovered", 2, 3),
        ]
    )
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    result = await provider.chat(
        [{"role": "user", "content": "x"}],
        model="gpt-4o-mini",
    )

    assert result.content == "recovered"
    assert result.provider == "openai"
    assert result.usage.input_tokens == 2
    assert result.usage.output_tokens == 3
    assert len(completions.calls) == 3


async def _collect_stream(provider: OpenAIProvider) -> list[Any]:
    chunks: list[Any] = []
    async for chunk in provider.stream_chat(
        [{"role": "user", "content": "x"}],
        model="gpt-4o-mini",
    ):
        chunks.append(chunk)
    return chunks


@pytest.mark.asyncio
async def test_openai_stream_transient_429_then_success_yields_chunks() -> None:
    completions = _FakeChatCompletions(
        sequence=[
            _rate_limit_error(),
            _rate_limit_error(),
            _FakeAsyncStream(),
        ]
    )
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    chunks = await _collect_stream(provider)

    assert len(chunks) == 1
    assert chunks[0].content_delta == "x"
    assert len(completions.calls) == 3


@pytest.mark.asyncio
async def test_openai_stream_persistent_429_retries_then_raises_normalized() -> None:
    completions = _FakeChatCompletions(
        sequence=[_rate_limit_error() for _ in range(OPENAI_RETRY_ATTEMPTS)]
    )
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    with pytest.raises(ProviderRateLimitError):
        await _collect_stream(provider)

    assert len(completions.calls) == OPENAI_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_openai_transient_5xx_then_success_returns_chat_result() -> None:
    completions = _FakeChatCompletions(
        sequence=[_server_error(), _ok_response("ok", 1, 1)]
    )
    provider = OpenAIProvider(client=_FakeOpenAI(completions))  # type: ignore[arg-type]

    result = await provider.chat(
        [{"role": "user", "content": "x"}],
        model="gpt-4o-mini",
    )

    assert result.content == "ok"
    assert len(completions.calls) == 2
