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
from app.llm.openai_adapter import OpenAIProvider


class _FakeChatCompletions:
    def __init__(self, response: Any | None = None, raises: BaseException | None = None):
        self._response = response
        self._raises = raises
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
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
