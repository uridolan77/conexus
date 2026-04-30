"""Tests for M8A admin project limits APIs."""

from __future__ import annotations

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
async def test_get_limits_unauthorized_returns_401(client: AsyncClient) -> None:
    response = await client.get("/admin/projects/p1/limits")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_default_disabled_limits_for_project_with_no_row(
    client: AsyncClient,
) -> None:
    await _login(client)
    created = await client.post("/admin/projects", json={"name": "p"})
    project_id = created.json()["id"]

    response = await client.get(f"/admin/projects/{project_id}/limits")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["limit_mode"] == "disabled"
    assert body["monthly_cost_limit"] is None
    assert body["daily_request_limit"] is None
    assert body["daily_token_limit"] is None


@pytest.mark.asyncio
async def test_put_creates_limits(client: AsyncClient) -> None:
    await _login(client)
    created = await client.post("/admin/projects", json={"name": "p"})
    project_id = created.json()["id"]

    response = await client.put(
        f"/admin/projects/{project_id}/limits",
        json={
            "limit_mode": "hard",
            "monthly_cost_limit": 10.0,
            "daily_request_limit": 100,
            "daily_token_limit": 5000,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["limit_mode"] == "hard"
    assert body["monthly_cost_limit"] == 10.0
    assert body["daily_request_limit"] == 100
    assert body["daily_token_limit"] == 5000


@pytest.mark.asyncio
async def test_put_updates_limits(client: AsyncClient) -> None:
    await _login(client)
    created = await client.post("/admin/projects", json={"name": "p"})
    project_id = created.json()["id"]

    first = await client.put(
        f"/admin/projects/{project_id}/limits",
        json={"limit_mode": "hard", "daily_request_limit": 10},
    )
    assert first.status_code == 200

    second = await client.put(
        f"/admin/projects/{project_id}/limits",
        json={"limit_mode": "disabled", "daily_request_limit": 0},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["limit_mode"] == "disabled"
    assert body["daily_request_limit"] == 0


@pytest.mark.asyncio
async def test_unknown_project_returns_404(client: AsyncClient) -> None:
    await _login(client)
    response = await client.get("/admin/projects/does-not-exist/limits")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_limits_usage_returns_daily_and_monthly_windows(
    client: AsyncClient,
) -> None:
    await _login(client)
    created = await client.post("/admin/projects", json={"name": "p"})
    project_id = created.json()["id"]

    response = await client.get(f"/admin/projects/{project_id}/limits/usage")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["daily"]["window"] == "utc_day"
    assert body["daily"]["request_count"] == 0
    assert body["daily"]["total_tokens"] == 0
    assert body["monthly"]["window"] == "utc_month"
    assert body["monthly"]["estimated_cost"] == 0.0
    assert body["monthly"]["currency"] == "USD"


@pytest.mark.asyncio
async def test_get_limits_reservations_null_when_no_usage_windows(
    client: AsyncClient,
) -> None:
    await _login(client)
    created = await client.post("/admin/projects", json={"name": "p"})
    project_id = created.json()["id"]

    response = await client.get(f"/admin/projects/{project_id}/limits/reservations")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["daily"] is None
    assert body["monthly"] is None


@pytest.mark.asyncio
async def test_get_stale_reservations_requires_admin(client: AsyncClient) -> None:
    response = await client.get("/admin/projects/limits/reservations/stale")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_stale_reservations_returns_shape(client: AsyncClient) -> None:
    await _login(client)
    response = await client.get("/admin/projects/limits/reservations/stale")
    assert response.status_code == 200
    body = response.json()
    assert "now" in body
    assert "older_than_seconds" in body
    assert "total_count" in body
    assert "oldest_age_seconds" in body
    assert "items" in body
    assert body["total_count"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_post_repair_dry_run_404_when_missing(client: AsyncClient) -> None:
    await _login(client)
    response = await client.post(
        "/admin/projects/limits/reservations/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/repair/dry-run"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_repair_apply_404_when_missing(client: AsyncClient) -> None:
    await _login(client)
    response = await client.post(
        "/admin/projects/limits/reservations/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/repair",
        json={"reason": "test"},
    )
    assert response.status_code == 404

