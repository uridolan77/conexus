"""Tests for M3 provider configuration admin APIs."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models
from app.db.session import get_session
from app.main import app
from app.services.provider_config_service import set_provider_factory_for_tests
from app.services.secret_crypto import decrypt_secret


class _FakeProvider:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.raises = raises
        self.calls: list[dict] = []

    async def chat(
        self,
        messages,
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        self.calls.append(
            {
                "messages": list(messages),
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        if self.raises is not None:
            raise self.raises
        return object()

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
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as ac:
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
async def test_admin_provider_routes_require_auth(client: AsyncClient) -> None:
    response = await client.get("/admin/providers")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_provider_create_list_revoke_encrypts_secret(
    client: AsyncClient, db_sessionmaker
) -> None:
    await _login(client)

    plaintext = "sk-test-1234567890-secret"
    created = await client.post(
        "/admin/providers",
        json={
            "provider": "openai",
            "label": "Primary OpenAI",
            "api_key": plaintext,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["provider"] == "openai"
    assert body["key_mask"] == "sk-t...cret"
    assert "api_key" not in body
    assert "api_key_encrypted" not in body

    async with db_sessionmaker() as session:
        row = (
            await session.execute(
                select(models.ProviderConfig).where(
                    models.ProviderConfig.id == body["id"]
                )
            )
        ).scalar_one()
        assert row.api_key_encrypted != plaintext
        assert decrypt_secret(row.api_key_encrypted) == plaintext

    listed = await client.get("/admin/providers")
    assert listed.status_code == 200
    listed_body = listed.json()
    assert len(listed_body) == 1
    assert listed_body[0]["key_mask"] == "sk-t...cret"
    assert plaintext not in listed.text

    revoked = await client.post(f"/admin/providers/{body['id']}/revoke")
    assert revoked.status_code == 200
    revoked_body = revoked.json()
    assert revoked_body["is_active"] is False
    assert revoked_body["revoked_at"] is not None


@pytest.mark.asyncio
async def test_provider_test_endpoint_uses_fake_provider(client: AsyncClient) -> None:
    await _login(client)

    fake = _FakeProvider()

    def fake_factory(_provider: str, _api_key: str):
        return fake

    set_provider_factory_for_tests(fake_factory)

    created = await client.post(
        "/admin/providers",
        json={
            "provider": "anthropic",
            "label": "A",
            "api_key": "anthropic-secret-xyz",
        },
    )
    provider_id = created.json()["id"]

    tested = await client.post(
        f"/admin/providers/{provider_id}/test",
        json={},
    )
    assert tested.status_code == 200
    assert tested.json()["status"] == "ok"
    assert fake.calls


@pytest.mark.asyncio
async def test_provider_test_failure_is_sanitized(
    client: AsyncClient,
) -> None:
    await _login(client)

    secret = "sensitive-secret"

    class _Boom(Exception):
        pass

    fake = _FakeProvider(raises=_Boom(f"bad key {secret}"))

    def fake_factory(_provider: str, _api_key: str):
        return fake

    set_provider_factory_for_tests(fake_factory)

    created = await client.post(
        "/admin/providers",
        json={"provider": "openai", "label": None, "api_key": secret},
    )
    provider_id = created.json()["id"]

    tested = await client.post(f"/admin/providers/{provider_id}/test", json={})
    assert tested.status_code == 200
    body = tested.json()
    assert body["status"] == "failed"
    assert secret not in (body["error"] or "")
