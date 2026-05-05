from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models
from app.services.provider_config_service import (
    get_active_gateway_model_alias,
    list_enabled_provider_configs,
)


@pytest_asyncio.fixture
async def sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield sm
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_enabled_provider_configs_filters_inactive_and_revoked(sessionmaker) -> None:
    async with sessionmaker() as session:
        active = models.ProviderConfig(
            provider="openai",
            label="active",
            api_key_encrypted="encrypted",
            key_mask="sk-...",
            is_active=True,
        )
        inactive = models.ProviderConfig(
            provider="anthropic",
            label="inactive",
            api_key_encrypted="encrypted",
            key_mask="sk-...",
            is_active=False,
        )
        revoked = models.ProviderConfig(
            provider="openai",
            label="revoked",
            api_key_encrypted="encrypted",
            key_mask="sk-...",
            is_active=True,
            revoked_at=models._utcnow(),
        )
        session.add_all([active, inactive, revoked])
        await session.commit()

    async with sessionmaker() as session:
        rows = await list_enabled_provider_configs(session)

    assert [row.label for row in rows] == ["active"]


@pytest.mark.asyncio
async def test_get_active_gateway_model_alias_returns_active_alias_only(sessionmaker) -> None:
    async with sessionmaker() as session:
        active = models.GatewayModelAlias(
            alias="conexus-fast",
            primary_provider="openai",
            primary_model="gpt-4o-mini",
            fallback_provider="anthropic",
            fallback_model="claude-haiku",
            status="active",
        )
        disabled = models.GatewayModelAlias(
            alias="conexus-disabled",
            primary_provider="openai",
            primary_model="gpt-4o-mini",
            status="disabled",
        )
        session.add_all([active, disabled])
        await session.commit()

    async with sessionmaker() as session:
        row = await get_active_gateway_model_alias(session, "conexus-fast")
        missing = await get_active_gateway_model_alias(session, "conexus-disabled")

    assert row is not None
    assert row.primary_provider == "openai"
    assert row.primary_model == "gpt-4o-mini"
    assert row.fallback_provider == "anthropic"
    assert missing is None
