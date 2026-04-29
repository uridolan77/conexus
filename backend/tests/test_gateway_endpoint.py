"""End-to-end tests for POST /v1/chat/completions (M2)."""

from __future__ import annotations

from datetime import datetime, timezone
import asyncio
import uuid
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.gateway import REQUEST_ID_HEADER
from app.db import models
from app.db.session import get_db_sessionmaker, get_session
from app.llm.base import LLMProvider
from app.llm.dependencies import get_provider
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    UnknownModelError,
)
from app.llm.gateway_router import GatewayProvider
from app.llm.types import ChatMessage, ChatResult, ChatStreamChunk, TokenUsage
from app.main import app
from app.services.gateway_service import GatewayClientError
from app.services.project_key_service import create_api_key
from app.core.config import settings


class _StubProvider(LLMProvider):
    """In-memory provider for endpoint tests — no SDK dependency."""

    def __init__(
        self,
        *,
        result: ChatResult | None = None,
        raises: BaseException | None = None,
        stream_chunks: list[ChatStreamChunk] | None = None,
        stream_raises: BaseException | None = None,
    ) -> None:
        self._result = result
        self._raises = raises
        self._stream_chunks = stream_chunks or []
        self._stream_raises = stream_raises
        self.calls: list[dict] = []
        self.stream_calls: list[dict] = []

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        self.calls.append({"model": model, "messages": list(messages)})
        if self._raises is not None:
            raise self._raises
        assert self._result is not None
        return self._result

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        self.stream_calls.append({"model": model, "messages": list(messages)})
        for chunk in self._stream_chunks:
            yield chunk
        if self._stream_raises is not None:
            raise self._stream_raises

    async def aclose(self) -> None:
        pass


class _SlowProvider(LLMProvider):
    def __init__(self, *, sleep_seconds: float) -> None:
        self.sleep_seconds = sleep_seconds

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        await asyncio.sleep(self.sleep_seconds)
        return ChatResult(
            content="too late",
            model=model,
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        yield ChatStreamChunk(provider="openai", model=model, role_delta="assistant")
        await asyncio.sleep(self.sleep_seconds)
        yield ChatStreamChunk(provider="openai", model=model, content_delta="never")

    async def aclose(self) -> None:
        pass


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_sessionmaker(db_engine):
    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded(db_sessionmaker):
    """Create a project + API key. Returns (plaintext_key, project, api_key)."""
    async with db_sessionmaker() as session:
        project = models.Project(name="test")
        session.add(project)
        await session.flush()
        issued = await create_api_key(session, project=project, label="t")
        await session.commit()
        return issued.plaintext, project, issued.api_key


@pytest_asyncio.fixture
async def client(db_sessionmaker):
    async def override_session():
        # Auth dep: read-only session with auto-commit on success.
        async with db_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def override_sessionmaker():
        # Gateway service: owns its own short-lived sessions.
        return db_sessionmaker

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_db_sessionmaker] = override_sessionmaker
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


def _set_provider(provider: LLMProvider) -> None:
    async def override():
        yield provider

    app.dependency_overrides[get_provider] = override


# ── Auth ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_completions_missing_token_returns_401(client) -> None:
    response = await client.post(
        "/v1/chat/completions",
        json={
            "model": "conexus-fast",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_completions_stream_missing_token_returns_401(client) -> None:
    response = await client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_completions_invalid_token_returns_401(client) -> None:
    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer cx_live_deadbeef_00000000000000000000000000000000"},
        json={
            "model": "conexus-fast",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_completions_revoked_token_returns_401(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, _project, api_key = seeded
    from datetime import datetime, timezone

    async with db_sessionmaker() as session:
        row = await session.get(models.ProjectApiKey, api_key.id)
        row.revoked_at = datetime.now(timezone.utc)
        await session.commit()

    response = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {plaintext}"},
        json={
            "model": "conexus-fast",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert response.status_code == 401


# ── Happy path ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_completions_happy_path(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, api_key = seeded
    _set_provider(
        _StubProvider(
            result=ChatResult(
                content="hello back",
                model="gpt-4o-mini",
                provider="openai",
                usage=TokenUsage(input_tokens=11, output_tokens=4),
            )
        )
    )
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "be brief"},
                    {"role": "user", "content": "hi"},
                ],
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "gpt-4o-mini"
    assert body["provider"] == "openai"
    assert body["fallback_used"] is False
    assert body["choices"][0]["message"] == {
        "role": "assistant",
        "content": "hello back",
    }
    assert body["usage"] == {
        "prompt_tokens": 11,
        "completion_tokens": 4,
        "total_tokens": 15,
    }
    request_id = body["id"].removeprefix("chatcmpl-")
    assert request_id
    # Success response advertises the request id so callers can correlate logs.
    assert response.headers[REQUEST_ID_HEADER] == request_id

    # Request log row written.
    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "completed"
        assert log.project_id == project.id
        assert log.api_key_id == api_key.id
        assert log.requested_model == "gpt-4o-mini"
        assert log.provider == "openai"
        assert log.model == "gpt-4o-mini"
        assert log.prompt_tokens == 11
        assert log.completion_tokens == 4
        assert log.total_tokens == 15
        assert log.estimated_cost is not None and log.estimated_cost > 0
        assert log.latency_ms is not None and log.latency_ms >= 0
        assert log.fallback_used is False
        assert log.completed_at is not None


@pytest.mark.asyncio
async def test_chat_completions_accepts_common_openai_fields_stream_false(
    client, seeded
) -> None:
    plaintext, _project, _api_key = seeded
    stub = _StubProvider(
        result=ChatResult(
            content="ok",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "top_p": 0.9,
                "stop": ["\n\n"],
                "user": "user-123",
                "seed": 123,
                "presence_penalty": 0.1,
                "frequency_penalty": 0.2,
                "response_format": {"type": "text"},
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 200
    assert len(stub.calls) == 1


@pytest.mark.asyncio
async def test_chat_completions_rejects_n_gt_1_with_400(client, seeded) -> None:
    plaintext, _project, _api_key = seeded
    stub = _StubProvider(
        result=ChatResult(
            content="should not happen",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "n": 2,
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 400
    assert stub.calls == []
    assert REQUEST_ID_HEADER in response.headers
    body = response.json()
    assert body["detail"]["code"] == "n_not_supported"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"tools": [{"type": "function", "function": {"name": "x"}}]},
        {"tool_choice": "auto"},
        {"tool_choice": {"type": "function", "function": {"name": "x"}}},
    ],
)
async def test_chat_completions_rejects_tool_calls_with_400(
    client, seeded, payload
) -> None:
    plaintext, _project, _api_key = seeded
    stub = _StubProvider(
        result=ChatResult(
            content="should not happen",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                **payload,
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 400
    assert stub.calls == []
    body = response.json()
    assert body["detail"]["code"] == "tool_calls_not_supported"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"logprobs": True},
        {"top_logprobs": 3},
        {"logprobs": False, "top_logprobs": 3},
    ],
)
async def test_chat_completions_rejects_logprobs_with_400(
    client, seeded, payload
) -> None:
    plaintext, _project, _api_key = seeded
    stub = _StubProvider(
        result=ChatResult(
            content="should not happen",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                **payload,
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 400
    assert stub.calls == []
    body = response.json()
    assert body["detail"]["code"] == "logprobs_not_supported"


@pytest.mark.asyncio
async def test_chat_completions_rejects_unsupported_response_format_with_400(
    client, seeded
) -> None:
    plaintext, _project, _api_key = seeded
    stub = _StubProvider(
        result=ChatResult(
            content="should not happen",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "response_format": {"type": "json_object"},
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 400
    assert stub.calls == []
    body = response.json()
    assert body["detail"]["code"] == "response_format_not_supported"


@pytest.mark.asyncio
async def test_chat_completions_stream_true_returns_sse_and_logs_success(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, api_key = seeded
    stub = _StubProvider(
        stream_chunks=[
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", role_delta="assistant"),
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", content_delta="hel"),
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", content_delta="lo"),
            ChatStreamChunk(
                provider="openai",
                model="gpt-4o-mini",
                finish_reason="stop",
                usage=TokenUsage(input_tokens=3, output_tokens=2),
            ),
        ]
    )
    _set_provider(stub)
    try:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert REQUEST_ID_HEADER in response.headers
            request_id = response.headers[REQUEST_ID_HEADER]
            payload = (await response.aread()).decode("utf-8")
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert "chat.completion.chunk" in payload
    assert "data: [DONE]" in payload
    assert stub.stream_calls

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "completed"
        assert log.project_id == project.id
        assert log.api_key_id == api_key.id
        assert log.requested_model == "gpt-4o-mini"
        assert log.provider == "openai"
        assert log.model == "gpt-4o-mini"
        assert log.prompt_tokens == 3
        assert log.completion_tokens == 2
        assert log.total_tokens == 5
        assert log.completed_at is not None


@pytest.mark.asyncio
async def test_chat_completions_stream_true_concrete_anthropic_model_returns_sse_and_logs_provider_model(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, api_key = seeded
    gateway = GatewayProvider(
        primary=_StubProvider(
            stream_chunks=[
                ChatStreamChunk(provider="anthropic", model="claude-sonnet-4-20250514", role_delta="assistant"),
                ChatStreamChunk(provider="anthropic", model="claude-sonnet-4-20250514", content_delta="hel"),
                ChatStreamChunk(provider="anthropic", model="claude-sonnet-4-20250514", content_delta="lo"),
                ChatStreamChunk(
                    provider="anthropic",
                    model="claude-sonnet-4-20250514",
                    finish_reason="stop",
                    usage=TokenUsage(input_tokens=3, output_tokens=2),
                ),
            ]
        ),
        fallback=_StubProvider(),
    )
    _set_provider(gateway)
    try:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "claude-sonnet-4-20250514",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        ) as response:
            assert response.status_code == 200
            request_id = response.headers[REQUEST_ID_HEADER]
            payload = (await response.aread()).decode("utf-8")
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert "chat.completion.chunk" in payload
    assert "data: [DONE]" in payload

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "completed"
        assert log.project_id == project.id
        assert log.api_key_id == api_key.id
        assert log.requested_model == "claude-sonnet-4-20250514"
        assert log.provider == "anthropic"
        assert log.model == "claude-sonnet-4-20250514"
        assert log.prompt_tokens == 3
        assert log.completion_tokens == 2
        assert log.total_tokens == 5


@pytest.mark.asyncio
async def test_chat_completions_stream_true_alias_stream_logs_anthropic_provider_model(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, api_key = seeded
    primary = _StubProvider(
        stream_chunks=[
            ChatStreamChunk(provider="anthropic", model="claude-haiku-4-5-20251001", role_delta="assistant"),
            ChatStreamChunk(provider="anthropic", model="claude-haiku-4-5-20251001", content_delta="hello"),
            ChatStreamChunk(
                provider="anthropic",
                model="claude-haiku-4-5-20251001",
                finish_reason="stop",
                usage=TokenUsage(input_tokens=2, output_tokens=1),
            ),
        ]
    )
    fallback = _StubProvider(
        stream_chunks=[
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", content_delta="should-not-happen"),
        ]
    )
    gateway = GatewayProvider(primary=primary, fallback=fallback)
    _set_provider(gateway)
    try:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "conexus-fast",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        ) as response:
            assert response.status_code == 200
            request_id = response.headers[REQUEST_ID_HEADER]
            payload = (await response.aread()).decode("utf-8")
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert "chat.completion.chunk" in payload
    assert "hello" in payload
    assert "data: [DONE]" in payload
    assert primary.stream_calls and primary.stream_calls[0]["model"] == "claude-haiku-4-5-20251001"
    assert fallback.stream_calls == []

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "completed"
        assert log.project_id == project.id
        assert log.api_key_id == api_key.id
        assert log.requested_model == "conexus-fast"
        assert log.provider == "anthropic"
        assert log.model == "claude-haiku-4-5-20251001"


@pytest.mark.asyncio
async def test_chat_completions_stream_true_logs_failure_on_mid_stream_error(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, api_key = seeded
    stub = _StubProvider(
        stream_chunks=[
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", role_delta="assistant"),
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", content_delta="hello"),
        ],
        stream_raises=RuntimeError("boom"),
    )
    _set_provider(stub)
    try:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        ) as response:
            assert response.status_code == 200
            request_id = response.headers[REQUEST_ID_HEADER]
            payload = (await response.aread()).decode("utf-8")
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert "data: [DONE]" in payload
    assert "\"error\"" in payload
    assert "Stream interrupted." in payload

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "failed"
        assert log.project_id == project.id
        assert log.api_key_id == api_key.id
        assert log.requested_model == "gpt-4o-mini"
        assert log.completed_at is not None


@pytest.mark.asyncio
async def test_stream_failure_after_partial_output_emits_safe_sse_error_and_logs_failed(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, api_key = seeded
    stub = _StubProvider(
        stream_chunks=[
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", role_delta="assistant"),
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", content_delta="hello"),
        ],
        stream_raises=ProviderError("upstream broke", provider="openai"),
    )
    _set_provider(stub)
    try:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        ) as response:
            assert response.status_code == 200
            request_id = response.headers[REQUEST_ID_HEADER]
            payload = (await response.aread()).decode("utf-8")
    finally:
        app.dependency_overrides.pop(get_provider, None)

    # Partial output is delivered.
    assert "hello" in payload
    # A safe error object is delivered (not the raw provider exception).
    assert "\"error\"" in payload
    assert "Stream interrupted." in payload
    assert "data: [DONE]" in payload

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "failed"
        assert log.project_id == project.id
        assert log.api_key_id == api_key.id
        assert log.requested_model == "gpt-4o-mini"
        # Failure finish must win: success fields must not be stamped.
        assert log.provider is None
        assert log.model is None
        assert log.error_code == "ProviderError"
        assert log.error_message == "upstream broke"
        assert log.completed_at is not None


# ── Limit enforcement (M8A) ────────────────────────────────────────────


async def _set_project_limits(
    db_sessionmaker,
    *,
    project_id: str,
    limit_mode: str,
    monthly_cost_limit: float | None = None,
    daily_request_limit: int | None = None,
    daily_token_limit: int | None = None,
) -> None:
    async with db_sessionmaker() as session:
        row = models.ProjectLimit(
            project_id=project_id,
            limit_mode=limit_mode,
            monthly_cost_limit=monthly_cost_limit,
            daily_request_limit=daily_request_limit,
            daily_token_limit=daily_token_limit,
        )
        session.add(row)
        await session.commit()


async def _seed_request(
    db_sessionmaker,
    *,
    project_id: str,
    created_at: datetime,
    total_tokens: int | None = None,
    estimated_cost: float | None = None,
) -> None:
    async with db_sessionmaker() as session:
        row = models.GatewayRequest(
            request_id=f"seed-{uuid.uuid4().hex}",
            project_id=project_id,
            api_key_id=None,
            requested_model="seed",
            status="failed",
            created_at=created_at,
            completed_at=created_at,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            latency_ms=0,
            error_code="seed",
            error_message="seed",
        )
        session.add(row)
        await session.commit()


@pytest.mark.asyncio
async def test_hard_daily_request_limit_blocks_before_provider_call(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, _api_key = seeded
    await _set_project_limits(
        db_sessionmaker,
        project_id=project.id,
        limit_mode="hard",
        daily_request_limit=1,
    )
    now = datetime.now(timezone.utc)
    await _seed_request(db_sessionmaker, project_id=project.id, created_at=now)

    stub = _StubProvider(
        result=ChatResult(
            content="should not happen",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 429
    assert stub.calls == []
    body = response.json()
    assert body["detail"]["code"] == "daily_request_limit_exceeded"
    assert body["detail"]["limit_type"] == "daily_request_limit"
    assert body["detail"]["current_value"] == 1.0
    assert body["detail"]["limit_value"] == 1.0
    assert body["detail"]["window"] == "utc_day"
    assert body["detail"]["reset_at"]
    request_id = body["detail"]["request_id"]
    assert response.headers[REQUEST_ID_HEADER] == request_id

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(models.GatewayRequest.request_id == request_id)
            )
        ).scalar_one()
        assert log.status == "failed"
        assert log.error_code == "daily_request_limit_exceeded"
        assert log.provider is None
        assert log.model is None


@pytest.mark.asyncio
async def test_hard_daily_request_limit_blocks_streaming_before_provider_call(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, _api_key = seeded
    await _set_project_limits(
        db_sessionmaker,
        project_id=project.id,
        limit_mode="hard",
        daily_request_limit=1,
    )
    now = datetime.now(timezone.utc)
    await _seed_request(db_sessionmaker, project_id=project.id, created_at=now)

    stub = _StubProvider(
        stream_chunks=[
            ChatStreamChunk(provider="openai", model="gpt-4o-mini", content_delta="nope")
        ]
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 429
    assert stub.stream_calls == []


class _DelayedStubProvider(_StubProvider):
    """Widen the race window so preflight runs for many requests before any log row commits."""

    def __init__(self, *, delay_s: float = 0.08, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._delay_s = delay_s

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> ChatResult:
        await asyncio.sleep(self._delay_s)
        return await super().chat(
            messages, model=model, max_tokens=max_tokens, temperature=temperature
        )


@pytest.mark.asyncio
async def test_hard_daily_request_limit_under_concurrent_burst(
    client, seeded, db_sessionmaker
) -> None:
    """With daily_request_limit=1, at most one request should succeed per strict admission.

    PostgreSQL (CI with a real DB URL) must allow exactly one 200. SQLite ``:memory:``
    pools may isolate connections; we still require at least one 429 and no 5xx.
    See docs/strict-limit-reservations.md.
    """
    plaintext, project, _api_key = seeded
    await _set_project_limits(
        db_sessionmaker,
        project_id=project.id,
        limit_mode="hard",
        daily_request_limit=1,
    )
    stub = _DelayedStubProvider(
        result=ChatResult(
            content="ok",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    n = 5
    try:

        async def one() -> int:
            r = await client.post(
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {plaintext}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            return r.status_code

        codes = await asyncio.gather(*[one() for _ in range(n)])
    finally:
        app.dependency_overrides.pop(get_provider, None)

    oks = sum(1 for c in codes if c == 200)
    rate429 = sum(1 for c in codes if c == 429)
    assert all(c in (200, 429) for c in codes)
    assert oks + rate429 == n
    assert oks == 1
    assert rate429 == n - 1
    assert len(stub.calls) == oks


@pytest.mark.asyncio
async def test_hard_daily_token_limit_blocks_before_provider_call(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, _api_key = seeded
    await _set_project_limits(
        db_sessionmaker,
        project_id=project.id,
        limit_mode="hard",
        daily_token_limit=10,
    )
    now = datetime.now(timezone.utc)
    await _seed_request(
        db_sessionmaker,
        project_id=project.id,
        created_at=now,
        total_tokens=15,
    )

    stub = _StubProvider(
        result=ChatResult(
            content="should not happen",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 429
    assert stub.calls == []
    body = response.json()
    assert body["detail"]["code"] == "daily_token_limit_exceeded"
    assert body["detail"]["limit_type"] == "daily_token_limit"
    assert body["detail"]["current_value"] == 15.0
    assert body["detail"]["limit_value"] == 10.0
    assert body["detail"]["window"] == "utc_day"
    assert body["detail"]["reset_at"]


@pytest.mark.asyncio
async def test_hard_monthly_cost_limit_blocks_before_provider_call(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, project, _api_key = seeded
    await _set_project_limits(
        db_sessionmaker,
        project_id=project.id,
        limit_mode="hard",
        monthly_cost_limit=1.0,
    )
    now = datetime.now(timezone.utc)
    await _seed_request(
        db_sessionmaker,
        project_id=project.id,
        created_at=now,
        estimated_cost=1.5,
    )

    stub = _StubProvider(
        result=ChatResult(
            content="should not happen",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 429
    assert stub.calls == []
    body = response.json()
    assert body["detail"]["code"] == "monthly_cost_limit_exceeded"
    assert body["detail"]["limit_type"] == "monthly_cost_limit"
    assert body["detail"]["current_value"] == 1.5
    assert body["detail"]["limit_value"] == 1.0
    assert body["detail"]["window"] == "utc_month"
    assert body["detail"]["reset_at"]


@pytest.mark.asyncio
async def test_disabled_limits_allow_provider_call(client, seeded, db_sessionmaker) -> None:
    plaintext, project, _api_key = seeded
    await _set_project_limits(
        db_sessionmaker,
        project_id=project.id,
        limit_mode="disabled",
        daily_request_limit=0,
        daily_token_limit=0,
        monthly_cost_limit=0.0,
    )
    stub = _StubProvider(
        result=ChatResult(
            content="ok",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)
    assert response.status_code == 200
    assert len(stub.calls) == 1


@pytest.mark.asyncio
async def test_soft_limits_allow_provider_call(client, seeded, db_sessionmaker) -> None:
    plaintext, project, _api_key = seeded
    await _set_project_limits(
        db_sessionmaker,
        project_id=project.id,
        limit_mode="soft",
        daily_request_limit=0,
        daily_token_limit=0,
        monthly_cost_limit=0.0,
    )
    stub = _StubProvider(
        result=ChatResult(
            content="ok",
            model="gpt-4o-mini",
            provider="openai",
            usage=TokenUsage(input_tokens=1, output_tokens=1),
        )
    )
    _set_provider(stub)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)
    assert response.status_code == 200
    assert len(stub.calls) == 1

# ── Error path ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_completions_gateway_client_error_returns_400_with_request_id(
    client, seeded, monkeypatch
) -> None:
    plaintext, _project, _api_key = seeded
    _set_provider(
        _StubProvider(
            result=ChatResult(
                content="should not happen",
                model="gpt-4o-mini",
                provider="openai",
                usage=TokenUsage(input_tokens=1, output_tokens=1),
            )
        )
    )

    request_id = "req_test_gateway_client_error"

    async def _raise(*args, **kwargs):
        raise GatewayClientError(
            "bad input",
            code="bad_input",
            request_id=request_id,
        )

    monkeypatch.setattr("app.api.gateway.run_chat_completion", _raise)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 400
    assert response.headers[REQUEST_ID_HEADER] == request_id
    body = response.json()
    assert body["detail"]["code"] == "bad_input"
    assert body["detail"]["message"] == "bad input"
    assert body["detail"]["request_id"] == request_id


@pytest.mark.asyncio
async def test_chat_completions_stream_gateway_client_error_returns_400_with_request_id(
    client, seeded, monkeypatch
) -> None:
    plaintext, _project, _api_key = seeded
    _set_provider(
        _StubProvider(
            stream_chunks=[
                ChatStreamChunk(provider="openai", model="gpt-4o-mini", content_delta="nope")
            ]
        )
    )

    request_id = "req_test_gateway_client_error_stream"

    async def _raise(*args, **kwargs):
        raise GatewayClientError(
            "bad input",
            code="bad_input",
            request_id=request_id,
        )

    monkeypatch.setattr("app.api.gateway.run_chat_completion_stream", _raise)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 400
    assert response.headers[REQUEST_ID_HEADER] == request_id
    body = response.json()
    assert body["detail"]["code"] == "bad_input"
    assert body["detail"]["message"] == "bad input"
    assert body["detail"]["request_id"] == request_id


@pytest.mark.asyncio
async def test_chat_completions_provider_failure_logs_failure(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, _project, _api_key = seeded
    _set_provider(
        _StubProvider(
            raises=AllProvidersFailedError("everyone is down"),
        )
    )
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "conexus-fast",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 502
    body = response.json()
    assert body["detail"]["code"] == "all_providers_failed"
    request_id = body["detail"]["request_id"]
    assert request_id
    assert response.headers[REQUEST_ID_HEADER] == request_id

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "failed"
        assert log.error_code == "all_providers_failed"
        assert log.error_message == "everyone is down"
        assert log.completed_at is not None
        assert log.latency_ms is not None


@pytest.mark.asyncio
async def test_chat_completions_unknown_model_returns_400(
    client, seeded
) -> None:
    plaintext, _project, _api_key = seeded
    _set_provider(
        _StubProvider(
            raises=UnknownModelError("gp-4o", known_aliases=["conexus-fast"]),
        )
    )
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gp-4o",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "unknown_model"
    request_id = body["detail"]["request_id"]
    assert request_id
    assert response.headers[REQUEST_ID_HEADER] == request_id


@pytest.mark.asyncio
async def test_chat_completions_provider_rate_limit_logs_failure(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, _project, _api_key = seeded
    _set_provider(
        _StubProvider(
            raises=ProviderRateLimitError("429", provider="openai"),
        )
    )
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "conexus-fast",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 502
    body = response.json()
    request_id = body["detail"]["request_id"]
    assert response.headers[REQUEST_ID_HEADER] == request_id
    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "failed"
        assert log.error_code == "ProviderRateLimitError"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [
        ProviderRateLimitError("429", provider="openai"),
        ProviderUnavailableError("503", provider="openai"),
    ],
)
async def test_chat_completions_direct_openai_model_failure_is_logged(
    client, seeded, db_sessionmaker, exc
) -> None:
    """Concrete OpenAI model should still map provider failure to 502 + DB log.

    This specifically exercises the gateway's OpenAI-only routing path while
    still verifying structured upstream error responses and durable request
    logging.
    """
    plaintext, _project, _api_key = seeded

    openai_stub = _StubProvider(raises=exc)
    gateway = GatewayProvider(primary=None, fallback=openai_stub)
    _set_provider(gateway)
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 502
    assert REQUEST_ID_HEADER in response.headers
    body = response.json()
    assert body["detail"]["code"] == type(exc).__name__
    assert body["detail"]["message"]
    request_id = body["detail"]["request_id"]
    assert request_id
    assert response.headers[REQUEST_ID_HEADER] == request_id

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(
                    models.GatewayRequest.request_id == request_id
                )
            )
        ).scalar_one()
        assert log.status == "failed"
        assert log.error_code == type(exc).__name__
        assert log.requested_model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_chat_completions_times_out_and_returns_502(client, seeded, db_sessionmaker) -> None:
    plaintext, _project, _api_key = seeded
    original = settings.llm_request_timeout_seconds
    settings.llm_request_timeout_seconds = 1
    _set_provider(_SlowProvider(sleep_seconds=2.0))
    try:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
        )
    finally:
        settings.llm_request_timeout_seconds = original
        app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 502
    body = response.json()
    assert body["detail"]["code"] == "ProviderUnavailableError"
    request_id = body["detail"]["request_id"]
    assert request_id

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(models.GatewayRequest.request_id == request_id)
            )
        ).scalar_one()
        assert log.status == "failed"
        assert log.error_code == "ProviderUnavailableError"


@pytest.mark.asyncio
async def test_chat_completions_stream_times_out_emits_sse_error_and_done(
    client, seeded, db_sessionmaker
) -> None:
    plaintext, _project, _api_key = seeded
    original = settings.llm_stream_timeout_seconds
    settings.llm_stream_timeout_seconds = 1
    _set_provider(_SlowProvider(sleep_seconds=2.0))
    try:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {plaintext}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}], "stream": True},
        ) as response:
            assert response.status_code == 200
            request_id = response.headers[REQUEST_ID_HEADER]
            payload = (await response.aread()).decode("utf-8")
    finally:
        settings.llm_stream_timeout_seconds = original
        app.dependency_overrides.pop(get_provider, None)

    assert "\"error\"" in payload
    assert "data: [DONE]" in payload

    async with db_sessionmaker() as session:
        log = (
            await session.execute(
                select(models.GatewayRequest).where(models.GatewayRequest.request_id == request_id)
            )
        ).scalar_one()
        assert log.status == "failed"
        assert log.error_code == "ProviderUnavailableError"
