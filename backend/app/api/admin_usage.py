"""Admin usage analytics endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import GatewayRequest, Project
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession

router = APIRouter(prefix="/admin/usage", tags=["admin"])

Window = Literal["24h", "7d", "30d"]


@dataclass(slots=True)
class TimeBounds:
    window: Window
    created_from: datetime
    created_to: datetime


class UsageMetrics(BaseModel):
    total_requests: int
    completed_requests: int
    failed_requests: int
    success_rate: float
    fallback_count: int
    fallback_rate: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_cost: float
    avg_latency_ms: float | None


class UsageSummaryResponse(UsageMetrics):
    window: Window
    created_from: datetime
    created_to: datetime
    currency: Literal["USD"] = "USD"


class ProjectUsageRow(UsageMetrics):
    project_id: str | None
    project_name: str | None


class ProjectUsageResponse(BaseModel):
    window: Window
    created_from: datetime
    created_to: datetime
    currency: Literal["USD"] = "USD"
    items: list[ProjectUsageRow]


def _window_start(window: Window, now: datetime) -> datetime:
    if window == "24h":
        return now - timedelta(hours=24)
    if window == "7d":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


def _time_bounds(
    *,
    window: Window,
    created_from: datetime | None,
    created_to: datetime | None,
) -> TimeBounds:
    now = datetime.now(timezone.utc)
    upper = created_to or now
    lower = created_from or _window_start(window, upper)
    if lower > upper:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="created_from must be before created_to",
        )
    return TimeBounds(window=window, created_from=lower, created_to=upper)


def _metric_columns() -> list:
    return [
        func.count(GatewayRequest.id).label("total_requests"),
        func.coalesce(
            func.sum(case((GatewayRequest.status == "completed", 1), else_=0)),
            0,
        ).label("completed_requests"),
        func.coalesce(
            func.sum(case((GatewayRequest.status == "failed", 1), else_=0)),
            0,
        ).label("failed_requests"),
        func.coalesce(
            func.sum(case((GatewayRequest.fallback_used.is_(True), 1), else_=0)),
            0,
        ).label("fallback_count"),
        func.coalesce(func.sum(GatewayRequest.prompt_tokens), 0).label(
            "total_prompt_tokens"
        ),
        func.coalesce(func.sum(GatewayRequest.completion_tokens), 0).label(
            "total_completion_tokens"
        ),
        func.coalesce(func.sum(GatewayRequest.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(GatewayRequest.estimated_cost), 0.0).label(
            "estimated_cost"
        ),
        func.avg(GatewayRequest.latency_ms).label("avg_latency_ms"),
    ]


def _apply_time_bounds(stmt: Select, bounds: TimeBounds) -> Select:
    return stmt.where(
        GatewayRequest.created_at >= bounds.created_from,
        GatewayRequest.created_at <= bounds.created_to,
    )


def _metrics_from_mapping(row: object) -> UsageMetrics:
    mapping = row._mapping  # type: ignore[attr-defined]
    total_requests = int(mapping["total_requests"] or 0)
    completed_requests = int(mapping["completed_requests"] or 0)
    failed_requests = int(mapping["failed_requests"] or 0)
    fallback_count = int(mapping["fallback_count"] or 0)
    return UsageMetrics(
        total_requests=total_requests,
        completed_requests=completed_requests,
        failed_requests=failed_requests,
        success_rate=completed_requests / total_requests if total_requests else 0.0,
        fallback_count=fallback_count,
        fallback_rate=fallback_count / total_requests if total_requests else 0.0,
        total_prompt_tokens=int(mapping["total_prompt_tokens"] or 0),
        total_completion_tokens=int(mapping["total_completion_tokens"] or 0),
        total_tokens=int(mapping["total_tokens"] or 0),
        estimated_cost=float(mapping["estimated_cost"] or 0.0),
        avg_latency_ms=(
            float(mapping["avg_latency_ms"])
            if mapping["avg_latency_ms"] is not None
            else None
        ),
    )


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
    window: Annotated[Window, Query()] = "30d",
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> UsageSummaryResponse:
    bounds = _time_bounds(
        window=window,
        created_from=created_from,
        created_to=created_to,
    )
    stmt = _apply_time_bounds(select(*_metric_columns()), bounds)
    row = (await session.execute(stmt)).one()
    metrics = _metrics_from_mapping(row)
    return UsageSummaryResponse(
        **metrics.model_dump(),
        window=bounds.window,
        created_from=bounds.created_from,
        created_to=bounds.created_to,
    )


@router.get("/by-project", response_model=ProjectUsageResponse)
async def get_usage_by_project(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
    window: Annotated[Window, Query()] = "30d",
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> ProjectUsageResponse:
    bounds = _time_bounds(
        window=window,
        created_from=created_from,
        created_to=created_to,
    )
    stmt = (
        select(
            GatewayRequest.project_id.label("project_id"),
            Project.name.label("project_name"),
            *_metric_columns(),
        )
        .outerjoin(Project, GatewayRequest.project_id == Project.id)
        .group_by(GatewayRequest.project_id, Project.name)
        .order_by(func.coalesce(func.sum(GatewayRequest.estimated_cost), 0.0).desc())
    )
    stmt = _apply_time_bounds(stmt, bounds)
    rows = (await session.execute(stmt)).all()
    return ProjectUsageResponse(
        window=bounds.window,
        created_from=bounds.created_from,
        created_to=bounds.created_to,
        items=[
            ProjectUsageRow(
                project_id=row._mapping["project_id"],
                project_name=row._mapping["project_name"],
                **_metrics_from_mapping(row).model_dump(),
            )
            for row in rows
        ],
    )
