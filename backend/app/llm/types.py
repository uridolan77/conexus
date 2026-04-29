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
from typing import Literal, TypedDict


class ChatMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


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
