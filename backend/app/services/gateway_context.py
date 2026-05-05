"""Response DTOs for gateway chat orchestration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.llm.types import ChatResult, ChatStreamChunk


@dataclass(slots=True)
class GatewayResponse:
    request_id: str
    result: ChatResult
    cost_usd: float


@dataclass(slots=True)
class GatewayStreamResponse:
    request_id: str
    stream: AsyncIterator[ChatStreamChunk]
