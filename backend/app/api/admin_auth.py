"""Admin auth endpoints for BO access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.services.admin_auth_service import (
    ADMIN_SESSION_COOKIE,
    AdminSession,
    any_admin_users_exist,
    authenticate_admin_user,
    issue_admin_session_token,
    require_admin_session,
    validate_admin_credentials,
)

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


async def get_admin_session(
    session_cookie: Annotated[str | None, Cookie(alias=ADMIN_SESSION_COOKIE)] = None,
) -> AdminSession:
    return require_admin_session(session_cookie)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginBody,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginResponse:
    username = body.username.strip()
    password = body.password

    admin_user_id: str | None = None
    if await any_admin_users_exist(session):
        user = await authenticate_admin_user(session, username=username, password=password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            )
        user.last_login_at = datetime.now(timezone.utc)
        await session.flush()
        admin_user_id = user.id
        username = user.username
    else:
        if not settings.effective_allow_env_admin_fallback:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="admin bootstrap required",
            )
        if not validate_admin_credentials(username, password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            )

    token = issue_admin_session_token(username=username, admin_user_id=admin_user_id)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "prod",
        max_age=settings.admin_session_ttl_hours * 3600,
        path="/",
    )
    return LoginResponse(username=username, admin_user_id=admin_user_id)


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/session", response_model=SessionResponse)
async def session_info(
    admin: Annotated[AdminSession, Depends(get_admin_session)],
) -> SessionResponse:
    return SessionResponse(username=admin.username, admin_user_id=admin.admin_user_id)
