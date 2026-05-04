"""Shared test fixtures."""
import pytest

from agentor_runtime.clients.conexus import ConexusClient, ConexusResponse, ConexusUsage


def make_conexus_response(
    content: str = "test response",
    model: str = "conexus-fast",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> ConexusResponse:
    return ConexusResponse(
        id="chatcmpl_test_001",
        model=model,
        content=content,
        finish_reason="stop",
        usage=ConexusUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


class MockConexusClient:
    """Synchronously-configured mock Conexus client for tests."""

    def __init__(self) -> None:
        self._responses: dict[str, ConexusResponse] = {}
        self._default: ConexusResponse = make_conexus_response()
        self.calls: list[dict] = []

    def set_response(self, model: str, response: ConexusResponse) -> None:
        self._responses[model] = response

    def set_default(self, response: ConexusResponse) -> None:
        self._default = response

    async def chat(
        self,
        model: str,
        messages: list[dict],
        **kwargs,
    ) -> ConexusResponse:
        self.calls.append({"model": model, "messages": messages, **kwargs})
        return self._responses.get(model, self._default)

    async def aclose(self) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
