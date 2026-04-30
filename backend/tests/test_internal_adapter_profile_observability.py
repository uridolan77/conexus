"""Tests for internal adapter profile observability endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db import models
from app.db.session import get_session
from app.main import app


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
async def client(db_sessionmaker):
    async def override_session():
        async with db_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_observability_requires_internal_api_key(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    response = await client.get("/internal/adapter-profiles/gw-1/observability")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_observability_unknown_profile_returns_404(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    response = await client.get(
        "/internal/adapter-profiles/gw-missing/observability",
        headers={"X-Internal-Api-Key": "secret"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_observability_returns_request_count_error_rate_latency_p95_and_cost(
    client: AsyncClient, db_sessionmaker
) -> None:
    settings.internal_adapter_api_key = "secret"
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=1)

    async with db_sessionmaker() as session:
        session.add(
            models.GatewayAdapterProfile(
                gateway_profile_id="gw-1",
                adapter_profile_id="ap-1",
                domain_key="gaming-crm",
                status="Registered",
            )
        )
        session.add_all(
            [
                models.GatewayRequest(
                    request_id="r1",
                    project_id=None,
                    api_key_id=None,
                    requested_model="m",
                    status="completed",
                    latency_ms=100,
                    estimated_cost=1.0,
                    gateway_profile_id="gw-1",
                    created_at=now - timedelta(minutes=30),
                    completed_at=now - timedelta(minutes=30),
                ),
                models.GatewayRequest(
                    request_id="r2",
                    project_id=None,
                    api_key_id=None,
                    requested_model="m",
                    status="completed",
                    latency_ms=200,
                    estimated_cost=3.0,
                    gateway_profile_id="gw-1",
                    created_at=now - timedelta(minutes=20),
                    completed_at=now - timedelta(minutes=20),
                ),
                models.GatewayRequest(
                    request_id="r3",
                    project_id=None,
                    api_key_id=None,
                    requested_model="m",
                    status="failed",
                    latency_ms=50,
                    estimated_cost=None,
                    gateway_profile_id="gw-1",
                    created_at=now - timedelta(minutes=10),
                    completed_at=None,
                    error_code="x",
                    error_message="y",
                ),
            ]
        )
        await session.commit()

    response = await client.get(
        "/internal/adapter-profiles/gw-1/observability",
        headers={"X-Internal-Api-Key": "secret"},
        params={"since": window_start.isoformat(), "until": now.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gatewayProfileId"] == "gw-1"
    assert body["requestCount"] == 3
    assert body["errorRate"] == pytest.approx(1 / 3)
    assert body["latencyP95Ms"] == 200
    assert body["costPerAnswer"] == pytest.approx(2.0)
    assert body["citationFailureRate"] is None

