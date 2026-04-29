"""Tests for M3 admin auth endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
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


@pytest.mark.asyncio
async def test_admin_login_session_logout_flow(client: AsyncClient) -> None:
    missing = await client.get("/admin/auth/session")
    assert missing.status_code == 401

    login = await client.post(
        "/admin/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert login.status_code == 200
    assert login.json() == {"ok": True, "username": "admin", "admin_user_id": None}

    session = await client.get("/admin/auth/session")
    assert session.status_code == 200
    assert session.json() == {"username": "admin", "admin_user_id": None}

    logout = await client.post("/admin/auth/logout")
    assert logout.status_code == 200

    after_logout = await client.get("/admin/auth/session")
    assert after_logout.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_invalid_credentials(client: AsyncClient) -> None:
    response = await client.post(
        "/admin/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_rate_limited_after_threshold_and_resets_on_success(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "admin_login_max_failures", 2)
    monkeypatch.setattr(settings, "admin_login_window_seconds", 600)

    r1 = await client.post("/admin/auth/login", json={"username": "admin", "password": "wrong"})
    assert r1.status_code == 401

    r2 = await client.post("/admin/auth/login", json={"username": "admin", "password": "wrong"})
    assert r2.status_code == 429

    ok = await client.post("/admin/auth/login", json={"username": "admin", "password": "admin"})
    assert ok.status_code == 429

    # After success, failures are cleared.
    again = await client.post("/admin/auth/login", json={"username": "admin", "password": "wrong"})
    assert again.status_code == 429


@pytest.mark.asyncio
async def test_admin_login_rate_limiter_normalizes_username(client: AsyncClient, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "admin_login_max_failures", 1)
    monkeypatch.setattr(settings, "admin_login_window_seconds", 600)

    r1 = await client.post("/admin/auth/login", json={"username": " Admin ", "password": "wrong"})
    assert r1.status_code == 429 or r1.status_code == 401

    r2 = await client.post("/admin/auth/login", json={"username": "admin", "password": "wrong"})
    assert r2.status_code == 429


@pytest.mark.asyncio
async def test_rate_limited_login_with_correct_password_returns_429_and_no_cookie_and_audited(
    client: AsyncClient, db_sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "admin_login_max_failures", 1)
    monkeypatch.setattr(settings, "admin_login_window_seconds", 600)

    # Trigger lockout.
    first = await client.post("/admin/auth/login", json={"username": "admin", "password": "wrong"})
    assert first.status_code == 429

    # Correct password should still be blocked.
    locked = await client.post("/admin/auth/login", json={"username": "admin", "password": "admin"})
    assert locked.status_code == 429
    assert locked.headers.get("set-cookie") is None

    async with db_sessionmaker() as session:
        rows = list(
            (
                await session.execute(
                    select(models.AuditLog)
                    .where(models.AuditLog.action == "admin.login")
                    .order_by(models.AuditLog.created_at.desc())
                    .limit(5)
                )
            ).scalars()
        )
        assert rows
        assert "rate_limited" in (rows[0].metadata_json or "")
