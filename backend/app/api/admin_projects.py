"""Admin project and API key management endpoints (M4)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import GatewayRequest, Project, ProjectApiKey
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.services.project_key_service import create_api_key, revoke_api_key
from app.services.audit_service import log_admin_action

router = APIRouter(prefix="/admin/projects", tags=["admin"])


class ProjectCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class ProjectView(BaseModel):
    id: str
    name: str
    created_at: datetime
    active_key_count: int
    total_request_count: int


class ApiKeyCreateBody(BaseModel):
    label: str | None = Field(default=None, max_length=100)


class ApiKeyCreatedView(BaseModel):
    id: str
    project_id: str
    label: str | None
    prefix: str
    created_at: datetime
    revoked_at: datetime | None
    plaintext: str


class ApiKeyView(BaseModel):
    id: str
    project_id: str
    label: str | None
    prefix: str
    created_at: datetime
    revoked_at: datetime | None


async def _project_or_404(session: AsyncSession, project_id: str) -> Project:
    row = await session.get(Project, project_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return row


def _to_key_view(row: ProjectApiKey) -> ApiKeyView:
    return ApiKeyView(
        id=row.id,
        project_id=row.project_id,
        label=row.label,
        prefix=row.prefix,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


@router.get("", response_model=list[ProjectView])
async def list_projects(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProjectView]:
    projects = list((await session.execute(select(Project).order_by(Project.created_at.desc()))).scalars())
    output: list[ProjectView] = []
    for project in projects:
        active_keys = (
            await session.execute(
                select(func.count())
                .select_from(ProjectApiKey)
                .where(
                    ProjectApiKey.project_id == project.id,
                    ProjectApiKey.revoked_at.is_(None),
                )
            )
        ).scalar_one()
        request_count = (
            await session.execute(
                select(func.count())
                .select_from(GatewayRequest)
                .where(GatewayRequest.project_id == project.id)
            )
        ).scalar_one()
        output.append(
            ProjectView(
                id=project.id,
                name=project.name,
                created_at=project.created_at,
                active_key_count=int(active_keys),
                total_request_count=int(request_count),
            )
        )
    return output


@router.post("", response_model=ProjectView, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateBody,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectView:
    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project name cannot be blank",
        )
    project = Project(name=name)
    session.add(project)
    await session.flush()
    await log_admin_action(
        session,
        actor=admin,
        action="project.create",
        resource_type="project",
        resource_id=project.id,
        metadata={"name": project.name},
    )
    return ProjectView(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        active_key_count=0,
        total_request_count=0,
    )


@router.get("/{project_id}/keys", response_model=list[ApiKeyView])
async def list_project_keys(
    project_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ApiKeyView]:
    await _project_or_404(session, project_id)
    stmt = select(ProjectApiKey).where(ProjectApiKey.project_id == project_id).order_by(ProjectApiKey.created_at.desc())
    rows = list((await session.execute(stmt)).scalars())
    return [_to_key_view(r) for r in rows]


@router.post("/{project_id}/keys", response_model=ApiKeyCreatedView, status_code=status.HTTP_201_CREATED)
async def create_project_key(
    project_id: str,
    body: ApiKeyCreateBody,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiKeyCreatedView:
    project = await _project_or_404(session, project_id)
    label = body.label.strip() if body.label is not None else None
    if label == "":
        label = None
    issued = await create_api_key(session, project=project, label=label)
    key = issued.api_key
    await log_admin_action(
        session,
        actor=admin,
        action="project_api_key.issue",
        resource_type="project_api_key",
        resource_id=key.id,
        metadata={
            "project_id": key.project_id,
            "label": key.label,
            "prefix": key.prefix,
        },
    )
    return ApiKeyCreatedView(
        id=key.id,
        project_id=key.project_id,
        label=key.label,
        prefix=key.prefix,
        created_at=key.created_at,
        revoked_at=key.revoked_at,
        plaintext=issued.plaintext,
    )


@router.post("/{project_id}/keys/{key_id}/revoke", response_model=ApiKeyView)
async def revoke_project_key(
    project_id: str,
    key_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiKeyView:
    await _project_or_404(session, project_id)
    key = await session.get(ProjectApiKey, key_id)
    if key is None or key.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="api key not found")
    await revoke_api_key(session, key)
    await log_admin_action(
        session,
        actor=admin,
        action="project_api_key.revoke",
        resource_type="project_api_key",
        resource_id=key.id,
        metadata={
            "project_id": key.project_id,
            "label": key.label,
            "prefix": key.prefix,
            "revoked_at": key.revoked_at,
        },
    )
    return _to_key_view(key)
