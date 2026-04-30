"""Admin endpoints for Conexus gateway adapter profile runtime state.

These endpoints are consumed by the BO. They must not require internal API keys.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import GatewayAdapterProfile, GatewayAdapterProfileActivation, GatewayRequest
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.services.admin_permissions_service import ADAPTATION_VIEW, require_adaptation_permission

router = APIRouter(prefix="/admin/adapter-profiles", tags=["admin"])


class RuntimeObservability(BaseModel):
    requestCount: int
    errorRate: float | None
    latencyP95Ms: int | None
    costPerAnswer: float | None


class AdapterProfileRuntimeState(BaseModel):
    adapterProfileId: str
    registered: bool
    gatewayProfileId: str | None = None
    registrationStatus: str | None = None
    domainKey: str | None = None
    activeGatewayProfileId: str | None = None
    canaryGatewayProfileId: str | None = None
    canaryPercent: int | None = None
    last24h: RuntimeObservability | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get(
    "/{adapterProfileId}/runtime-state",
    response_model=AdapterProfileRuntimeState,
)
async def get_runtime_state(
    adapterProfileId: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    _perm: Annotated[None, Depends(require_adaptation_permission(ADAPTATION_VIEW))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdapterProfileRuntimeState:
    adapter_profile_id = adapterProfileId.strip()
    row = await session.scalar(
        select(GatewayAdapterProfile).where(GatewayAdapterProfile.adapter_profile_id == adapter_profile_id)
    )
    if row is None:
        return AdapterProfileRuntimeState(adapterProfileId=adapter_profile_id, registered=False)

    domain = row.domain_key
    active = await session.scalar(
        select(GatewayAdapterProfileActivation).where(
            GatewayAdapterProfileActivation.domain_key == domain,
            GatewayAdapterProfileActivation.status == "Active",
        ).order_by(desc(GatewayAdapterProfileActivation.created_at))
    )
    canary = await session.scalar(
        select(GatewayAdapterProfileActivation).where(
            GatewayAdapterProfileActivation.domain_key == domain,
            GatewayAdapterProfileActivation.status == "Canary",
        ).order_by(desc(GatewayAdapterProfileActivation.created_at))
    )

    last24h = None
    window_end = _utcnow()
    window_start = window_end - timedelta(hours=24)
    req_rows = (
        await session.execute(
            select(GatewayRequest.status, GatewayRequest.latency_ms, GatewayRequest.estimated_cost).where(
                GatewayRequest.gateway_profile_id == row.gateway_profile_id,
                GatewayRequest.created_at >= window_start,
                GatewayRequest.created_at <= window_end,
            )
        )
    ).all()
    if req_rows:
        request_count = len(req_rows)
        error_count = sum(1 for (st, _lat, _cost) in req_rows if st == "failed")
        latencies = sorted([lat for (st, lat, _c) in req_rows if st == "completed" and lat is not None])
        latency_p95 = None
        if latencies:
            idx = max(0, math.ceil(0.95 * len(latencies)) - 1)
            latency_p95 = int(latencies[idx])
        completed_costs = [c for (st, _lat, c) in req_rows if st == "completed" and c is not None]
        completed_count = sum(1 for (st, _lat, _c) in req_rows if st == "completed")
        cost_per_answer = None
        if completed_count > 0 and completed_costs:
            cost_per_answer = float(sum(completed_costs) / completed_count)
        last24h = RuntimeObservability(
            requestCount=request_count,
            errorRate=error_count / request_count if request_count else None,
            latencyP95Ms=latency_p95,
            costPerAnswer=cost_per_answer,
        )

    return AdapterProfileRuntimeState(
        adapterProfileId=adapter_profile_id,
        registered=True,
        gatewayProfileId=row.gateway_profile_id,
        registrationStatus=row.status,
        domainKey=row.domain_key,
        activeGatewayProfileId=None if active is None else active.gateway_profile_id,
        canaryGatewayProfileId=None if canary is None else canary.gateway_profile_id,
        canaryPercent=None if canary is None else canary.canary_percent,
        last24h=last24h,
    )

