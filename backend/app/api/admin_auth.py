"""Admin auth endpoints for BO access."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.admin_auth_service import (
    ADMIN_SESSION_COOKIE,
    AdminSession,
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


class SessionResponse(BaseModel):
    username: str


async def get_admin_session(
    session_cookie: Annotated[str | None, Cookie(alias=ADMIN_SESSION_COOKIE)] = None,
) -> AdminSession:
    return require_admin_session(session_cookie)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginBody, response: Response) -> LoginResponse:
    if not validate_admin_credentials(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    token = issue_admin_session_token(body.username)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "prod",
        max_age=settings.admin_session_ttl_hours * 3600,
        path="/",
    )
    return LoginResponse(username=body.username)


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/session", response_model=SessionResponse)
async def session_info(
    admin: Annotated[AdminSession, Depends(get_admin_session)],
) -> SessionResponse:
    return SessionResponse(username=admin.username)
