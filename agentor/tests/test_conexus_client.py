"""Tests for ConexusClient."""
import json

import httpx
import pytest
import respx

from app.clients.conexus import ConexusClient, ConexusClientError

_BASE = "http://conexus-test"
_KEY = "cx_test_key"
_VALID_RESPONSE = {
    "id": "chatcmpl_001",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "conexus-fast",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello!"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
}


@respx.mock
async def test_chat_success():
    respx.post(f"{_BASE}/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_VALID_RESPONSE)
    )

    async with ConexusClient(base_url=_BASE, api_key=_KEY) as client:
        response = await client.chat(
            model="conexus-fast",
            messages=[{"role": "user", "content": "Hi"}],
        )

    assert response.id == "chatcmpl_001"
    assert response.model == "conexus-fast"
    assert response.content == "Hello!"
    assert response.finish_reason == "stop"
    assert response.usage.prompt_tokens == 10
    assert response.usage.completion_tokens == 3
    assert response.usage.total_tokens == 13


@respx.mock
async def test_chat_sends_bearer_auth():
    route = respx.post(f"{_BASE}/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_VALID_RESPONSE)
    )

    async with ConexusClient(base_url=_BASE, api_key=_KEY) as client:
        await client.chat(model="conexus-fast", messages=[{"role": "user", "content": "Hi"}])

    request = route.calls[0].request
    assert request.headers["authorization"] == f"Bearer {_KEY}"


@respx.mock
async def test_chat_http_error_raises_client_error():
    respx.post(f"{_BASE}/v1/chat/completions").mock(
        return_value=httpx.Response(
            502,
            json={"error": {"code": "llm_gateway_error", "message": "All providers failed"}},
        )
    )

    async with ConexusClient(base_url=_BASE, api_key=_KEY) as client:
        with pytest.raises(ConexusClientError) as exc_info:
            await client.chat(model="conexus-fast", messages=[])

    assert exc_info.value.status_code == 502


@respx.mock
async def test_chat_401_raises_client_error():
    respx.post(f"{_BASE}/v1/chat/completions").mock(
        return_value=httpx.Response(401, json={"detail": "Invalid API key"})
    )

    async with ConexusClient(base_url=_BASE, api_key=_KEY) as client:
        with pytest.raises(ConexusClientError) as exc_info:
            await client.chat(model="conexus-fast", messages=[])

    assert exc_info.value.status_code == 401


@respx.mock
async def test_chat_malformed_response_raises_client_error():
    respx.post(f"{_BASE}/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"unexpected": "shape"})
    )

    async with ConexusClient(base_url=_BASE, api_key=_KEY) as client:
        with pytest.raises(ConexusClientError):
            await client.chat(model="conexus-fast", messages=[])


async def test_chat_network_error_raises_client_error():
    transport = httpx.MockTransport(
        lambda req: (_ for _ in ()).throw(
            httpx.ConnectError("connection refused")
        )
    )
    http = httpx.AsyncClient(transport=transport)

    client = ConexusClient(base_url=_BASE, api_key=_KEY, _http_client=http)
    with pytest.raises(ConexusClientError) as exc_info:
        await client.chat(model="conexus-fast", messages=[])

    assert "Request failed" in str(exc_info.value)
