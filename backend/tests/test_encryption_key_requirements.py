"""Tests for ENCRYPTION_KEY requirement and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.services.secret_crypto import (
    SecretCryptoError,
    ensure_encryption_ready,
    reset_fernet_for_tests,
)


def test_settings_require_encryption_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_encryption_key_invalid_value_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_fernet_for_tests()
    monkeypatch.setattr(settings, "encryption_key", "not-a-valid-fernet-key")
    with pytest.raises(SecretCryptoError, match="invalid encryption key"):
        ensure_encryption_ready()
    reset_fernet_for_tests()
