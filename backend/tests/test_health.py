"""Smoke test for /health, /readyz, and /health/ready (M0 + v0.6)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import reset_engine
from app.main import app


class _FailingDbConnect:
    async def __aenter__(self) -> None:
        raise RuntimeError("simulated db failure")

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def test_health_returns_ok_with_metadata() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "conexus"
    assert "version" in body and isinstance(body["version"], str)


def test_readyz_returns_ok() -> None:
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    reset_engine()
    client = TestClient(app)
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {
        "db": True,
        "encryption": True,
        "model_aliases": True,
    }


def test_health_ready_alias_matches_readyz() -> None:
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    reset_engine()
    client = TestClient(app)
    assert client.get("/readyz").json() == client.get("/health/ready").json()


def test_readyz_returns_503_when_db_check_fails() -> None:
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    reset_engine()
    client = TestClient(app)

    fake_engine = MagicMock()
    fake_engine.connect = lambda: _FailingDbConnect()

    with patch("app.api.health.get_engine", return_value=fake_engine):
        response = client.get("/readyz")
    assert response.status_code == 503
    # Non-prod test client defaults to local — detailed checks allowed
    assert response.json()["detail"]["status"] == "not_ready"
    assert response.json()["detail"]["checks"]["db"] is False


def test_readyz_503_prod_hides_check_details(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prod 503 bodies must not include per-check flags (operator-safe, no leak surface)."""
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "auth_secret", "test-prod-auth-secret-not-default-value")
    monkeypatch.setattr(settings, "admin_password", "not-the-default-admin-password")
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    reset_engine()
    client = TestClient(app)

    fake_engine = MagicMock()
    fake_engine.connect = lambda: _FailingDbConnect()

    with patch("app.api.health.get_engine", return_value=fake_engine):
        response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["detail"] == {"status": "not_ready"}
