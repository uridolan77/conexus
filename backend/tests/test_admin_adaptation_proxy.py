"""Tests for Conexus -> adaptation admin proxy endpoints."""

from __future__ import annotations

from typing import Any, Callable

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db import models
from app.db.session import get_session
from app.main import app
from app.services.password_hasher import hash_password


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


async def _login_admin(client: AsyncClient) -> None:
    response = await client.post("/admin/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200


async def _create_admin_user(
    client: AsyncClient,
    *,
    username: str,
    password: str,
    roles_json: str,
) -> None:
    override = app.dependency_overrides.get(get_session)
    if override is None:
        raise AssertionError("test setup failed: missing db session override")
    agen = override()
    try:
        session = await anext(agen)
        user = models.AdminUser(
            username=username,
            email=None,
            password_hash=hash_password(password),
            roles_json=roles_json,
            is_active=True,
        )
        session.add(user)
        await session.commit()
    finally:
        await agen.aclose()


async def _login_db_admin(client: AsyncClient, *, username: str, password: str) -> None:
    response = await client.post("/admin/auth/login", json={"username": username, "password": password})
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

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Any = None,
        json: Any = None,
        headers: Any = None,
        **kwargs: Any,
    ) -> httpx.Response:
        return self._handler(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=headers,
            timeout=self.timeout,
            **kwargs,
        )


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
    assert captured["json"]["approvedByUserId"] == "admin"
    assert captured["json"]["approverRoles"] == [
        "ComplianceReviewer",
        "AdaptationPublisher",
        "AdaptationOperator",
    ]


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
    assert captured["json"]["createdByUserId"] == "admin"
    assert captured["url"].endswith("/adaptation-plans/plan_1/run")
    assert isinstance(captured["timeout"], httpx.Timeout)
    assert captured["timeout"].read == 30.0


_DEPLOYMENT_ROLES = (
    "ComplianceReviewer",
    "AdaptationPublisher",
    "AdaptationOperator",
)


@pytest.mark.asyncio
async def test_GET_run_evaluation_requires_session(client: AsyncClient) -> None:
    response = await client.get("/admin/adaptation/runs/run_1/evaluation")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_GET_run_evaluation_forwards_to_upstream(monkeypatch: pytest.MonkeyPatch, client: AsyncClient) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(200, json={"runId": "run_1"}, headers={"content-type": "application/json"})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/runs/run_1/evaluation")
    assert response.status_code == 200
    assert captured["method"] == "GET"
    assert captured["url"].endswith("/adaptation-runs/run_1/evaluation")


@pytest.mark.asyncio
async def test_GET_run_evaluation_preserves_404_problem_details(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"

    def handler(**_kwargs: Any) -> httpx.Response:
        return httpx.Response(
            404,
            json={"title": "Not Found", "detail": "no evidence"},
            headers={"content-type": "application/problem+json"},
        )

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/runs/run_1/evaluation")
    assert response.status_code == 404
    assert response.json()["detail"] == "no evidence"


@pytest.mark.asyncio
async def test_POST_publish_requires_admin(client: AsyncClient) -> None:
    response = await client.post("/admin/adaptation/profiles/p1/publish", json={"notes": "x"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_POST_publish_injects_admin_identity_and_roles(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
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

    response = await client.post("/admin/adaptation/profiles/p1/publish", json={"notes": "ship it"})
    assert response.status_code == 200
    assert captured["url"].endswith("/adapter-profiles/p1/publish")
    assert captured["json"]["publishedByUserId"] == "admin"
    assert captured["json"]["roles"] == list(_DEPLOYMENT_ROLES)
    assert captured["json"]["notes"] == "ship it"


@pytest.mark.asyncio
async def test_read_only_can_view_profiles_but_cannot_deploy(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _create_admin_user(client, username="ro", password="pw", roles_json='["ReadOnly"]')
    await _login_db_admin(client, username="ro", password="pw")
    settings.adaptation_api_base_url = "http://adapt:5000"

    def handler(**kwargs: Any) -> httpx.Response:
        if kwargs["method"] == "GET" and kwargs["url"].endswith("/adapter-profiles"):
            return httpx.Response(
                200, json=[{"id": "p1"}], headers={"content-type": "application/json"}
            )
        raise AssertionError(f"unexpected upstream proxy call: {kwargs['method']} {kwargs['url']}")

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    ok = await client.get("/admin/adaptation/profiles")
    assert ok.status_code == 200
    assert ok.json() == [{"id": "p1"}]

    forbidden = await client.post("/admin/adaptation/profiles/p1/publish", json={})
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_deploy_without_permission_returns_403_before_proxy(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _create_admin_user(client, username="viewer", password="pw", roles_json='["ReadOnly"]')
    await _login_db_admin(client, username="viewer", password="pw")
    settings.adaptation_api_base_url = "http://adapt:5000"

    def handler(**_kwargs: Any) -> httpx.Response:
        raise AssertionError("should not proxy when forbidden")

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    assert (await client.post("/admin/adaptation/profiles/p1/publish", json={})).status_code == 403
    assert (
        await client.post("/admin/adaptation/profiles/p1/activate-canary", json={"canaryPercent": 10})
    ).status_code == 403
    assert (await client.post("/admin/adaptation/profiles/p1/promote", json={})).status_code == 403
    assert (await client.post("/admin/adaptation/profiles/p1/rollback", json={"reason": "x"})).status_code == 403


@pytest.mark.asyncio
async def test_super_admin_gets_all_adaptation_roles(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _create_admin_user(client, username="sa", password="pw", roles_json='["SuperAdmin"]')
    await _login_db_admin(client, username="sa", password="pw")
    settings.adaptation_api_base_url = "http://adapt:5000"
    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(200, json={"ok": True}, headers={"content-type": "application/json"})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.post("/admin/adaptation/profiles/p1/publish", json={"notes": "x"})
    assert response.status_code == 200
    assert captured["json"]["roles"] == list(_DEPLOYMENT_ROLES)


@pytest.mark.asyncio
async def test_POST_publish_does_not_forward_browser_roles(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
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

    response = await client.post(
        "/admin/adaptation/profiles/p1/publish",
        json={
            "roles": ["FakeSuperAdmin"],
            "publishedByUserId": "attacker",
            "notes": "x",
        },
    )
    assert response.status_code == 200
    assert captured["json"]["publishedByUserId"] == "admin"
    assert captured["json"]["roles"] == list(_DEPLOYMENT_ROLES)
    assert captured["json"]["notes"] == "x"


@pytest.mark.asyncio
async def test_POST_publish_preserves_409_problem_details(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"

    def handler(**_kwargs: Any) -> httpx.Response:
        return httpx.Response(
            409,
            json={"title": "Conflict", "detail": "already published"},
            headers={"content-type": "application/problem+json"},
        )

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.post("/admin/adaptation/profiles/p1/publish", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "already published"


@pytest.mark.asyncio
async def test_POST_activate_canary_injects_identity_roles_and_percent(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
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

    response = await client.post(
        "/admin/adaptation/profiles/p1/activate-canary",
        json={"canaryPercent": 10},
    )
    assert response.status_code == 200
    assert captured["json"]["activatedByUserId"] == "admin"
    assert captured["json"]["roles"] == list(_DEPLOYMENT_ROLES)
    assert captured["json"]["canaryPercent"] == 10


@pytest.mark.asyncio
async def test_POST_activate_canary_rejects_invalid_percent_before_proxy(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    called = {"n": 0}

    def handler(**_kwargs: Any) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.post(
        "/admin/adaptation/profiles/p1/activate-canary",
        json={"canaryPercent": 99},
    )
    assert response.status_code == 400
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_POST_promote_injects_identity_and_roles(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
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

    response = await client.post("/admin/adaptation/profiles/p1/promote", json={})
    assert response.status_code == 200
    assert captured["json"]["userId"] == "admin"
    assert captured["json"]["roles"] == list(_DEPLOYMENT_ROLES)


@pytest.mark.asyncio
async def test_POST_rollback_injects_identity_roles_and_reason(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
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

    response = await client.post(
        "/admin/adaptation/profiles/p1/rollback",
        json={"reason": "  bad metrics  "},
    )
    assert response.status_code == 200
    assert captured["json"]["userId"] == "admin"
    assert captured["json"]["roles"] == list(_DEPLOYMENT_ROLES)
    assert captured["json"]["reason"] == "bad metrics"


@pytest.mark.asyncio
async def test_POST_rollback_rejects_empty_reason(client: AsyncClient) -> None:
    await _login_admin(client)
    response = await client.post(
        "/admin/adaptation/profiles/p1/rollback",
        json={"reason": "   "},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_GET_profile_activations_forwards_to_upstream(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(200, json=[], headers={"content-type": "application/json"})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/profiles/p1/activations")
    assert response.status_code == 200
    assert captured["url"].endswith("/adapter-profiles/p1/activations")


@pytest.mark.asyncio
async def test_GET_domain_active_profile_forwards_to_upstream(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(200, json={"profileId": "p1"}, headers={"content-type": "application/json"})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/domains/my-domain/active-profile")
    assert response.status_code == 200
    assert "/domains/my-domain/active-profile" in captured["url"]


@pytest.mark.asyncio
async def test_browser_supplied_roles_are_ignored_for_activate_canary(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
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

    response = await client.post(
        "/admin/adaptation/profiles/p1/activate-canary",
        json={"canaryPercent": 5, "roles": ["Evil"], "activatedByUserId": "attacker"},
    )
    assert response.status_code == 200
    assert captured["json"]["activatedByUserId"] == "admin"
    assert captured["json"]["roles"] == list(_DEPLOYMENT_ROLES)


@pytest.mark.asyncio
async def test_POST_publish_malformed_json_returns_400_without_proxy(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    called = {"n": 0}

    def handler(**_kwargs: Any) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.post(
        "/admin/adaptation/profiles/p1/publish",
        content=b"{not-json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["title"] == "Invalid JSON body."
    assert body["status"] == 400
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_POST_activate_canary_malformed_json_returns_400_without_proxy(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    called = {"n": 0}

    def handler(**_kwargs: Any) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.post(
        "/admin/adaptation/profiles/p1/activate-canary",
        content=b"[1,2,3]",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["title"] == "Invalid JSON body."
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_POST_rollback_malformed_json_returns_400_without_proxy(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    called = {"n": 0}

    def handler(**_kwargs: Any) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.post(
        "/admin/adaptation/profiles/p1/rollback",
        content=b"null",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["title"] == "Invalid JSON body."
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_POST_promote_malformed_json_returns_400_without_proxy(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    called = {"n": 0}

    def handler(**_kwargs: Any) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.post(
        "/admin/adaptation/profiles/p1/promote",
        content=b"oops",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["title"] == "Invalid JSON body."
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_GET_profile_deployment_events_forwards_to_upstream(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
    await _login_admin(client)
    settings.adaptation_api_base_url = "http://adapt:5000"
    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(200, json=[], headers={"content-type": "application/json"})

    monkeypatch.setattr(
        "app.api.admin_adaptation.httpx.AsyncClient",
        lambda *, timeout: _MockAsyncClient(timeout=timeout, handler=handler),
    )

    response = await client.get("/admin/adaptation/profiles/p1/deployment-events")
    assert response.status_code == 200
    assert captured["url"].endswith("/adapter-profiles/p1/deployment-events")


@pytest.mark.asyncio
async def test_POST_publish_forwards_idempotency_key_to_upstream(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
) -> None:
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

    response = await client.post(
        "/admin/adaptation/profiles/p1/publish",
        json={"notes": "n"},
        headers={"Idempotency-Key": "idem-abc-1"},
    )
    assert response.status_code == 200
    hdrs = captured.get("headers")
    assert hdrs is not None
    assert hdrs.get("Idempotency-Key") == "idem-abc-1"

