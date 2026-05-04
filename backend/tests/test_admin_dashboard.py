"""Tests for M6 dashboard summary endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models
from app.db.session import get_session
from app.main import app


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


async def _login(client: AsyncClient) -> None:
    response = await client.post(
        "/admin/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_summary_requires_admin_auth(client: AsyncClient) -> None:
    response = await client.get("/admin/dashboard/summary")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_summary_returns_today_metrics_and_latest_errors(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    now = datetime.now(timezone.utc)
    today = datetime(now.year, now.month, now.day, 10, 0, tzinfo=timezone.utc)
    old = today - timedelta(days=2)
    async with db_sessionmaker() as session:
        project = models.Project(id="projecta", name="Project A", created_at=today)
        session.add(project)
        session.add_all(
            [
                models.GatewayRequest(
                    request_id="dash_completed",
                    project_id=project.id,
                    requested_model="conexus-fast",
                    provider="openai",
                    model="gpt-4o-mini",
                    status="completed",
                    latency_ms=100,
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                    estimated_cost=0.01,
                    fallback_used=False,
                    created_at=today,
                    completed_at=today + timedelta(milliseconds=100),
                ),
                models.GatewayRequest(
                    request_id="dash_failed",
                    project_id=project.id,
                    requested_model="conexus-fast",
                    provider="anthropic",
                    model="claude-sonnet-4-20250514",
                    status="failed",
                    latency_ms=200,
                    estimated_cost=None,
                    fallback_used=True,
                    error_code="provider_timeout",
                    error_message="provider timed out",
                    created_at=today + timedelta(minutes=5),
                    completed_at=today + timedelta(minutes=5, milliseconds=200),
                ),
                models.GatewayRequest(
                    request_id="dash_old",
                    project_id=project.id,
                    requested_model="conexus-fast",
                    provider="openai",
                    model="gpt-4o-mini",
                    status="completed",
                    latency_ms=900,
                    estimated_cost=9.0,
                    fallback_used=False,
                    created_at=old,
                    completed_at=old + timedelta(milliseconds=900),
                ),
            ]
        )
        await session.commit()

    await _login(client)
    response = await client.get("/admin/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["requests_today"] == 2
    assert body["success_rate"] == pytest.approx(0.5)
    assert body["failed_requests"] == 1
    assert body["average_latency_ms"] == pytest.approx(150)
    assert body["estimated_cost_today"] == pytest.approx(0.01)
    assert body["latest_errors"][0]["request_id"] == "dash_failed"
    assert body["latest_errors"][0]["project_name"] == "Project A"
    assert body["latest_errors"][0]["error_code"] == "provider_timeout"
