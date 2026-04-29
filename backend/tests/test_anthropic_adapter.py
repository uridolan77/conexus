"""AnthropicProvider tests using a fake AsyncAnthropic client."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.llm.anthropic_adapter import AnthropicProvider


class _FakeMessages:
    def __init__(self, response: Any | None = None, raises: BaseException | None = None):
        self._response = response
        self._raises = raises
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
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
