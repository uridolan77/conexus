from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models
from app.db.session import get_session
from app.main import app
from app.services.password_hasher import hash_password, verify_password
from app.services.provider_config_service import (
    reset_provider_factory_for_tests,
    set_provider_factory_for_tests,
)


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


async def _login_env_admin(client: AsyncClient) -> None:
    res = await client.post("/admin/auth/login", json={"username": "admin", "password": "admin"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_password_hashing_roundtrip() -> None:
    hashed = hash_password("pw123")
    assert hashed != "pw123"
    assert verify_password("pw123", hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.asyncio
async def test_db_admin_login_succeeds_and_sets_last_login(client: AsyncClient, db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        user = models.AdminUser(
            username="root",
            email="root@example.com",
            password_hash=hash_password("s3cret"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        user_id = user.id

    res = await client.post("/admin/auth/login", json={"username": "root", "password": "s3cret"})
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "root"
    assert body["admin_user_id"] == user_id

    session_res = await client.get("/admin/auth/session")
    assert session_res.status_code == 200
    assert session_res.json()["admin_user_id"] == user_id

    async with db_sessionmaker() as session:
        refreshed = await session.get(models.AdminUser, user_id)
        assert refreshed is not None
        assert refreshed.last_login_at is not None


@pytest.mark.asyncio
async def test_db_admin_wrong_password_fails(client: AsyncClient, db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        user = models.AdminUser(
            username="root",
            email=None,
            password_hash=hash_password("pw"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    res = await client.post("/admin/auth/login", json={"username": "root", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_db_admin_inactive_fails(client: AsyncClient, db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        user = models.AdminUser(
            username="root",
            email=None,
            password_hash=hash_password("pw"),
            is_active=False,
        )
        session.add(user)
        await session.commit()

    res = await client.post("/admin/auth/login", json={"username": "root", "password": "pw"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_env_fallback_only_when_no_admin_users_exist(client: AsyncClient, db_sessionmaker) -> None:
    # When no admin users exist, env fallback works.
    res = await client.post("/admin/auth/login", json={"username": "admin", "password": "admin"})
    assert res.status_code == 200
    assert res.json()["admin_user_id"] is None

    # Once an admin user exists, env fallback must stop working.
    async with db_sessionmaker() as session:
        user = models.AdminUser(
            username="root",
            email=None,
            password_hash=hash_password("pw"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

    res2 = await client.post("/admin/auth/login", json={"username": "admin", "password": "admin"})
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_audit_endpoint_requires_admin_auth(client: AsyncClient) -> None:
    res = await client.get("/admin/audit")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_successful_mutations_write_audit_rows_and_no_secrets_leak(
    client: AsyncClient, db_sessionmaker
) -> None:
    await _login_env_admin(client)

    class _FakeProvider:
        async def chat(self, messages, *, model: str, max_tokens: int = 4096, temperature: float = 0.2):
            return object()

        async def aclose(self) -> None:
            pass

    def fake_factory(_provider: str, _api_key: str):
        return _FakeProvider()

    set_provider_factory_for_tests(fake_factory)

    provider_secret = "sk-test-1234567890-secret"
    try:
        created_provider = await client.post(
            "/admin/providers",
            json={"provider": "openai", "label": "Primary", "api_key": provider_secret},
        )
        assert created_provider.status_code == 201
        provider_id = created_provider.json()["id"]

        tested_provider = await client.post(f"/admin/providers/{provider_id}/test", json={})
        assert tested_provider.status_code == 200

        revoked_provider = await client.post(f"/admin/providers/{provider_id}/revoke")
        assert revoked_provider.status_code == 200
    finally:
        reset_provider_factory_for_tests()

    created_project = await client.post("/admin/projects", json={"name": "payments"})
    assert created_project.status_code == 201
    project_id = created_project.json()["id"]

    created_key = await client.post(
        f"/admin/projects/{project_id}/keys",
        json={"label": "prod"},
    )
    assert created_key.status_code == 201
    plaintext_key = created_key.json()["plaintext"]
    key_id = created_key.json()["id"]

    revoked_key = await client.post(f"/admin/projects/{project_id}/keys/{key_id}/revoke")
    assert revoked_key.status_code == 200

    updated_limits = await client.put(
        f"/admin/projects/{project_id}/limits",
        json={"limit_mode": "hard", "daily_request_limit": 10},
    )
    assert updated_limits.status_code == 200

    audit = await client.get("/admin/audit?limit=200&offset=0")
    assert audit.status_code == 200
    body = audit.json()
    assert body["total"] >= 7
    actions = [row["action"] for row in body["items"]]
    for required in [
        "provider.create",
        "provider.test",
        "provider.revoke",
        "project.create",
        "project_api_key.issue",
        "project_api_key.revoke",
        "project_limits.update",
    ]:
        assert required in actions

    # Ensure no sensitive values appear in the audit response.
    audit_text = audit.text
    assert provider_secret not in audit_text
    assert plaintext_key not in audit_text
    assert "secret_hash" not in audit_text
    assert "api_key_encrypted" not in audit_text

    # Ensure we didn't accidentally store provider secret in DB audit logs either.
    async with db_sessionmaker() as session:
        rows = list((await session.execute(select(models.AuditLog))).scalars().all())
        assert rows
        combined = "\n".join([r.metadata_json or "" for r in rows])
        assert provider_secret not in combined
        assert plaintext_key not in combined
        assert "secret_hash" not in combined


@pytest.mark.asyncio
async def test_audit_filters_and_pagination(client: AsyncClient) -> None:
    await _login_env_admin(client)

    p1 = await client.post("/admin/projects", json={"name": "p1"})
    p2 = await client.post("/admin/projects", json={"name": "p2"})
    assert p1.status_code == 201
    assert p2.status_code == 201

    page1 = await client.get("/admin/audit?limit=1&offset=0&action=project.create")
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1["limit"] == 1
    assert body1["offset"] == 0
    assert body1["total"] >= 2
    assert len(body1["items"]) == 1
    assert body1["items"][0]["action"] == "project.create"

    page2 = await client.get("/admin/audit?limit=1&offset=1&action=project.create")
    assert page2.status_code == 200
    body2 = page2.json()
    assert body2["offset"] == 1
    assert body2["total"] == body1["total"]
    assert len(body2["items"]) == 1
    assert body2["items"][0]["action"] == "project.create"

