"""Minimal admin session auth for BO routes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AdminUser
from app.services.password_hasher import verify_password

ADMIN_SESSION_COOKIE = "conexus_admin_session"


@dataclass(slots=True)
class AdminSession:
    username: str
    admin_user_id: str | None = None


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _sign(payload: bytes) -> str:
    digest = hmac.new(
        settings.auth_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).digest()
    return _b64_encode(digest)


def issue_admin_session_token(*, username: str, admin_user_id: str | None) -> str:
    exp = int(time.time()) + settings.admin_session_ttl_hours * 3600
    # Payload v2: username|admin_user_id|exp
    # Payload v1 (legacy): username|exp
    admin_user_id_raw = admin_user_id or ""
    payload = f"{username}|{admin_user_id_raw}|{exp}".encode("utf-8")
    signature = _sign(payload)
    return f"{_b64_encode(payload)}.{signature}"


def parse_admin_session_token(token: str) -> AdminSession | None:
    if "." not in token:
        return None
    payload_b64, signature = token.split(".", 1)
    try:
        payload = _b64_decode(payload_b64)
    except Exception:
        return None
    expected = _sign(payload)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        parts = payload.decode("utf-8").split("|")
        if len(parts) == 2:
            username, exp_raw = parts
            admin_user_id = None
        elif len(parts) == 3:
            username, admin_user_id_raw, exp_raw = parts
            admin_user_id = admin_user_id_raw or None
        else:
            return None
        exp = int(exp_raw)
    except Exception:
        return None
    if exp < int(time.time()):
        return None
    return AdminSession(username=username, admin_user_id=admin_user_id)


def validate_admin_credentials(username: str, password: str) -> bool:
    return hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password, settings.admin_password
    )


async def any_admin_users_exist(session: AsyncSession) -> bool:
    count_stmt = select(func.count()).select_from(AdminUser)
    count = int((await session.execute(count_stmt)).scalar_one() or 0)
    return count > 0


async def authenticate_admin_user(
    session: AsyncSession, *, username: str, password: str
) -> AdminUser | None:
    stmt = select(AdminUser).where(AdminUser.username == username)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def require_admin_session(token: str | None) -> AdminSession:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="admin auth required",
        )
    session = parse_admin_session_token(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin session",
        )
    return session
