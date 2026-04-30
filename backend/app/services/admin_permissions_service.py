"""Admin role/permission mapping for BO endpoints."""

from __future__ import annotations

import json
from collections.abc import Iterable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import AdminUser
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession

ADAPTATION_VIEW = "adaptation.view"
ADAPTATION_APPROVE = "adaptation.approve"
ADAPTATION_PUBLISH = "adaptation.publish"
ADAPTATION_OPERATE = "adaptation.operate"
ADAPTATION_ROLLBACK = "adaptation.rollback"


_ALL_ADAPTATION_PERMS = {
    ADAPTATION_VIEW,
    ADAPTATION_APPROVE,
    ADAPTATION_PUBLISH,
    ADAPTATION_OPERATE,
    ADAPTATION_ROLLBACK,
}

_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "Admin": set(_ALL_ADAPTATION_PERMS),
    "SuperAdmin": set(_ALL_ADAPTATION_PERMS),
    "AdaptationReviewer": {ADAPTATION_VIEW, ADAPTATION_APPROVE, ADAPTATION_ROLLBACK},
    "AdaptationPublisher": {ADAPTATION_VIEW, ADAPTATION_PUBLISH},
    "AdaptationOperator": {ADAPTATION_VIEW, ADAPTATION_OPERATE, ADAPTATION_ROLLBACK},
    "ReadOnly": {ADAPTATION_VIEW},
}


def _parse_roles_json(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for item in data:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def resolve_permissions_from_roles(roles: Iterable[str]) -> set[str]:
    perms: set[str] = set()
    for role in roles:
        perms |= _ROLE_PERMISSIONS.get(role, set())
    return perms


async def get_admin_permissions(
    session: AsyncSession,
    *,
    admin: AdminSession,
) -> set[str]:
    # If the session is the env-fallback (no DB user), preserve current behavior:
    # treat as full admin for BO access.
    if not admin.admin_user_id:
        return set(_ALL_ADAPTATION_PERMS)

    row = await session.scalar(select(AdminUser).where(AdminUser.id == admin.admin_user_id))
    if row is None or not row.is_active:
        return set()
    roles = _parse_roles_json(row.roles_json)
    return resolve_permissions_from_roles(roles)


def require_adaptation_permission(permission: str):
    async def _dep(
        session: AsyncSession = Depends(get_session),
        admin: AdminSession = Depends(get_admin_session),
    ) -> None:
        perms = await get_admin_permissions(session, admin=admin)
        if permission not in perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return _dep


def deployment_roles_from_permissions(perms: set[str]) -> list[str]:
    roles: list[str] = []
    if ADAPTATION_APPROVE in perms or ADAPTATION_ROLLBACK in perms:
        roles.append("ComplianceReviewer")
    if ADAPTATION_PUBLISH in perms:
        roles.append("AdaptationPublisher")
    if ADAPTATION_OPERATE in perms:
        roles.append("AdaptationOperator")
    return roles

