"""Admin auth endpoints for BO access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.services.admin_login_rate_limiter import get_admin_login_rate_limiter
from app.services.admin_auth_service import (
    ADMIN_SESSION_COOKIE,
    AdminSession,
    InvalidAdminUsernameError,
    any_admin_users_exist,
    authenticate_admin_user,
    issue_admin_session_token,
    require_admin_session,
    validate_admin_credentials,
    validate_admin_username_format,
)
from app.services.audit_service import log_admin_action

router = APIRouter(prefix="/admin/auth", tags=["admin"])


class LoginBody(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    ok: bool = True
    username: str
    admin_user_id: str | None = None


class SessionResponse(BaseModel):
    username: str
    admin_user_id: str | None = None


async def _audit_login(
    session: AsyncSession,
    *,
    username: str,
    reason: str,
    admin_user_id: str | None = None,
    client_ip_present: bool,
) -> None:
    actor = (
        AdminSession(username=username, admin_user_id=admin_user_id)
        if reason == "success"
        else None
    )
    await log_admin_action(
        session,
        actor=actor,
        action="admin.login",
        resource_type="admin_auth",
        metadata={
            "username": username,
            "admin_user_id": admin_user_id,
            "reason": reason,
            "client_ip_present": client_ip_present,
        },
    )
    # Ensure audit rows persist even when we raise HTTPException afterwards.
    await session.commit()


async def _raise_rate_limited(
    session: AsyncSession, *, username: str, client_ip_present: bool
) -> None:
    await _audit_login(
        session,
        username=username,
        reason="rate_limited",
        client_ip_present=client_ip_present,
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="too many login attempts",
    )


async def _raise_invalid_credentials(
    session: AsyncSession, *, username: str, client_ip_present: bool
) -> None:
    await _audit_login(
        session,
        username=username,
        reason="invalid_credentials",
        client_ip_present=client_ip_present,
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid credentials",
    )


async def _raise_bootstrap_required(
    session: AsyncSession, *, username: str, client_ip_present: bool
) -> None:
    await _audit_login(
        session,
        username=username,
        reason="bootstrap_required",
        client_ip_present=client_ip_present,
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="admin bootstrap required",
    )


async def get_admin_session(
    session_cookie: Annotated[str | None, Cookie(alias=ADMIN_SESSION_COOKIE)] = None,
) -> AdminSession:
    return require_admin_session(session_cookie)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginBody,
    response: Response,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginResponse:
    username = body.username.strip()
    password = body.password
    client_ip = request.client.host if request.client else None

    try:
        validate_admin_username_format(username)
    except InvalidAdminUsernameError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    limiter = get_admin_login_rate_limiter(
        max_failures=settings.admin_login_max_failures,
        window_seconds=settings.admin_login_window_seconds,
    )
    if limiter.is_rate_limited(username=username, client_ip=client_ip):
        await _raise_rate_limited(
            session,
            username=username,
            client_ip_present=bool(client_ip),
        )

    admin_user_id: str | None = None
    if await any_admin_users_exist(session):
        user = await authenticate_admin_user(session, username=username, password=password)
        if user is None:
            limiter.record_failure(username=username, client_ip=client_ip)
            if limiter.is_rate_limited(username=username, client_ip=client_ip):
                await _raise_rate_limited(
                    session, username=username, client_ip_present=bool(client_ip)
                )
            await _raise_invalid_credentials(
                session, username=username, client_ip_present=bool(client_ip)
            )
        user.last_login_at = datetime.now(timezone.utc)
        await session.flush()
        admin_user_id = user.id
        username = user.username
    else:
        if not settings.effective_allow_env_admin_fallback:
            limiter.record_failure(username=username, client_ip=client_ip)
            if limiter.is_rate_limited(username=username, client_ip=client_ip):
                await _raise_rate_limited(
                    session, username=username, client_ip_present=bool(client_ip)
                )
            await _raise_bootstrap_required(
                session, username=username, client_ip_present=bool(client_ip)
            )
        if not validate_admin_credentials(username, password):
            limiter.record_failure(username=username, client_ip=client_ip)
            if limiter.is_rate_limited(username=username, client_ip=client_ip):
                await _raise_rate_limited(
                    session, username=username, client_ip_present=bool(client_ip)
                )
            await _raise_invalid_credentials(
                session, username=username, client_ip_present=bool(client_ip)
            )

    await _audit_login(
        session,
        username=username,
        admin_user_id=admin_user_id,
        reason="success",
        client_ip_present=bool(client_ip),
    )

    limiter.clear(username=username, client_ip=client_ip)
    token = issue_admin_session_token(username=username, admin_user_id=admin_user_id)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.effective_cookie_secure,
        max_age=settings.admin_session_ttl_hours * 3600,
        path="/",
    )
    return LoginResponse(username=username, admin_user_id=admin_user_id)


@router.post("/logout")
async def logout(
    response: Response,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, bool]:
    await log_admin_action(
        session,
        actor=admin,
        action="admin.logout",
        resource_type="admin_auth",
        metadata={"username": admin.username, "admin_user_id": admin.admin_user_id},
    )
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/session", response_model=SessionResponse)
async def session_info(
    admin: Annotated[AdminSession, Depends(get_admin_session)],
) -> SessionResponse:
    return SessionResponse(username=admin.username, admin_user_id=admin.admin_user_id)
