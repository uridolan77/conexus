"""Shared LLM types.

Adapted from ``KGB/backend/app/llm/router.py`` (``LLMCallResult``) and
``KGB/backend/app/llm/conexus_types.py`` (``TokenUsage``), simplified for the
Conexus gateway:

- KGB's ``stage_name``-indexed routing is replaced with an explicit ``model``
  argument on :class:`ChatResult`.
- ``cached`` field is reserved for a future cache module.
- ``TokenUsage`` is a plain dataclass instead of a TypedDict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict


class ChatMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant"]
    content: str


# Explicit alias used in M1 / provider-adapter layer.
Message = ChatMessage


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class ToolCallFunction(TypedDict):
    """Function spec inside a tool call (OpenAI format)."""

    name: str
    arguments: str  # JSON-encoded kwargs


class ToolCall(TypedDict):
    """A single tool invocation requested by the model."""

    id: str
    type: str  # always "function"
    function: ToolCallFunction


@dataclass(slots=True)
class ProviderRequest:
    """Normalised request handed to a provider adapter.

    ``model`` should be the concrete model name (e.g. ``"gpt-4o-mini"``)
    resolved before the call; the adapter does no further alias resolution.
    """

    model: str
    messages: list[ChatMessage]
    temperature: float = 0.2
    max_tokens: int = 4096
    tools: list[dict[str, Any]] | None = None
    request_id: str | None = None
    project_id: str | None = None


@dataclass(slots=True)
class ProviderResponse:
    """Normalised response from a provider adapter.

    Maps to the fields Conexus needs for request logging and
    OpenAI-compatible response serialisation.
    """

    content: str
    model: str
    provider: Literal["openai", "anthropic"]
    usage: TokenUsage = field(default_factory=lambda: TokenUsage())
    tool_calls: list[ToolCall] | None = None
    fallback_used: bool = False
    cached: bool = False


@dataclass(slots=True)
class ChatResult:
    """Normalised chat completion result.

    ``provider`` records which provider actually served the response —
    important for the gateway router which may have failed over.
    """

    content: str
    model: str
    provider: Literal["openai", "anthropic"]
    usage: TokenUsage = field(default_factory=TokenUsage)
    fallback_used: bool = False
    cached: bool = False


@dataclass(slots=True)
class ChatStreamChunk:
    """A single streaming chunk in a normalized shape.

    This is an internal type used to translate provider-specific streaming
    events into OpenAI-compatible SSE output.
    """

    provider: Literal["openai", "anthropic"]
    model: str
    role_delta: Literal["assistant"] | None = None
    content_delta: str = ""
    finish_reason: str | None = None
    usage: TokenUsage | None = None
    fallback_used: bool = False
