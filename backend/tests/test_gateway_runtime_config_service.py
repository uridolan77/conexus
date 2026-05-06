from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db import models
from app.llm.gateway_router import GatewayProvider
from app.llm.openai_adapter import OpenAIProvider
from app.services.gateway_runtime_config_service import resolve_request_provider
from app.services.secret_crypto import encrypt_secret


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
async def test_resolve_request_provider_prefers_bo_openai_config(sessionmaker, monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "env-openai-key")

    async with sessionmaker() as session:
        session.add(
            models.ProviderConfig(
                provider="openai",
                label="bo-openai",
                api_key_encrypted=encrypt_secret("bo-openai-key"),
                key_mask="bo...key",
                is_active=True,
            )
        )
        await session.commit()

    async with sessionmaker() as session:
        provider = await resolve_request_provider(session)

    assert isinstance(provider, OpenAIProvider)


@pytest.mark.asyncio
async def test_resolve_request_provider_falls_back_to_env_when_bo_missing(sessionmaker, monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "env-openai-key")

    async with sessionmaker() as session:
        provider = await resolve_request_provider(session)

    assert isinstance(provider, OpenAIProvider)


@pytest.mark.asyncio
async def test_resolve_request_provider_gateway_uses_bo_and_env_mix(sessionmaker, monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "gateway")
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", "env-openai-key")

    async with sessionmaker() as session:
        session.add(
            models.ProviderConfig(
                provider="anthropic",
                label="bo-anthropic",
                api_key_encrypted=encrypt_secret("bo-anthropic-key"),
                key_mask="bo...key",
                is_active=True,
            )
        )
        await session.commit()

    async with sessionmaker() as session:
        provider = await resolve_request_provider(session)

    assert isinstance(provider, GatewayProvider)


@pytest.mark.asyncio
async def test_resolve_request_provider_skips_bad_bo_secret_and_uses_env(sessionmaker, monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "env-openai-key")

    async with sessionmaker() as session:
        session.add(
            models.ProviderConfig(
                provider="openai",
                label="bad-encrypted",
                api_key_encrypted="not-a-valid-token",
                key_mask="bo...bad",
                is_active=True,
            )
        )
        await session.commit()

    async with sessionmaker() as session:
        provider = await resolve_request_provider(session)

    assert isinstance(provider, OpenAIProvider)
