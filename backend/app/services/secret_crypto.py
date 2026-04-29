"""Encryption helpers for provider API keys."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_fernet: Fernet | None = None


class SecretCryptoError(ValueError):
    pass


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        try:
            _fernet = Fernet(settings.encryption_key.encode("utf-8"))
        except Exception as exc:  # pragma: no cover - validated in ensure_encryption_ready
            raise SecretCryptoError("invalid encryption key") from exc
    return _fernet


def ensure_encryption_ready() -> None:
    _get_fernet()


def reset_fernet_for_tests() -> None:
    global _fernet
    _fernet = None


def encrypt_secret(secret: str) -> str:
    if not secret:
        raise SecretCryptoError("secret cannot be empty")
    token = _get_fernet().encrypt(secret.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(encrypted: str) -> str:
    try:
        raw = _get_fernet().decrypt(encrypted.encode("utf-8"))
    except InvalidToken as exc:
        raise SecretCryptoError("unable to decrypt provider secret") from exc
    return raw.decode("utf-8")
