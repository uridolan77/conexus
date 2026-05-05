"""Internal adapter profile registry endpoints.

These endpoints are intended for conexus.adaptation and other trusted callers.
They must never be called from browsers.
"""

from __future__ import annotations

import hmac
import math
import uuid
from datetime import datetime, timedelta, timezone
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.domain_enums import (
    GatewayAdapterProfileActivationStatus,
    GatewayAdapterProfileStatus,
    GatewayRequestStatus,
)
from app.db.models import GatewayAdapterProfile, GatewayAdapterProfileActivation
from app.db.session import get_session
from app.services.audit_service import log_admin_action

router = APIRouter(prefix="/internal/adapter-profiles", tags=["internal"])


def _is_adapter_activation_unique_violation(exc: IntegrityError) -> bool:
    raw = str(exc.orig or exc).lower()
    return "uq_gw_profile_activation_domain" in raw or (
        "unique" in raw and "gateway_adapter_profile_activations" in raw
    )


async def _flush_adapter_activation_or_conflict(session: AsyncSession) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        if not _is_adapter_activation_unique_violation(exc):
            raise
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="adapter profile activation conflict for this domain",
        ) from exc


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_gateway_profile_id() -> str:
    return f"gw-{uuid.uuid4().hex}"


def require_internal_adapter_api_key(
    internal_key: Annotated[str | None, Header(alias="X-Internal-Api-Key")] = None,
) -> None:
    if not settings.adapter_profile_registry_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="adapter profile registry disabled")
    expected = (settings.internal_adapter_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="internal adapter api key is not configured",
        )
    provided = (internal_key or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal api key")


def get_internal_actor(
    internal_actor: Annotated[str | None, Header(alias="X-Internal-Actor")] = None,
) -> str | None:
    actor = (internal_actor or "").strip()
    return actor or None


class RegisterAdapterProfileBody(BaseModel):
    adapterProfileId: str = Field(..., min_length=1)
    domainKey: str = Field(..., min_length=1)
    runId: str | None = None
    planId: str | None = None
    compositeScore: float | None = None
    evidenceHash: str | None = None
    semanticContextHash: str | None = None
    slodModelVersion: str | None = None
    profileVersion: str | None = None
    metadata: dict[str, Any] | None = None


class RegisterAdapterProfileResponse(BaseModel):
    gatewayProfileId: str
    status: str


@router.post(
    "/register",
    response_model=RegisterAdapterProfileResponse,
    dependencies=[Depends(require_internal_adapter_api_key)],
)
async def register_adapter_profile(
    body: RegisterAdapterProfileBody,
    session: Annotated[AsyncSession, Depends(get_session)],
    internal_actor: Annotated[str | None, Depends(get_internal_actor)],
) -> RegisterAdapterProfileResponse:
    adapter_profile_id = body.adapterProfileId.strip()
    domain_key = body.domainKey.strip()
    if not domain_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="domainKey is required")
    if not adapter_profile_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="adapterProfileId is required")

    existing = await session.scalar(
        select(GatewayAdapterProfile).where(GatewayAdapterProfile.adapter_profile_id == adapter_profile_id)
    )
    if existing is not None:
        return RegisterAdapterProfileResponse(
            gatewayProfileId=existing.gateway_profile_id,
            status=existing.status,
        )

    row = GatewayAdapterProfile(
        gateway_profile_id=_new_gateway_profile_id(),
        adapter_profile_id=adapter_profile_id,
        domain_key=domain_key,
        profile_version=body.profileVersion,
        status=GatewayAdapterProfileStatus.REGISTERED,
        source_run_id=body.runId,
        source_plan_id=body.planId,
        composite_score=body.compositeScore,
        evidence_hash=body.evidenceHash,
        semantic_context_hash=body.semanticContextHash,
        slod_model_version=body.slodModelVersion,
        metadata_json=None if body.metadata is None else json.dumps(body.metadata, separators=(",", ":"), sort_keys=True),
        created_at=_utcnow(),
        updated_at=_utcnow(),
        published_at=None,
    )
    session.add(row)
    try:
        await session.flush()
    except BaseException as exc:
        if not isinstance(exc, IntegrityError):
            raise
        # Race: another request inserted the same adapter_profile_id concurrently.
        await session.rollback()
        existing = None
        # The winning transaction may not be committed yet; retry briefly.
        for _ in range(100):
            existing = await session.scalar(
                select(GatewayAdapterProfile).where(
                    GatewayAdapterProfile.adapter_profile_id == adapter_profile_id
                )
            )
            if existing is not None:
                break
            import asyncio

            await asyncio.sleep(0.01)
        if existing is None:
            raise
        return RegisterAdapterProfileResponse(
            gatewayProfileId=existing.gateway_profile_id,
            status=existing.status,
        )
    await log_admin_action(
        session,
        actor=None,
        action="gateway.adapter_profile.registered",
        resource_type="gateway_adapter_profile",
        resource_id=row.gateway_profile_id,
        metadata={
            "adapter_profile_id": adapter_profile_id,
            "domain_key": domain_key,
            "internal_actor": internal_actor,
        },
    )
    return RegisterAdapterProfileResponse(gatewayProfileId=row.gateway_profile_id, status=row.status)


class ActivateCanaryBody(BaseModel):
    canaryPercent: int = Field(..., ge=1, le=50)
    metadata: dict[str, Any] | None = None


class ActivationResponse(BaseModel):
    domainKey: str
    gatewayProfileId: str
    status: str
    canaryPercent: int | None = None
    previousGatewayProfileId: str | None = None


async def _get_profile_or_404(session: AsyncSession, *, gateway_profile_id: str) -> GatewayAdapterProfile:
    row = await session.scalar(
        select(GatewayAdapterProfile).where(GatewayAdapterProfile.gateway_profile_id == gateway_profile_id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="gateway profile not found")
    return row


@router.post(
    "/{gatewayProfileId}/activate-canary",
    response_model=ActivationResponse,
    dependencies=[Depends(require_internal_adapter_api_key)],
)
async def activate_canary(
    gatewayProfileId: str,
    body: ActivateCanaryBody,
    session: Annotated[AsyncSession, Depends(get_session)],
    internal_actor: Annotated[str | None, Depends(get_internal_actor)],
) -> ActivationResponse:
    profile = await _get_profile_or_404(session, gateway_profile_id=gatewayProfileId)
    domain_key = profile.domain_key

    existing_canary = await session.scalar(
        select(GatewayAdapterProfileActivation).where(
            GatewayAdapterProfileActivation.domain_key == domain_key,
            GatewayAdapterProfileActivation.status == GatewayAdapterProfileActivationStatus.CANARY,
        ).order_by(desc(GatewayAdapterProfileActivation.created_at))
    )
    if existing_canary is not None and existing_canary.gateway_profile_id != gatewayProfileId:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="domain already has a canary profile")

    if existing_canary is None:
        row = GatewayAdapterProfileActivation(
            domain_key=domain_key,
            gateway_profile_id=gatewayProfileId,
            status=GatewayAdapterProfileActivationStatus.CANARY,
            canary_percent=body.canaryPercent,
            previous_gateway_profile_id=None,
            created_at=_utcnow(),
            activated_at=_utcnow(),
            promoted_at=None,
            rolled_back_at=None,
            metadata_json=None
            if body.metadata is None
            else json.dumps(body.metadata, separators=(",", ":"), sort_keys=True),
        )
        session.add(row)
        await _flush_adapter_activation_or_conflict(session)
        existing_canary = row
    else:
        existing_canary.canary_percent = body.canaryPercent
        existing_canary.activated_at = _utcnow()
        existing_canary.metadata_json = (
            None
            if body.metadata is None
            else json.dumps(body.metadata, separators=(",", ":"), sort_keys=True)
        )
        await _flush_adapter_activation_or_conflict(session)

    await log_admin_action(
        session,
        actor=None,
        action="gateway.adapter_profile.canary_activated",
        resource_type="gateway_adapter_profile_activation",
        resource_id=gatewayProfileId,
        metadata={
            "domain_key": domain_key,
            "canary_percent": existing_canary.canary_percent,
            "internal_actor": internal_actor,
        },
    )
    return ActivationResponse(
        domainKey=domain_key,
        gatewayProfileId=gatewayProfileId,
        status=GatewayAdapterProfileActivationStatus.CANARY,
        canaryPercent=existing_canary.canary_percent,
    )


@router.post(
    "/{gatewayProfileId}/promote",
    response_model=ActivationResponse,
    dependencies=[Depends(require_internal_adapter_api_key)],
)
async def promote(
    gatewayProfileId: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    internal_actor: Annotated[str | None, Depends(get_internal_actor)],
) -> ActivationResponse:
    profile = await _get_profile_or_404(session, gateway_profile_id=gatewayProfileId)
    domain_key = profile.domain_key

    active = await session.scalar(
        select(GatewayAdapterProfileActivation).where(
            GatewayAdapterProfileActivation.domain_key == domain_key,
            GatewayAdapterProfileActivation.status == GatewayAdapterProfileActivationStatus.ACTIVE,
        ).order_by(desc(GatewayAdapterProfileActivation.created_at))
    )
    previous_id = active.gateway_profile_id if active is not None else None
    if active is not None and active.gateway_profile_id == gatewayProfileId:
        return ActivationResponse(
            domainKey=domain_key,
            gatewayProfileId=gatewayProfileId,
            status=GatewayAdapterProfileActivationStatus.ACTIVE,
            previousGatewayProfileId=active.previous_gateway_profile_id,
        )

    if active is not None:
        active.status = GatewayAdapterProfileActivationStatus.RETIRED
        await session.flush()

    # Preserve canary history: if the promoted profile was previously canary, mark it Promoted.
    # If a different canary exists, retire it (do not delete).
    canaries = (
        await session.execute(
            select(GatewayAdapterProfileActivation).where(
                GatewayAdapterProfileActivation.domain_key == domain_key,
                GatewayAdapterProfileActivation.status == GatewayAdapterProfileActivationStatus.CANARY,
            )
        )
    ).scalars().all()
    for c in canaries:
        if c.gateway_profile_id == gatewayProfileId:
            c.status = GatewayAdapterProfileActivationStatus.PROMOTED
            c.promoted_at = _utcnow()
        else:
            c.status = GatewayAdapterProfileActivationStatus.RETIRED
        await session.flush()

    row = GatewayAdapterProfileActivation(
        domain_key=domain_key,
        gateway_profile_id=gatewayProfileId,
        status=GatewayAdapterProfileActivationStatus.ACTIVE,
        canary_percent=None,
        previous_gateway_profile_id=previous_id,
        created_at=_utcnow(),
        activated_at=_utcnow(),
        promoted_at=_utcnow(),
        rolled_back_at=None,
        metadata_json=None,
    )
    session.add(row)
    await _flush_adapter_activation_or_conflict(session)
    await log_admin_action(
        session,
        actor=None,
        action="gateway.adapter_profile.promoted",
        resource_type="gateway_adapter_profile_activation",
        resource_id=gatewayProfileId,
        metadata={
            "domain_key": domain_key,
            "previous_gateway_profile_id": previous_id,
            "internal_actor": internal_actor,
        },
    )

    return ActivationResponse(
        domainKey=domain_key,
        gatewayProfileId=gatewayProfileId,
        status=GatewayAdapterProfileActivationStatus.ACTIVE,
        previousGatewayProfileId=previous_id,
    )


@router.post(
    "/{gatewayProfileId}/rollback",
    response_model=ActivationResponse,
    dependencies=[Depends(require_internal_adapter_api_key)],
)
async def rollback(
    gatewayProfileId: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    internal_actor: Annotated[str | None, Depends(get_internal_actor)],
) -> ActivationResponse:
    profile = await _get_profile_or_404(session, gateway_profile_id=gatewayProfileId)
    domain_key = profile.domain_key

    active = await session.scalar(
        select(GatewayAdapterProfileActivation).where(
            GatewayAdapterProfileActivation.domain_key == domain_key,
            GatewayAdapterProfileActivation.status == GatewayAdapterProfileActivationStatus.ACTIVE,
        ).order_by(desc(GatewayAdapterProfileActivation.created_at))
    )
    if active is None or active.gateway_profile_id != gatewayProfileId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="active profile not found")
    if not active.previous_gateway_profile_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="no previous profile to roll back to")

    previous_id = active.previous_gateway_profile_id
    active.status = GatewayAdapterProfileActivationStatus.ROLLED_BACK
    active.rolled_back_at = _utcnow()
    await session.flush()

    # Preserve history: retire any current canary rows.
    canaries = (
        await session.execute(
            select(GatewayAdapterProfileActivation).where(
                GatewayAdapterProfileActivation.domain_key == domain_key,
                GatewayAdapterProfileActivation.status == GatewayAdapterProfileActivationStatus.CANARY,
            )
        )
    ).scalars().all()
    for c in canaries:
        c.status = GatewayAdapterProfileActivationStatus.RETIRED
    await session.flush()

    row = GatewayAdapterProfileActivation(
        domain_key=domain_key,
        gateway_profile_id=previous_id,
        status=GatewayAdapterProfileActivationStatus.ACTIVE,
        canary_percent=None,
        previous_gateway_profile_id=None,
        created_at=_utcnow(),
        activated_at=_utcnow(),
        promoted_at=None,
        rolled_back_at=None,
        metadata_json=None,
    )
    session.add(row)
    await _flush_adapter_activation_or_conflict(session)
    await log_admin_action(
        session,
        actor=None,
        action="gateway.adapter_profile.rolled_back",
        resource_type="gateway_adapter_profile_activation",
        resource_id=gatewayProfileId,
        metadata={
            "domain_key": domain_key,
            "restored_gateway_profile_id": previous_id,
            "internal_actor": internal_actor,
        },
    )

    return ActivationResponse(
        domainKey=domain_key,
        gatewayProfileId=previous_id,
        status=GatewayAdapterProfileActivationStatus.ACTIVE,
    )


class ObservabilityResponse(BaseModel):
    gatewayProfileId: str
    windowStart: str
    windowEnd: str
    requestCount: int
    errorRate: float | None
    latencyP95Ms: int | None
    costPerAnswer: float | None
    citationFailureRate: float | None = None
    refusalRate: float | None = None
    userNegativeFeedbackRate: float | None = None


def _parse_window_param(value: str | None) -> datetime | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    # Accept "Z" suffix for UTC.
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid since/until") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get(
    "/{gatewayProfileId}/observability",
    response_model=ObservabilityResponse,
    dependencies=[Depends(require_internal_adapter_api_key)],
)
async def get_observability(
    gatewayProfileId: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    since: str | None = None,
    until: str | None = None,
) -> ObservabilityResponse:
    if not settings.adapter_profile_observability_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="observability disabled")

    await _get_profile_or_404(session, gateway_profile_id=gatewayProfileId)
    window_end = _parse_window_param(until) or _utcnow()
    window_start = _parse_window_param(since) or (window_end - timedelta(hours=24))
    if window_start > window_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="since must be <= until")

    from app.db.models import GatewayRequest  # local import

    result = await session.execute(
        select(GatewayRequest.status, GatewayRequest.latency_ms, GatewayRequest.estimated_cost).where(
            GatewayRequest.gateway_profile_id == gatewayProfileId,
            GatewayRequest.created_at >= window_start,
            GatewayRequest.created_at <= window_end,
        )
    )
    records = list(result.all())
    request_count = len(records)
    if request_count == 0:
        return ObservabilityResponse(
            gatewayProfileId=gatewayProfileId,
            windowStart=window_start.isoformat(),
            windowEnd=window_end.isoformat(),
            requestCount=0,
            errorRate=0.0,
            latencyP95Ms=None,
            costPerAnswer=None,
        )

    error_count = sum(
        1 for (status_value, _lat, _cost) in records if status_value == GatewayRequestStatus.FAILED
    )
    error_rate = error_count / request_count

    latencies = sorted(
        [lat for (_st, lat, _c) in records if lat is not None and _st == GatewayRequestStatus.COMPLETED]
    )
    latency_p95: int | None = None
    if latencies:
        idx = max(0, math.ceil(0.95 * len(latencies)) - 1)
        latency_p95 = int(latencies[idx])

    completed_costs = [
        c for (st, _lat, c) in records if st == GatewayRequestStatus.COMPLETED and c is not None
    ]
    completed_count = sum(1 for (st, _lat, _c) in records if st == GatewayRequestStatus.COMPLETED)
    cost_per_answer: float | None = None
    if completed_count > 0 and completed_costs:
        cost_per_answer = float(sum(completed_costs) / completed_count)

    return ObservabilityResponse(
        gatewayProfileId=gatewayProfileId,
        windowStart=window_start.isoformat(),
        windowEnd=window_end.isoformat(),
        requestCount=request_count,
        errorRate=error_rate,
        latencyP95Ms=latency_p95,
        costPerAnswer=cost_per_answer,
        citationFailureRate=None,
        refusalRate=None,
        userNegativeFeedbackRate=None,
    )

