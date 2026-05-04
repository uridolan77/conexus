"""OpenAI-compatible request/response schemas for POST /v1/chat/completions.

These types mirror the minimal subset of the OpenAI Chat Completions API that
Conexus exposes. Full OpenAI compatibility is not a goal; only the fields that
downstream clients genuinely need are accepted or returned.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessageBody(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionsRequest(BaseModel):
    model: str = Field(..., min_length=1)
    messages: list[ChatMessageBody] = Field(..., min_length=1)
    max_tokens: int = Field(default=4096, ge=1, le=128_000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # OpenAI-compat fields accepted for compatibility; most are ignored for now.
    stream: bool = False
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    stop: str | list[str] | None = None
    user: str | None = None
    response_format: dict[str, Any] | None = None
    seed: int | None = None
    n: int | None = Field(default=None, ge=1, le=128)
    tools: list[dict[str, Any]] | None = None
    tool_choice: dict[str, Any] | str | None = None
    logprobs: bool | None = None
    top_logprobs: int | None = Field(default=None, ge=0, le=20)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)


class _Choice(BaseModel):
    index: int
    message: ChatMessageBody
    finish_reason: str


class _Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionsResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    provider: str
    fallback_used: bool
    choices: list[_Choice]
    usage: _Usage
