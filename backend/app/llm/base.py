"""LLMProvider — abstract base class for Conexus LLM providers.

Adapted from ``KGB/backend/app/llm/base.py``. Differences from KGB:

- ``call(stage_name, system, user)`` becomes ``chat(messages, model)`` so the
  surface is OpenAI-compatible and free of KG pipeline assumptions.
- ``stream_call`` and ``estimate_stage_cost`` are removed from the v1 surface;
  they will return when streaming and budgets are needed.
- ``BudgetContext`` parameter is dropped.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self

from app.llm.types import ChatMessage, ChatResult


class LLMProvider(ABC):
    """Abstract base class for LLM provider adapters.

    Subclasses implement a single non-streaming ``chat()`` call and an
    ``aclose()`` for HTTP client shutdown. The async context manager
    protocol delegates to :meth:`aclose`.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        """Make a non-streaming chat completion call."""

    @abstractmethod
    async def aclose(self) -> None:
        """Release the underlying HTTP client."""

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        await self.aclose()
