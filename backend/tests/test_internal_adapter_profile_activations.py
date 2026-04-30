"""Tests for internal adapter profile activation endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db import models
from app.db.models import GatewayAdapterProfileActivation
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


async def _register(client: AsyncClient, *, adapter_profile_id: str, domain_key: str) -> str:
    response = await client.post(
        "/internal/adapter-profiles/register",
        headers={"X-Internal-Api-Key": settings.internal_adapter_api_key or ""},
        json={"adapterProfileId": adapter_profile_id, "domainKey": domain_key},
    )
    assert response.status_code == 200
    return response.json()["gatewayProfileId"]


@pytest.mark.asyncio
async def test_activate_canary_creates_state(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    gw1 = await _register(client, adapter_profile_id="ap-1", domain_key="gaming-crm")

    response = await client.post(
        f"/internal/adapter-profiles/{gw1}/activate-canary",
        headers={"X-Internal-Api-Key": "secret"},
        json={"canaryPercent": 10},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Canary"
    assert response.json()["canaryPercent"] == 10


@pytest.mark.asyncio
async def test_second_canary_same_domain_conflicts(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    gw1 = await _register(client, adapter_profile_id="ap-1", domain_key="gaming-crm")
    gw2 = await _register(client, adapter_profile_id="ap-2", domain_key="gaming-crm")

    ok = await client.post(
        f"/internal/adapter-profiles/{gw1}/activate-canary",
        headers={"X-Internal-Api-Key": "secret"},
        json={"canaryPercent": 10},
    )
    assert ok.status_code == 200
    conflict = await client.post(
        f"/internal/adapter-profiles/{gw2}/activate-canary",
        headers={"X-Internal-Api-Key": "secret"},
        json={"canaryPercent": 10},
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_promote_makes_profile_active(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    gw1 = await _register(client, adapter_profile_id="ap-1", domain_key="gaming-crm")
    await client.post(
        f"/internal/adapter-profiles/{gw1}/activate-canary",
        headers={"X-Internal-Api-Key": "secret"},
        json={"canaryPercent": 10},
    )
    response = await client.post(
        f"/internal/adapter-profiles/{gw1}/promote",
        headers={"X-Internal-Api-Key": "secret"},
        json={},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Active"
    active = await client.get(
        "/internal/domains/gaming-crm/active-profile",
        headers={"X-Internal-Api-Key": "secret"},
    )
    assert active.status_code == 200
    assert active.json()["gatewayProfileId"] == gw1


@pytest.mark.asyncio
async def test_rollback_restores_previous_active(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    gw1 = await _register(client, adapter_profile_id="ap-1", domain_key="gaming-crm")
    gw2 = await _register(client, adapter_profile_id="ap-2", domain_key="gaming-crm")

    p1 = await client.post(
        f"/internal/adapter-profiles/{gw1}/promote",
        headers={"X-Internal-Api-Key": "secret"},
        json={},
    )
    assert p1.status_code == 200
    p2 = await client.post(
        f"/internal/adapter-profiles/{gw2}/promote",
        headers={"X-Internal-Api-Key": "secret"},
        json={},
    )
    assert p2.status_code == 200

    rb = await client.post(
        f"/internal/adapter-profiles/{gw2}/rollback",
        headers={"X-Internal-Api-Key": "secret"},
        json={},
    )
    assert rb.status_code == 200
    assert rb.json()["gatewayProfileId"] == gw1

    override = app.dependency_overrides[get_session]
    agen = override()
    try:
        session = await anext(agen)
        active = await session.scalar(
            select(GatewayAdapterProfileActivation).where(
                GatewayAdapterProfileActivation.domain_key == "gaming-crm",
                GatewayAdapterProfileActivation.status == "Active",
            )
        )
        assert active is not None
        assert active.gateway_profile_id == gw1
    finally:
        await agen.aclose()

