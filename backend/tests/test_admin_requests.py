"""Tests for M5 request monitoring admin APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

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


async def _seed_requests(db_sessionmaker) -> dict[str, Any]:
    created = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
    async with db_sessionmaker() as session:
        project_a = models.Project(id="projecta", name="Project A", created_at=created)
        project_b = models.Project(id="projectb", name="Project B", created_at=created)
        key_a = models.ProjectApiKey(
            id="keya",
            project_id=project_a.id,
            prefix="cx_key_a",
            secret_hash="not-a-secret",
            label="prod",
            created_at=created,
        )
        session.add_all([project_a, project_b, key_a])
        session.add_all(
            [
                models.GatewayRequest(
                    id="reqrow1",
                    request_id="req_completed",
                    project_id=project_a.id,
                    api_key_id=key_a.id,
                    requested_model="conexus-default",
                    provider="openai",
                    model="gpt-4o-mini",
                    status="completed",
                    latency_ms=900,
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30,
                    estimated_cost=0.0012,
                    fallback_used=False,
                    created_at=created,
                    completed_at=created + timedelta(seconds=1),
                ),
                models.GatewayRequest(
                    id="reqrow2",
                    request_id="req_failed",
                    project_id=project_b.id,
                    api_key_id=None,
                    requested_model="claude-fast",
                    provider="anthropic",
                    model="claude-3-haiku",
                    status="failed",
                    latency_ms=6_000,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    estimated_cost=None,
                    fallback_used=True,
                    error_code="provider_timeout",
                    error_message="provider timed out",
                    created_at=created + timedelta(hours=1),
                    completed_at=created + timedelta(hours=1, seconds=6),
                ),
                models.GatewayRequest(
                    id="reqrow3",
                    request_id="req_started",
                    project_id=project_a.id,
                    api_key_id=key_a.id,
                    requested_model="conexus-default",
                    provider=None,
                    model=None,
                    status="started",
                    latency_ms=None,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    estimated_cost=None,
                    fallback_used=False,
                    created_at=created + timedelta(hours=2),
                    completed_at=None,
                ),
            ]
        )
        await session.commit()
    return {
        "project_a": project_a.id,
        "project_b": project_b.id,
        "created": created,
    }


def _assert_no_body_fields(value: Any) -> None:
    forbidden = {
        "prompt",
        "messages",
        "request_body",
        "response_body",
        "response_content",
        "completion_content",
        "choices",
        "secret_hash",
        "plaintext",
    }
    if isinstance(value, dict):
        assert forbidden.isdisjoint(value)
        for child in value.values():
            _assert_no_body_fields(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_body_fields(child)


@pytest.mark.asyncio
async def test_request_routes_require_admin_auth(client: AsyncClient) -> None:
    list_response = await client.get("/admin/requests")
    detail_response = await client.get("/admin/requests/req_completed")

    assert list_response.status_code == 401
    assert detail_response.status_code == 401


@pytest.mark.asyncio
async def test_list_returns_request_rows_and_pagination_shape(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    await _seed_requests(db_sessionmaker)
    await _login(client)

    response = await client.get("/admin/requests?limit=2&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "limit", "offset", "total"}
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["items"][0]["request_id"] == "req_started"
    assert body["items"][0]["project_name"] == "Project A"
    assert body["items"][0]["api_key_prefix"] == "cx_key_a"


@pytest.mark.asyncio
async def test_list_filters(client: AsyncClient, db_sessionmaker) -> None:
    seed = await _seed_requests(db_sessionmaker)
    await _login(client)
    created = seed["created"]

    cases = [
        ({"project_id": seed["project_b"]}, ["req_failed"]),
        ({"status": "failed"}, ["req_failed"]),
        ({"provider": "openai"}, ["req_completed"]),
        ({"requested_model": "claude-fast"}, ["req_failed"]),
        ({"model": "gpt-4o-mini"}, ["req_completed"]),
        ({"fallback_used": "true"}, ["req_failed"]),
        ({"error_code": "provider_timeout"}, ["req_failed"]),
        (
            {
                "created_from": (created + timedelta(minutes=30)).isoformat(),
                "created_to": (created + timedelta(hours=1, minutes=30)).isoformat(),
            },
            ["req_failed"],
        ),
    ]

    for params, expected_ids in cases:
        response = await client.get("/admin/requests", params=params)
        assert response.status_code == 200
        body = response.json()
        assert [item["request_id"] for item in body["items"]] == expected_ids
        assert body["total"] == len(expected_ids)


@pytest.mark.asyncio
async def test_model_search_matches_served_model(client: AsyncClient, db_sessionmaker) -> None:
    await _seed_requests(db_sessionmaker)
    await _login(client)

    response = await client.get("/admin/requests", params={"model_search": "gpt"})

    assert response.status_code == 200
    body = response.json()
    assert [item["request_id"] for item in body["items"]] == ["req_completed"]
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_model_search_matches_requested_model(client: AsyncClient, db_sessionmaker) -> None:
    await _seed_requests(db_sessionmaker)
    await _login(client)

    response = await client.get("/admin/requests", params={"model_search": "conexus"})

    assert response.status_code == 200
    body = response.json()
    assert [item["request_id"] for item in body["items"]] == [
        "req_started",
        "req_completed",
    ]
    assert body["total"] == 2


@pytest.mark.asyncio
async def test_detail_returns_one_request(client: AsyncClient, db_sessionmaker) -> None:
    await _seed_requests(db_sessionmaker)
    await _login(client)

    response = await client.get("/admin/requests/req_completed")

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req_completed"
    assert body["normalized_status_group"] == "success"
    assert body["token_summary"] == {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
    }
    assert body["cost_summary"] == {"estimated_cost": 0.0012, "currency": "USD"}
    assert body["routing_summary"] == {
        "requested_model": "conexus-default",
        "served_provider": "openai",
        "served_model": "gpt-4o-mini",
        "fallback_used": False,
    }


@pytest.mark.asyncio
async def test_detail_404_for_unknown_request_id(client: AsyncClient, db_sessionmaker) -> None:
    await _seed_requests(db_sessionmaker)
    await _login(client)

    response = await client.get("/admin/requests/missing")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_request_responses_do_not_include_body_or_secret_fields(
    client: AsyncClient,
    db_sessionmaker,
) -> None:
    await _seed_requests(db_sessionmaker)
    await _login(client)

    list_response = await client.get("/admin/requests")
    detail_response = await client.get("/admin/requests/req_failed")

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    _assert_no_body_fields(list_response.json())
    _assert_no_body_fields(detail_response.json())
