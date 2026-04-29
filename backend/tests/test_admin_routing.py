"""Tests for read-only admin routing policy APIs."""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
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


def _assert_no_secret_fields(value: Any) -> None:
    forbidden = {
        "api_key",
        "api_key_encrypted",
        "secret_hash",
        "plaintext",
        "prompt",
        "messages",
        "response_body",
    }
    if isinstance(value, dict):
        assert forbidden.isdisjoint(value)
        for child in value.values():
            _assert_no_secret_fields(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_secret_fields(child)


@pytest.mark.asyncio
async def test_routing_policy_requires_admin_auth(client: AsyncClient) -> None:
    response = await client.get("/admin/routing/policy")
    candidates_response = await client.get("/admin/routing/provider-candidates")

    assert response.status_code == 401
    assert candidates_response.status_code == 401


@pytest.mark.asyncio
async def test_routing_policy_describes_current_static_aliases(
    client: AsyncClient,
) -> None:
    await _login(client)

    response = await client.get("/admin/routing/policy")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "default"
    assert body["mode"] == "static"
    assert body["default_alias"] == "conexus-default"
    aliases = {row["alias"]: row for row in body["aliases"]}
    assert aliases["conexus-fast"] == {
        "alias": "conexus-fast",
        "primary_provider": "anthropic",
        "primary_model": "claude-haiku-4-5-20251001",
        "fallback_provider": "openai",
        "fallback_model": "gpt-4o-mini",
    }
    assert aliases["conexus-default"]["primary_provider"] == "anthropic"
    assert aliases["conexus-default"]["fallback_provider"] == "openai"
    direct_routes = {row["provider"]: row for row in body["direct_routes"]}
    assert direct_routes["anthropic"]["fallback_enabled"] is False
    assert "claude-" in direct_routes["anthropic"]["model_prefixes"]
    assert direct_routes["openai"]["fallback_enabled"] is False
    assert "gpt-" in direct_routes["openai"]["model_prefixes"]
    _assert_no_secret_fields(body)


@pytest.mark.asyncio
async def test_provider_candidates_include_active_configs_and_env_fallback(
    client: AsyncClient,
    db_sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", "sk-env-secret")
    async with db_sessionmaker() as session:
        session.add_all(
            [
                models.ProviderConfig(
                    id="active_provider",
                    provider="anthropic",
                    label="Primary Anthropic",
                    api_key_encrypted="encrypted-secret",
                    key_mask="sk-ant...1234",
                    is_active=True,
                    last_test_status="ok",
                ),
                models.ProviderConfig(
                    id="revoked_provider",
                    provider="openai",
                    label="Revoked OpenAI",
                    api_key_encrypted="encrypted-revoked-secret",
                    key_mask="sk-openai...9999",
                    is_active=False,
                ),
            ]
        )
        await session.commit()
    await _login(client)

    response = await client.get("/admin/routing/provider-candidates")

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "provider": "anthropic",
            "source": "bo_config",
            "config_id": "active_provider",
            "label": "Primary Anthropic",
            "key_mask": "sk-ant...1234",
            "is_active": True,
            "last_test_status": "ok",
            "last_tested_at": None,
        },
        {
            "provider": "openai",
            "source": "env",
            "config_id": None,
            "label": "Environment fallback",
            "key_mask": None,
            "is_active": True,
            "last_test_status": None,
            "last_tested_at": None,
        },
    ]
    _assert_no_secret_fields(body)
    assert "sk-env-secret" not in response.text
    assert "encrypted-secret" not in response.text
