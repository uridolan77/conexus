"""Tests for M4 project and API key admin APIs."""

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


async def _login(client: AsyncClient) -> None:
    response = await client.post(
        "/admin/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_project_routes_require_admin_auth(client: AsyncClient) -> None:
    response = await client.get("/admin/projects")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_project_and_issue_revoke_key(client: AsyncClient) -> None:
    await _login(client)

    created_project = await client.post("/admin/projects", json={"name": "payments"})
    assert created_project.status_code == 201
    project = created_project.json()
    assert project["name"] == "payments"
    project_id = project["id"]

    listed_projects = await client.get("/admin/projects")
    assert listed_projects.status_code == 200
    assert listed_projects.json()[0]["id"] == project_id

    created_key = await client.post(
        f"/admin/projects/{project_id}/keys",
        json={"label": "prod"},
    )
    assert created_key.status_code == 201
    key_body = created_key.json()
    assert key_body["project_id"] == project_id
    assert key_body["prefix"]
    assert key_body["plaintext"].startswith("cx_live_")

    listed_keys = await client.get(f"/admin/projects/{project_id}/keys")
    assert listed_keys.status_code == 200
    keys_body = listed_keys.json()
    assert len(keys_body) == 1
    assert keys_body[0]["id"] == key_body["id"]
    assert "plaintext" not in keys_body[0]

    revoked = await client.post(
        f"/admin/projects/{project_id}/keys/{key_body['id']}/revoke"
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None


@pytest.mark.asyncio
async def test_create_project_rejects_whitespace_name(client: AsyncClient) -> None:
    await _login(client)

    response = await client.post("/admin/projects", json={"name": "   "})
    assert response.status_code == 400
    assert response.json()["detail"] == "project name cannot be blank"


@pytest.mark.asyncio
async def test_create_key_strips_blank_label_to_none(client: AsyncClient) -> None:
    await _login(client)

    created_project = await client.post("/admin/projects", json={"name": "billing"})
    project_id = created_project.json()["id"]

    created_key = await client.post(
        f"/admin/projects/{project_id}/keys",
        json={"label": "   "},
    )
    assert created_key.status_code == 201
    assert created_key.json()["label"] is None
