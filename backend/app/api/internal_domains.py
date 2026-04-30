"""Internal domain-level routing state endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.internal_adapter_profiles import require_internal_adapter_api_key
from app.db.models import GatewayAdapterProfileActivation
from app.db.session import get_session

router = APIRouter(prefix="/internal/domains", tags=["internal"])


class ActiveProfileResponse(BaseModel):
    domainKey: str
    gatewayProfileId: str
    status: str


@router.get(
    "/{domainKey}/active-profile",
    response_model=ActiveProfileResponse,
    dependencies=[Depends(require_internal_adapter_api_key)],
)
async def get_active_profile(
    domainKey: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActiveProfileResponse:
    domain = domainKey.strip()
    if not domain:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="domainKey is required")
    row = await session.scalar(
        select(GatewayAdapterProfileActivation).where(
            GatewayAdapterProfileActivation.domain_key == domain,
            GatewayAdapterProfileActivation.status == "Active",
        ).order_by(desc(GatewayAdapterProfileActivation.created_at))
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no active profile for domain")
    return ActiveProfileResponse(domainKey=domain, gatewayProfileId=row.gateway_profile_id, status=row.status)

