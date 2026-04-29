"""Tests for M3 admin auth endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_admin_login_session_logout_flow(client: AsyncClient) -> None:
    missing = await client.get("/admin/auth/session")
    assert missing.status_code == 401

    login = await client.post(
        "/admin/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert login.status_code == 200
    assert login.json()["username"] == "admin"

    session = await client.get("/admin/auth/session")
    assert session.status_code == 200
    assert session.json() == {"username": "admin"}

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
