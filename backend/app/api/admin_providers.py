"""Admin provider config endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import ProviderConfig
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.services.provider_config_service import (
    ProviderTestResult,
    create_provider_config,
    list_provider_configs,
    revoke_provider_config,
    test_provider_config,
)
from app.services.audit_service import log_admin_action
from app.llm.gateway_router import DEFAULT_PRIMARY_MODEL

router = APIRouter(prefix="/admin/providers", tags=["admin"])


class ProviderConfigBody(BaseModel):
    provider: Literal["openai", "anthropic"]
    api_key: str = Field(..., min_length=1)
    label: str | None = Field(default=None, max_length=120)


class ProviderConfigView(BaseModel):
    id: str
    provider: str
    label: str | None
    key_mask: str
    is_active: bool
    revoked_at: datetime | None
    last_test_status: str | None
    last_test_error: str | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProviderTestBody(BaseModel):
    model: str | None = None


class ProviderTestView(BaseModel):
    status: str
    latency_ms: int
    error: str | None


def _to_view(row: ProviderConfig) -> ProviderConfigView:
    return ProviderConfigView(
        id=row.id,
        provider=row.provider,
        label=row.label,
        key_mask=row.key_mask,
        is_active=row.is_active,
        revoked_at=row.revoked_at,
        last_test_status=row.last_test_status,
        last_test_error=row.last_test_error,
        last_tested_at=row.last_tested_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _default_model(provider: str) -> str:
    if provider == "openai":
        return "gpt-4o-mini"
    return DEFAULT_PRIMARY_MODEL


@router.get("", response_model=list[ProviderConfigView])
async def get_provider_configs(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProviderConfigView]:
    rows = await list_provider_configs(session)
    return [_to_view(r) for r in rows]


@router.post(
    "",
    response_model=ProviderConfigView,
    status_code=status.HTTP_201_CREATED,
)
async def add_provider_config(
    body: ProviderConfigBody,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderConfigView:
    row = await create_provider_config(
        session,
        provider=body.provider,
        api_key=body.api_key,
        label=body.label,
    )
    await log_admin_action(
        session,
        actor=admin,
        action="provider.create",
        resource_type="provider_config",
        resource_id=row.id,
        metadata={
            "provider": row.provider,
            "label": row.label,
            "key_mask": row.key_mask,
        },
    )
    return _to_view(row)


@router.post("/{provider_id}/revoke", response_model=ProviderConfigView)
async def revoke_provider(
    provider_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderConfigView:
    row = await session.get(ProviderConfig, provider_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="provider config not found",
        )
    await revoke_provider_config(session, row)
    await log_admin_action(
        session,
        actor=admin,
        action="provider.revoke",
        resource_type="provider_config",
        resource_id=row.id,
        metadata={
            "provider": row.provider,
            "label": row.label,
            "key_mask": row.key_mask,
        },
    )
    return _to_view(row)


@router.post("/{provider_id}/test", response_model=ProviderTestView)
async def test_provider(
    provider_id: str,
    body: ProviderTestBody,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderTestView:
    row = await session.get(ProviderConfig, provider_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="provider config not found",
        )
    if not row.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider config is revoked",
        )
    model = body.model or _default_model(row.provider)
    result: ProviderTestResult = await test_provider_config(session, row, model=model)
    await log_admin_action(
        session,
        actor=admin,
        action="provider.test",
        resource_type="provider_config",
        resource_id=row.id,
        metadata={
            "provider": row.provider,
            "model": model,
            "status": result.status,
            "latency_ms": result.latency_ms,
            "error": result.error,
        },
    )
    return ProviderTestView(
        status=result.status,
        latency_ms=result.latency_ms,
        error=result.error,
    )
