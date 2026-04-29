"""End-to-end tests for POST /v1/chat/completions (M2)."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.gateway import REQUEST_ID_HEADER
from app.db import models
from app.db.session import get_db_sessionmaker, get_session
from app.llm.base import LLMProvider
from app.llm.dependencies import get_provider
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    UnknownModelError,
)
from app.llm.gateway_router import GatewayProvider
from app.llm.types import ChatMessage, ChatResult, TokenUsage
from app.main import app
from app.services.project_key_service import create_api_key


class _StubProvider(LLMProvider):
    """In-memory provider for endpoint tests — no SDK dependency."""

    def __init__(
        self,
        *,
        result: ChatResult | None = None,
        raises: BaseException | None = None,
    ) -> None:
        self._result = result
        self._raises = raises
        self.calls: list[dict] = []

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

    async def aclose(self) -> None:
        pass


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
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
