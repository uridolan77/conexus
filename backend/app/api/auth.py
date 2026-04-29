"""Auth dependencies for the gateway API.

V1 only authenticates project-scoped requests via ``Authorization: Bearer
<project_api_key>``. BO admin auth lands in M3.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project, ProjectApiKey
from app.db.session import get_session
from app.services.project_key_service import verify_api_key


@dataclass(slots=True)
class AuthenticatedProject:
    project: Project
    api_key: ProjectApiKey


async def require_project_api_key(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> AuthenticatedProject:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    result = await verify_api_key(session, token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or revoked api key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    project, api_key = result
    return AuthenticatedProject(project=project, api_key=api_key)
