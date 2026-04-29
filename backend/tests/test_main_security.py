"""Startup security guard tests."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.main import _ensure_prod_secret_hardening


@pytest.mark.parametrize(
    ("auth_secret", "admin_password", "message"),
    [
        ("replace-me-local", "safe-pass", "AUTH_SECRET uses default"),
        ("safe-secret", "admin", "ADMIN_PASSWORD uses default"),
    ],
)
def test_prod_guard_rejects_default_secrets(
    monkeypatch: pytest.MonkeyPatch,
    auth_secret: str,
    admin_password: str,
    message: str,
) -> None:
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "auth_secret", auth_secret)
    monkeypatch.setattr(settings, "admin_password", admin_password)

    with pytest.raises(RuntimeError, match=message):
        _ensure_prod_secret_hardening()


def test_prod_guard_allows_non_default_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "auth_secret", "safe-secret")
    monkeypatch.setattr(settings, "admin_password", "safe-pass")

    _ensure_prod_secret_hardening()


def test_non_prod_skips_default_secret_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "auth_secret", "replace-me-local")
    monkeypatch.setattr(settings, "admin_password", "admin")

    _ensure_prod_secret_hardening()
