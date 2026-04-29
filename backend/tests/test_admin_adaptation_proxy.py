"""Tests for Conexus -> adaptation admin proxy endpoints."""

from __future__ import annotations

import os
from typing import Any, Callable

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def _login_admin(client: AsyncClient) -> None:
    response = await client.post("/admin/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200


class _MockAsyncClient:
    def __init__(
        self,
        *,
        timeout: httpx.Timeout | None = None,
        handler: Callable[..., httpx.Response],
    ) -> None:
        self.timeout = timeout
        self._handler = handler

    async def __aenter__(self) -> "_MockAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def request(self, method: str, url: str, *, params: Any = None, json: Any = None) -> httpx.Response:
        return self._handler(method=method, url=url, params=params, json=json, timeout=self.timeout)


@pytest.mark.asyncio
async def test_admin_adaptation_requires_session(client: AsyncClient) -> None:
    response = await client.get("/admin/adaptation/plans")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_adaptation_missing_base_url_returns_503(client: AsyncClient) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = None
    response = await client.get("/admin/adaptation/plans")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == 503
    assert "not configured" in body["title"].lower() or "not configured" in body["detail"].lower()


@pytest.mark.asyncio
async def test_admin_adaptation_forwards_query_params(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000/"

    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(200, json=[{"id": "plan_1"}], headers={"content-type": "application/json"})

    def factory(*, timeout: httpx.Timeout) -> _MockAsyncClient:
        return _MockAsyncClient(timeout=timeout, handler=handler)

    monkeypatch.setattr("app.api.admin_adaptation.httpx.AsyncClient", factory)

    response = await client.get("/admin/adaptation/plans?status=Draft&domainKey=dk&status=Draft")
    assert response.status_code == 200
    assert response.json() == [{"id": "plan_1"}]
    assert captured["method"] == "GET"
    assert captured["url"].endswith("/adaptation-plans")
    # multi_items preserves duplicates
    assert ("status", "Draft") in list(captured["params"])
    assert ("domainKey", "dk") in list(captured["params"])


@pytest.mark.asyncio
async def test_admin_adaptation_passthrough_problem_details_400(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"

    def handler(**_kwargs: Any) -> httpx.Response:
        return httpx.Response(
            400,
            content=b'{"title":"Bad Request","detail":"invalid filter"}',
            headers={"content-type": "application/problem+json"},
        )

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/plans?status=wat")
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "invalid filter"


@pytest.mark.asyncio
async def test_admin_adaptation_passthrough_problem_details_404(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"

    def handler(**_kwargs: Any) -> httpx.Response:
        return httpx.Response(
            404,
            json={"title": "Not Found", "detail": "missing"},
            headers={"content-type": "application/problem+json"},
        )

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/plans/plan_missing")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "missing"


@pytest.mark.asyncio
async def test_admin_adaptation_connect_error_returns_502(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"

    def handler(**kwargs: Any) -> httpx.Response:
        request = httpx.Request(kwargs["method"], kwargs["url"])
        raise httpx.ConnectError("connect failed", request=request)

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/plans")
    assert response.status_code == 502
    assert response.json()["status"] == 502


@pytest.mark.asyncio
async def test_admin_adaptation_timeout_returns_504(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"

    def handler(**kwargs: Any) -> httpx.Response:
        request = httpx.Request(kwargs["method"], kwargs["url"])
        raise httpx.ReadTimeout("timed out", request=request)

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/plans")
    assert response.status_code == 504
    assert response.json()["status"] == 504


@pytest.mark.asyncio
async def test_admin_adaptation_approve_injects_identity(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"

    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(200, json={"ok": True}, headers={"content-type": "application/json"})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.post("/admin/adaptation/plans/plan_1/approve", json={"approvedByUserId": "spoof"})
    assert response.status_code == 200
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/adaptation-plans/plan_1/approve")
    assert captured["json"]["approvedByUserId"] == "admin-user"
    assert captured["json"]["approverRoles"] == ["ComplianceReviewer"]


@pytest.mark.asyncio
async def test_admin_adaptation_run_injects_created_by_and_uses_longer_timeout(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"

    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(200, json={"runId": "run_1"}, headers={"content-type": "application/json"})

    def factory(*, timeout: httpx.Timeout) -> _MockAsyncClient:
        # record timeout object so we can assert it is not the 10s default
        captured["timeout"] = timeout
        return _MockAsyncClient(timeout=timeout, handler=handler)

    monkeypatch.setattr("app.api.admin_adaptation.httpx.AsyncClient", factory)

    response = await client.post("/admin/adaptation/plans/plan_1/run", json={"createdByUserId": "spoof"})
    assert response.status_code == 200
    assert captured["json"]["createdByUserId"] == "admin-user"
    assert captured["url"].endswith("/adaptation-plans/plan_1/run")
    assert isinstance(captured["timeout"], httpx.Timeout)
    assert captured["timeout"].read == 30.0

