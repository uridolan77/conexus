"""Tests for internal adapter profile registry endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db import models
from app.db.models import GatewayAdapterProfile
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


@pytest.mark.asyncio
async def test_register_adapter_profile_requires_internal_api_key(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    response = await client.post(
        "/internal/adapter-profiles/register",
        json={"adapterProfileId": "ap-1", "domainKey": "gaming-crm"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_internal_api_key_not_configured_returns_503(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Registry is enabled but INTERNAL_ADAPTER_API_KEY is absent → safe 503 (not 401)."""
    monkeypatch.setattr(settings, "adapter_profile_registry_enabled", True)
    monkeypatch.setattr(settings, "internal_adapter_api_key", None)
    response = await client.post(
        "/internal/adapter-profiles/register",
        headers={"X-Internal-Api-Key": "any-value"},
        json={"adapterProfileId": "ap-x", "domainKey": "dk"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_adapter_profile_registry_disabled_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADAPTER_PROFILE_REGISTRY_ENABLED=false → every internal endpoint returns 404."""
    monkeypatch.setattr(settings, "adapter_profile_registry_enabled", False)
    monkeypatch.setattr(settings, "internal_adapter_api_key", "secret")
    response = await client.post(
        "/internal/adapter-profiles/register",
        headers={"X-Internal-Api-Key": "secret"},
        json={"adapterProfileId": "ap-x", "domainKey": "dk"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_register_adapter_profile_creates_gateway_profile(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    response = await client.post(
        "/internal/adapter-profiles/register",
        headers={"X-Internal-Api-Key": "secret"},
        json={
            "adapterProfileId": "ap-1",
            "domainKey": "gaming-crm",
            "runId": "run-1",
            "planId": "plan-1",
            "compositeScore": 0.87,
            "evidenceHash": "evh",
            "semanticContextHash": "sch",
            "slodModelVersion": "v1",
            "metadata": {"k": "v"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gatewayProfileId"].startswith("gw-")
    assert body["status"] == "Registered"

    override = app.dependency_overrides[get_session]
    agen = override()
    try:
        session = await anext(agen)
        row = await session.scalar(
            select(GatewayAdapterProfile).where(GatewayAdapterProfile.adapter_profile_id == "ap-1")
        )
        assert row is not None
        assert row.gateway_profile_id == body["gatewayProfileId"]
        assert row.domain_key == "gaming-crm"
    finally:
        await agen.aclose()


@pytest.mark.asyncio
async def test_register_adapter_profile_is_idempotent_by_adapterProfileId(client: AsyncClient) -> None:
    settings.internal_adapter_api_key = "secret"
    first = await client.post(
        "/internal/adapter-profiles/register",
        headers={"X-Internal-Api-Key": "secret"},
        json={"adapterProfileId": "ap-1", "domainKey": "gaming-crm"},
    )
    assert first.status_code == 200
    second = await client.post(
        "/internal/adapter-profiles/register",
        headers={"X-Internal-Api-Key": "secret"},
        json={"adapterProfileId": "ap-1", "domainKey": "other"},
    )
    assert second.status_code == 200
    assert second.json()["gatewayProfileId"] == first.json()["gatewayProfileId"]

    override = app.dependency_overrides[get_session]
    agen = override()
    try:
        session = await anext(agen)
        rows = (await session.scalars(select(GatewayAdapterProfile))).all()
        assert len(rows) == 1
    finally:
        await agen.aclose()


@pytest.mark.asyncio
async def test_register_duplicate_with_conflicts_returns_existing_without_mutation(
    client: AsyncClient,
) -> None:
    settings.internal_adapter_api_key = "secret"
    first = await client.post(
        "/internal/adapter-profiles/register",
        headers={"X-Internal-Api-Key": "secret"},
        json={"adapterProfileId": "ap-1", "domainKey": "gaming-crm", "evidenceHash": "h1"},
    )
    assert first.status_code == 200
    gwid = first.json()["gatewayProfileId"]

    second = await client.post(
        "/internal/adapter-profiles/register",
        headers={"X-Internal-Api-Key": "secret"},
        json={"adapterProfileId": "ap-1", "domainKey": "other-domain", "evidenceHash": "h2"},
    )
    assert second.status_code == 200
    assert second.json()["gatewayProfileId"] == gwid

    override = app.dependency_overrides[get_session]
    agen = override()
    try:
        session = await anext(agen)
        row = await session.scalar(
            select(GatewayAdapterProfile).where(GatewayAdapterProfile.adapter_profile_id == "ap-1")
        )
        assert row is not None
        # No mutation on duplicates: keep the originally-registered domain.
        assert row.domain_key == "gaming-crm"
    finally:
        await agen.aclose()


@pytest.mark.asyncio
async def test_unique_constraint_prevents_duplicate_adapter_profile_id(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        session.add(
            GatewayAdapterProfile(
                gateway_profile_id="gw-1",
                adapter_profile_id="ap-dup",
                domain_key="dk",
                status="Registered",
            )
        )
        await session.commit()

    async with db_sessionmaker() as session2:
        session2.add(
            GatewayAdapterProfile(
                gateway_profile_id="gw-2",
                adapter_profile_id="ap-dup",
                domain_key="dk",
                status="Registered",
            )
        )
        with pytest.raises(IntegrityError):
            await session2.commit()

