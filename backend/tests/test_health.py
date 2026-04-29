"""Smoke test for /health and /health/ready (M0)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import reset_engine
from app.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_ok() -> None:
    # Ensure readiness can check DB connectivity without requiring Postgres.
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    reset_engine()
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
