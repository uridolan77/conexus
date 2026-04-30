"""Admin project limit endpoints (M8A/M8C)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.core.config import settings
from app.db.models import Project, ProjectLimit
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.services.audit_service import log_admin_action
from app.services.project_limits_service import get_project_limit_usage
from app.services.project_limit_reservations_query import load_project_limit_reservations_snapshot
from app.services.project_limit_reservation_repair_service import (
    ReservationRepairResult,
    ReservationWindowDelta,
    count_stale_reservations,
    list_stale_reservations,
    repair_stale_reservation,
)

router = APIRouter(prefix="/admin/projects", tags=["admin"])

LimitMode = Literal["disabled", "soft", "hard"]


class ProjectLimitsView(BaseModel):
    project_id: str
    limit_mode: LimitMode
    monthly_cost_limit: float | None
    daily_request_limit: int | None
    daily_token_limit: int | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProjectLimitsPutBody(BaseModel):
    limit_mode: LimitMode = "disabled"
    monthly_cost_limit: float | None = Field(default=None, ge=0)
    daily_request_limit: int | None = Field(default=None, ge=0)
    daily_token_limit: int | None = Field(default=None, ge=0)


class _ProjectLimitsUsageDaily(BaseModel):
    window: Literal["utc_day"] = "utc_day"
    start_at: datetime
    reset_at: datetime
    request_count: int
    total_tokens: int


class _ProjectLimitsUsageMonthly(BaseModel):
    window: Literal["utc_month"] = "utc_month"
    start_at: datetime
    reset_at: datetime
    estimated_cost: float
    currency: Literal["USD"] = "USD"


class ProjectLimitsUsageView(BaseModel):
    project_id: str
    now: datetime
    daily: _ProjectLimitsUsageDaily
    monthly: _ProjectLimitsUsageMonthly


class _ProjectLimitsReservationsDaily(BaseModel):
    window_start: datetime
    window_end: datetime
    request_count_reserved: int
    request_count_completed: int
    token_count_reserved: int
    token_count_completed: int


class _ProjectLimitsReservationsMonthly(BaseModel):
    window_start: datetime
    window_end: datetime
    cost_reserved: float
    cost_completed: float


class ProjectLimitsReservationsView(BaseModel):
    project_id: str
    now: datetime
    daily: _ProjectLimitsReservationsDaily | None
    monthly: _ProjectLimitsReservationsMonthly | None


async def _project_or_404(session: AsyncSession, project_id: str) -> Project:
    row = await session.get(Project, project_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="project not found"
        )
    return row


def _default_limits(project_id: str) -> ProjectLimitsView:
    return ProjectLimitsView(
        project_id=project_id,
        limit_mode="disabled",
        monthly_cost_limit=None,
        daily_request_limit=None,
        daily_token_limit=None,
        created_at=None,
        updated_at=None,
    )


def _to_view(row: ProjectLimit) -> ProjectLimitsView:
    return ProjectLimitsView(
        project_id=row.project_id,
        limit_mode=row.limit_mode,  # type: ignore[arg-type]
        monthly_cost_limit=row.monthly_cost_limit,
        daily_request_limit=row.daily_request_limit,
        daily_token_limit=row.daily_token_limit,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class _DailyWindowSnapshotView(BaseModel):
    request_count_reserved: int
    request_count_completed: int
    token_count_reserved: int
    token_count_completed: int


class _MonthlyWindowSnapshotView(BaseModel):
    cost_reserved: float
    cost_completed: float


class ReservationWindowDeltaView(BaseModel):
    daily_before: _DailyWindowSnapshotView
    daily_after: _DailyWindowSnapshotView
    monthly_before: _MonthlyWindowSnapshotView | None
    monthly_after: _MonthlyWindowSnapshotView | None


class StaleReservationItemView(BaseModel):
    reservation_id: str
    project_id: str
    created_at: datetime
    age_seconds: int
    daily_window_id: str
    monthly_window_id: str | None
    request_slots: int
    tokens_reserved: int
    cost_reserved: float
    gateway_request_id: str | None
    gateway_request_status: str | None
    gateway_request_completed_at: datetime | None
    repair_kind: str
    recommended_action: str


class StaleReservationsListView(BaseModel):
    now: datetime
    older_than_seconds: int
    total_count: int
    oldest_age_seconds: int | None
    items: list[StaleReservationItemView]


class ReservationRepairBody(BaseModel):
    reason: str | None = None


class ReservationRepairResponse(BaseModel):
    reservation_id: str
    project_id: str
    repair_kind: str
    action: str
    applied: bool
    message: str
    before: ReservationWindowDeltaView
    after: ReservationWindowDeltaView | None


def _delta_to_view(d: ReservationWindowDelta) -> ReservationWindowDeltaView:
    return ReservationWindowDeltaView(
        daily_before=_DailyWindowSnapshotView(
            request_count_reserved=d.daily_before.request_count_reserved,
            request_count_completed=d.daily_before.request_count_completed,
            token_count_reserved=d.daily_before.token_count_reserved,
            token_count_completed=d.daily_before.token_count_completed,
        ),
        daily_after=_DailyWindowSnapshotView(
            request_count_reserved=d.daily_after.request_count_reserved,
            request_count_completed=d.daily_after.request_count_completed,
            token_count_reserved=d.daily_after.token_count_reserved,
            token_count_completed=d.daily_after.token_count_completed,
        ),
        monthly_before=(
            _MonthlyWindowSnapshotView(
                cost_reserved=d.monthly_before.cost_reserved,
                cost_completed=d.monthly_before.cost_completed,
            )
            if d.monthly_before is not None
            else None
        ),
        monthly_after=(
            _MonthlyWindowSnapshotView(
                cost_reserved=d.monthly_after.cost_reserved,
                cost_completed=d.monthly_after.cost_completed,
            )
            if d.monthly_after is not None
            else None
        ),
    )


def _repair_audit_metadata(
    result: ReservationRepairResult, *, reason: str | None
) -> dict:
    return {
        "reservation_id": result.reservation_id,
        "project_id": result.project_id,
        "repair_kind": result.repair_kind,
        "action": result.action,
        "reason": reason,
        "applied": result.applied,
        "before": _delta_to_view(result.before).model_dump(),
        "after": _delta_to_view(result.after).model_dump() if result.after else None,
    }


def _repair_to_response(result: ReservationRepairResult) -> ReservationRepairResponse:
    return ReservationRepairResponse(
        reservation_id=result.reservation_id,
        project_id=result.project_id,
        repair_kind=result.repair_kind,
        action=result.action,
        applied=result.applied,
        message=result.message,
        before=_delta_to_view(result.before),
        after=_delta_to_view(result.after) if result.after else None,
    )


@router.get("/limits/reservations/stale", response_model=StaleReservationsListView)
async def get_stale_limit_reservations(
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
    project_id: str | None = None,
    older_than_seconds: int | None = Query(default=None, ge=60),
    limit: int = Query(default=100, ge=1, le=500),
) -> StaleReservationsListView:
    _ = admin
    now = datetime.now(timezone.utc)
    threshold = (
        older_than_seconds
        if older_than_seconds is not None
        else settings.limit_reservation_stale_after_seconds
    )
    summary = await count_stale_reservations(
        session, older_than_seconds=threshold, project_id=project_id, now=now
    )
    raw = await list_stale_reservations(
        session,
        older_than_seconds=threshold,
        project_id=project_id,
        limit=limit,
        now=now,
    )
    items = [
        StaleReservationItemView(
            reservation_id=c.reservation_id,
            project_id=c.project_id,
            created_at=c.created_at,
            age_seconds=c.age_seconds,
            daily_window_id=c.daily_window_id,
            monthly_window_id=c.monthly_window_id,
            request_slots=c.request_slots,
            tokens_reserved=c.tokens_reserved,
            cost_reserved=c.cost_reserved,
            gateway_request_id=c.gateway_request_id,
            gateway_request_status=c.gateway_request_status,
            gateway_request_completed_at=c.gateway_request_completed_at,
            repair_kind=c.repair_kind,
            recommended_action=c.recommended_action,
        )
        for c in raw
    ]
    return StaleReservationsListView(
        now=now,
        older_than_seconds=threshold,
        total_count=summary.total_count,
        oldest_age_seconds=summary.oldest_age_seconds,
        items=items,
    )


@router.post(
    "/limits/reservations/{reservation_id}/repair/dry-run",
    response_model=ReservationRepairResponse,
)
async def post_repair_limit_reservation_dry_run(
    reservation_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReservationRepairResponse:
    now = datetime.now(timezone.utc)
    result = await repair_stale_reservation(
        session, reservation_id=reservation_id, mode="dry_run", now=now
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reservation not found")
    await log_admin_action(
        session,
        actor=admin,
        action="project.limit_reservation.repair_dry_run",
        resource_type="project_gateway_limit_reservation",
        resource_id=reservation_id,
        metadata=_repair_audit_metadata(result, reason=None),
    )
    return _repair_to_response(result)


@router.post("/limits/reservations/{reservation_id}/repair", response_model=ReservationRepairResponse)
async def post_repair_limit_reservation(
    reservation_id: str,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
    body: ReservationRepairBody | None = Body(default=None),
) -> ReservationRepairResponse:
    reason = body.reason if body else None
    now = datetime.now(timezone.utc)
    result = await repair_stale_reservation(
        session, reservation_id=reservation_id, mode="apply", now=now
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reservation not found")

    if result.action == "already_reconciled" or not result.applied:
        audit_action = "project.limit_reservation.repair_skipped"
    else:
        audit_action = "project.limit_reservation.repair_applied"
    await log_admin_action(
        session,
        actor=admin,
        action=audit_action,
        resource_type="project_gateway_limit_reservation",
        resource_id=reservation_id,
        metadata=_repair_audit_metadata(result, reason=reason),
    )
    return _repair_to_response(result)


@router.get("/{project_id}/limits", response_model=ProjectLimitsView)
async def get_project_limits(
    project_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectLimitsView:
    await _project_or_404(session, project_id)
    stmt = select(ProjectLimit).where(ProjectLimit.project_id == project_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return _default_limits(project_id)
    return _to_view(row)


@router.put("/{project_id}/limits", response_model=ProjectLimitsView)
async def put_project_limits(
    project_id: str,
    body: ProjectLimitsPutBody,
    admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectLimitsView:
    await _project_or_404(session, project_id)
    stmt = select(ProjectLimit).where(ProjectLimit.project_id == project_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = ProjectLimit(project_id=project_id)
        session.add(row)
        await session.flush()

    row.limit_mode = body.limit_mode
    row.monthly_cost_limit = body.monthly_cost_limit
    row.daily_request_limit = body.daily_request_limit
    row.daily_token_limit = body.daily_token_limit
    await session.flush()
    await log_admin_action(
        session,
        actor=admin,
        action="project_limits.update",
        resource_type="project_limit",
        resource_id=row.project_id,
        metadata={
            "limit_mode": row.limit_mode,
            "monthly_cost_limit": row.monthly_cost_limit,
            "daily_request_limit": row.daily_request_limit,
            "daily_token_limit": row.daily_token_limit,
        },
    )
    return _to_view(row)


@router.get("/{project_id}/limits/usage", response_model=ProjectLimitsUsageView)
async def get_project_limits_usage(
    project_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectLimitsUsageView:
    await _project_or_404(session, project_id)
    now = datetime.now(timezone.utc)
    usage = await get_project_limit_usage(session, project_id=project_id, now=now)
    return ProjectLimitsUsageView(
        project_id=project_id,
        now=now,
        daily=_ProjectLimitsUsageDaily(
            start_at=usage.day_start,
            reset_at=usage.day_end,
            request_count=usage.daily_request_count,
            total_tokens=usage.daily_total_tokens,
        ),
        monthly=_ProjectLimitsUsageMonthly(
            start_at=usage.month_start,
            reset_at=usage.month_end,
            estimated_cost=usage.monthly_estimated_cost,
        ),
    )


@router.get("/{project_id}/limits/reservations", response_model=ProjectLimitsReservationsView)
async def get_project_limits_reservations(
    project_id: str,
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectLimitsReservationsView:
    await _project_or_404(session, project_id)
    now = datetime.now(timezone.utc)
    snap = await load_project_limit_reservations_snapshot(session, project_id=project_id, now=now)
    daily = (
        _ProjectLimitsReservationsDaily(
            window_start=snap.daily.window_start,
            window_end=snap.daily.window_end,
            request_count_reserved=snap.daily.request_count_reserved,
            request_count_completed=snap.daily.request_count_completed,
            token_count_reserved=snap.daily.token_count_reserved,
            token_count_completed=snap.daily.token_count_completed,
        )
        if snap.daily is not None
        else None
    )
    monthly = (
        _ProjectLimitsReservationsMonthly(
            window_start=snap.monthly.window_start,
            window_end=snap.monthly.window_end,
            cost_reserved=snap.monthly.cost_reserved,
            cost_completed=snap.monthly.cost_completed,
        )
        if snap.monthly is not None
        else None
    )
    return ProjectLimitsReservationsView(
        project_id=project_id,
        now=now,
        daily=daily,
        monthly=monthly,
    )

