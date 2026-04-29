"""Tests for admin usage analytics APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

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


async def _seed_usage_requests(db_sessionmaker) -> dict[str, Any]:
    created = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
    async with db_sessionmaker() as session:
        project_a = models.Project(id="projecta", name="Project A", created_at=created)
        project_b = models.Project(id="projectb", name="Project B", created_at=created)
        session.add_all([project_a, project_b])
        session.add_all(
            [
                models.GatewayRequest(
                    id="usage_req_1",
                    request_id="usage_completed",
                    project_id=project_a.id,
                    requested_model="conexus-default",
                    provider="openai",
                    model="gpt-4o-mini",
                    status="completed",
                    latency_ms=100,
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30,
                    estimated_cost=0.01,
                    fallback_used=False,
                    created_at=created,
                    completed_at=created + timedelta(milliseconds=100),
                ),
                models.GatewayRequest(
                    id="usage_req_2",
                    request_id="usage_failed",
                    project_id=project_a.id,
                    requested_model="conexus-default",
                    provider="anthropic",
                    model="claude-sonnet-4-20250514",
                    status="failed",
                    latency_ms=200,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    estimated_cost=None,
                    fallback_used=True,
                    error_code="provider_timeout",
                    error_message="provider timed out",
                    created_at=created + timedelta(hours=1),
                    completed_at=created + timedelta(hours=1, milliseconds=200),
                ),
                models.GatewayRequest(
                    id="usage_req_3",
                    request_id="usage_started",
                    project_id=project_b.id,
                    requested_model="gpt-4o-mini",
                    provider=None,
                    model=None,
                    status="started",
                    latency_ms=None,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    estimated_cost=None,
                    fallback_used=False,
                    created_at=created + timedelta(hours=2),
                    completed_at=None,
                ),
                models.GatewayRequest(
                    id="usage_req_old",
                    request_id="usage_old",
                    project_id=project_b.id,
                    requested_model="gpt-4o-mini",
                    provider="openai",
                    model="gpt-4o-mini",
                    status="completed",
                    latency_ms=500,
                    prompt_tokens=1_000,
                    completion_tokens=1_000,
                    total_tokens=2_000,
                    estimated_cost=99.0,
                    fallback_used=False,
                    created_at=created - timedelta(days=10),
                    completed_at=created - timedelta(days=10, seconds=-1),
                ),
            ]
        )
        await session.commit()
    return {
        "project_a": project_a.id,
        "project_b": project_b.id,
        "created": created,
    }


@pytest.mark.asyncio
async def test_usage_routes_require_admin_auth(client: AsyncClient) -> None:
    summary_response = await client.get("/admin/usage/summary")
    by_project_response = await client.get("/admin/usage/by-project")
    by_provider_response = await client.get("/admin/usage/by-provider")
    timeseries_response = await client.get("/admin/usage/timeseries")

    assert summary_response.status_code == 401
    assert by_project_response.status_code == 401
    assert by_provider_response.status_code == 401
    assert timeseries_response.status_code == 401


@pytest.mark.asyncio
async def test_usage_summary_aggregates_request_metadata(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    seed = await _seed_usage_requests(db_sessionmaker)
    created = seed["created"]
    await _login(client)

    response = await client.get(
        "/admin/usage/summary",
        params={
            "created_from": (created - timedelta(minutes=1)).isoformat(),
            "created_to": (created + timedelta(hours=3)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 3
    assert body["completed_requests"] == 1
    assert body["failed_requests"] == 1
    assert body["success_rate"] == pytest.approx(1 / 3)
    assert body["fallback_count"] == 1
    assert body["fallback_rate"] == pytest.approx(1 / 3)
    assert body["total_prompt_tokens"] == 10
    assert body["total_completion_tokens"] == 20
    assert body["total_tokens"] == 30
    assert body["estimated_cost"] == pytest.approx(0.01)
    assert body["avg_latency_ms"] == pytest.approx(150)
    assert body["currency"] == "USD"


@pytest.mark.asyncio
async def test_usage_by_project_groups_metadata(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    seed = await _seed_usage_requests(db_sessionmaker)
    created = seed["created"]
    await _login(client)

    response = await client.get(
        "/admin/usage/by-project",
        params={
            "created_from": (created - timedelta(minutes=1)).isoformat(),
            "created_to": (created + timedelta(hours=3)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    items = {item["project_id"]: item for item in body["items"]}
    assert set(items) == {seed["project_a"], seed["project_b"]}
    assert items[seed["project_a"]]["project_name"] == "Project A"
    assert items[seed["project_a"]]["total_requests"] == 2
    assert items[seed["project_a"]]["completed_requests"] == 1
    assert items[seed["project_a"]]["failed_requests"] == 1
    assert items[seed["project_a"]]["fallback_count"] == 1
    assert items[seed["project_a"]]["estimated_cost"] == pytest.approx(0.01)
    assert items[seed["project_b"]]["project_name"] == "Project B"
    assert items[seed["project_b"]]["total_requests"] == 1
    assert items[seed["project_b"]]["total_tokens"] == 0


@pytest.mark.asyncio
async def test_usage_by_provider_groups_metadata(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    seed = await _seed_usage_requests(db_sessionmaker)
    created = seed["created"]
    await _login(client)

    response = await client.get(
        "/admin/usage/by-provider",
        params={
            "created_from": (created - timedelta(minutes=1)).isoformat(),
            "created_to": (created + timedelta(hours=3)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    items = {item["provider"]: item for item in body["items"]}
    assert set(items) == {"openai", "anthropic", None}
    assert items["openai"]["total_requests"] == 1
    assert items["openai"]["completed_requests"] == 1
    assert items["openai"]["estimated_cost"] == pytest.approx(0.01)
    assert items["anthropic"]["total_requests"] == 1
    assert items["anthropic"]["failed_requests"] == 1
    assert items["anthropic"]["fallback_count"] == 1
    assert items[None]["total_requests"] == 1
    assert items[None]["total_tokens"] == 0


@pytest.mark.asyncio
async def test_usage_custom_dates_filter_requests(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    seed = await _seed_usage_requests(db_sessionmaker)
    created = seed["created"]
    await _login(client)

    response = await client.get(
        "/admin/usage/summary",
        params={
            "created_from": (created + timedelta(minutes=30)).isoformat(),
            "created_to": (created + timedelta(hours=1, minutes=30)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 1
    assert body["failed_requests"] == 1
    assert body["fallback_count"] == 1
    assert body["estimated_cost"] == 0


@pytest.mark.asyncio
async def test_usage_timeseries_returns_hourly_metadata_buckets(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    seed = await _seed_usage_requests(db_sessionmaker)
    created = seed["created"]
    await _login(client)

    response = await client.get(
        "/admin/usage/timeseries",
        params={
            "window": "24h",
            "created_from": created.isoformat(),
            "created_to": (created + timedelta(hours=3)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["interval"] == "hour"
    assert len(body["items"]) == 3
    assert [item["total_requests"] for item in body["items"]] == [1, 1, 1]
    assert body["items"][0]["completed_requests"] == 1
    assert body["items"][0]["total_tokens"] == 30
    assert body["items"][1]["failed_requests"] == 1
    assert body["items"][1]["fallback_count"] == 1
    assert body["items"][2]["avg_latency_ms"] is None


@pytest.mark.asyncio
async def test_usage_window_filter_uses_relative_time(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    now = datetime.now(timezone.utc)
    async with db_sessionmaker() as session:
        session.add_all(
            [
                models.GatewayRequest(
                    request_id="recent_usage",
                    requested_model="gpt-4o-mini",
                    status="completed",
                    total_tokens=10,
                    estimated_cost=0.01,
                    fallback_used=False,
                    created_at=now - timedelta(hours=2),
                    completed_at=now - timedelta(hours=2),
                ),
                models.GatewayRequest(
                    request_id="old_usage",
                    requested_model="gpt-4o-mini",
                    status="completed",
                    total_tokens=20,
                    estimated_cost=0.02,
                    fallback_used=False,
                    created_at=now - timedelta(days=2),
                    completed_at=now - timedelta(days=2),
                ),
            ]
        )
        await session.commit()
    await _login(client)

    response = await client.get("/admin/usage/summary", params={"window": "24h"})

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 1
    assert body["total_tokens"] == 10
    assert body["estimated_cost"] == pytest.approx(0.01)


@pytest.mark.asyncio
async def test_usage_rejects_inverted_custom_dates(
    client: AsyncClient,
) -> None:
    await _login(client)

    response = await client.get(
        "/admin/usage/summary",
        params={
            "created_from": "2026-04-30T00:00:00+00:00",
            "created_to": "2026-04-29T00:00:00+00:00",
        },
    )

    assert response.status_code == 400
