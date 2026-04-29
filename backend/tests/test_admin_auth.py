"""Tests for M3 admin auth endpoints."""

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
