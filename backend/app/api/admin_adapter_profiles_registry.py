"""Read-only admin endpoints for gateway adapter profile registry.

These endpoints are consumed by the BO:
- must require admin session
- must be read-only
- must not expose secrets
- must not call adaptation service
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import GatewayAdapterProfile, GatewayAdapterProfileActivation
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.services.admin_permissions_service import ADAPTATION_VIEW, require_adaptation_permission

router = APIRouter(prefix="/admin/adapter-profiles", tags=["admin"])


_SENSITIVE_KEY_RE = re.compile(
    r"api_?key|apikey|token|secret|password|authorization|bearer|^key$",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(key))


def _redact_metadata(value: Any, _seen: set[int] | None = None) -> Any:  # noqa: ANN401
    """Recursively redact values whose keys look sensitive."""
    if _seen is None:
        _seen = set()
    if value is None or not isinstance(value, (dict, list)):
        return value
    obj_id = id(value)
    if obj_id in _seen:
        return value
    _seen.add(obj_id)
    if isinstance(value, list):
        return [_redact_metadata(item, _seen) for item in value]
    return {
        k: (_REDACTED if _is_sensitive_key(k) else _redact_metadata(v, _seen))
        for k, v in value.items()
    }


def _parse_metadata(value: str | None) -> Any | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except Exception:
        return value
    return _redact_metadata(parsed)


class GatewayAdapterProfileRow(BaseModel):
    gateway_profile_id: str
    adapter_profile_id: str
    domain_key: str
    status: str
    composite_score: float | None
    profile_version: str | None
    evidence_hash: str | None
    semantic_context_hash: str | None
    slod_model_version: str | None
    created_at: datetime


class GatewayAdapterProfileDetail(GatewayAdapterProfileRow):
    source_run_id: str | None
    source_plan_id: str | None
    metadata: Any | None
    updated_at: datetime
    published_at: datetime | None


class GatewayAdapterProfileActivationRow(BaseModel):
    id: str
    domain_key: str
    gateway_profile_id: str
    status: str
    canary_percent: int | None
    previous_gateway_profile_id: str | None
    created_at: datetime
    activated_at: datetime | None
    promoted_at: datetime | None
    rolled_back_at: datetime | None
    metadata: Any | None


class GatewayAdapterProfileListResponse(BaseModel):
    items: list[GatewayAdapterProfileRow]
    limit: int
    offset: int
    total: int


@router.get("", response_model=GatewayAdapterProfileListResponse)
async def list_gateway_adapter_profiles(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GatewayAdapterProfileListResponse:
    stmt = (
        select(GatewayAdapterProfile)
        .order_by(desc(GatewayAdapterProfile.created_at))
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count()).select_from(GatewayAdapterProfile)
    rows = list((await session.execute(stmt)).scalars().all())
    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    return GatewayAdapterProfileListResponse(
        items=[
            GatewayAdapterProfileRow(
                gateway_profile_id=r.gateway_profile_id,
                adapter_profile_id=r.adapter_profile_id,
                domain_key=r.domain_key,
                status=r.status,
                composite_score=r.composite_score,
                profile_version=r.profile_version,
                evidence_hash=r.evidence_hash,
                semantic_context_hash=r.semantic_context_hash,
                slod_model_version=r.slod_model_version,
                created_at=r.created_at,
            )
            for r in rows
        ],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get("/{gateway_profile_id}", response_model=GatewayAdapterProfileDetail)
async def get_gateway_adapter_profile(
    gateway_profile_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GatewayAdapterProfileDetail:
    row = await session.scalar(
        select(GatewayAdapterProfile).where(GatewayAdapterProfile.gateway_profile_id == gateway_profile_id)
    )
    if row is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="profile not found")
    return GatewayAdapterProfileDetail(
        gateway_profile_id=row.gateway_profile_id,
        adapter_profile_id=row.adapter_profile_id,
        domain_key=row.domain_key,
        status=row.status,
        composite_score=row.composite_score,
        profile_version=row.profile_version,
        evidence_hash=row.evidence_hash,
        semantic_context_hash=row.semantic_context_hash,
        slod_model_version=row.slod_model_version,
        created_at=row.created_at,
        source_run_id=row.source_run_id,
        source_plan_id=row.source_plan_id,
        metadata=_parse_metadata(row.metadata_json),
        updated_at=row.updated_at,
        published_at=row.published_at,
    )


@router.get(
    "/{gateway_profile_id}/activations",
    response_model=list[GatewayAdapterProfileActivationRow],
)
async def list_gateway_adapter_profile_activations(
    gateway_profile_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[GatewayAdapterProfileActivationRow]:
    stmt = (
        select(GatewayAdapterProfileActivation)
        .where(GatewayAdapterProfileActivation.gateway_profile_id == gateway_profile_id)
        .order_by(desc(GatewayAdapterProfileActivation.created_at))
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return [
        GatewayAdapterProfileActivationRow(
            id=r.id,
            domain_key=r.domain_key,
            gateway_profile_id=r.gateway_profile_id,
            status=r.status,
            canary_percent=r.canary_percent,
            previous_gateway_profile_id=r.previous_gateway_profile_id,
            created_at=r.created_at,
            activated_at=r.activated_at,
            promoted_at=r.promoted_at,
            rolled_back_at=r.rolled_back_at,
            metadata=_parse_metadata(r.metadata_json),
        )
        for r in rows
    ]

