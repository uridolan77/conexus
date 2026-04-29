"""Admin audit log endpoints (M9)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import AuditLog
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession

router = APIRouter(prefix="/admin/audit", tags=["admin"])


class AuditLogItem(BaseModel):
    id: str
    actor_admin_user_id: str | None
    actor_username: str | None
    action: str
    resource_type: str
    resource_id: str | None
    metadata: Any | None
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditLogItem]
    limit: int
    offset: int
    total: int


def _parse_metadata(value: str | None) -> Any | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


@router.get("", response_model=AuditListResponse)
async def list_audit_logs(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    actor_admin_user_id: str | None = None,
    actor_username: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> AuditListResponse:
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if actor_admin_user_id:
        stmt = stmt.where(AuditLog.actor_admin_user_id == actor_admin_user_id)
        count_stmt = count_stmt.where(AuditLog.actor_admin_user_id == actor_admin_user_id)
    if actor_username:
        stmt = stmt.where(AuditLog.actor_username == actor_username)
        count_stmt = count_stmt.where(AuditLog.actor_username == actor_username)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
        count_stmt = count_stmt.where(AuditLog.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
        count_stmt = count_stmt.where(AuditLog.resource_id == resource_id)
    if created_from:
        stmt = stmt.where(AuditLog.created_at >= created_from)
        count_stmt = count_stmt.where(AuditLog.created_at >= created_from)
    if created_to:
        stmt = stmt.where(AuditLog.created_at <= created_to)
        count_stmt = count_stmt.where(AuditLog.created_at <= created_to)

    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    rows = list((await session.execute(stmt)).scalars().all())
    total = int((await session.execute(count_stmt)).scalar_one() or 0)

    return AuditListResponse(
        items=[
            AuditLogItem(
                id=r.id,
                actor_admin_user_id=r.actor_admin_user_id,
                actor_username=r.actor_username,
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                metadata=_parse_metadata(r.metadata_json),
                created_at=r.created_at,
            )
            for r in rows
        ],
        limit=limit,
        offset=offset,
        total=total,
    )

