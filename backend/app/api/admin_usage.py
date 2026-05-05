"""Admin usage analytics endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Integer, Select, case, cast, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.sqltypes import DateTime

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


@dataclass(slots=True)
class _MetricAccumulator:
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    fallback_count: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    latency_sum_ms: int = 0
    latency_count: int = 0


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


class ProviderUsageRow(UsageMetrics):
    provider: str | None


class ProviderUsageResponse(BaseModel):
    window: Window
    created_from: datetime
    created_to: datetime
    currency: Literal["USD"] = "USD"
    items: list[ProviderUsageRow]


class UsageTimeseriesPoint(UsageMetrics):
    bucket_start: datetime
    bucket_end: datetime


class UsageTimeseriesResponse(BaseModel):
    window: Window
    created_from: datetime
    created_to: datetime
    interval: Literal["hour", "day"]
    currency: Literal["USD"] = "USD"
    items: list[UsageTimeseriesPoint]


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


def _metrics_from_accumulator(accumulator: _MetricAccumulator) -> UsageMetrics:
    total_requests = accumulator.total_requests
    return UsageMetrics(
        total_requests=total_requests,
        completed_requests=accumulator.completed_requests,
        failed_requests=accumulator.failed_requests,
        success_rate=(
            accumulator.completed_requests / total_requests if total_requests else 0.0
        ),
        fallback_count=accumulator.fallback_count,
        fallback_rate=accumulator.fallback_count / total_requests if total_requests else 0.0,
        total_prompt_tokens=accumulator.total_prompt_tokens,
        total_completion_tokens=accumulator.total_completion_tokens,
        total_tokens=accumulator.total_tokens,
        estimated_cost=accumulator.estimated_cost,
        avg_latency_ms=(
            accumulator.latency_sum_ms / accumulator.latency_count
            if accumulator.latency_count
            else None
        ),
    )


def _timeseries_interval(window: Window) -> tuple[Literal["hour", "day"], timedelta]:
    if window == "24h":
        return "hour", timedelta(hours=1)
    return "day", timedelta(days=1)


def _empty_buckets(
    bounds: TimeBounds,
    step: timedelta,
) -> list[tuple[datetime, datetime, _MetricAccumulator]]:
    buckets: list[tuple[datetime, datetime, _MetricAccumulator]] = []
    bucket_start = bounds.created_from
    while bucket_start < bounds.created_to:
        bucket_end = min(bucket_start + step, bounds.created_to)
        buckets.append((bucket_start, bucket_end, _MetricAccumulator()))
        bucket_start = bucket_end
    if not buckets:
        buckets.append((bounds.created_from, bounds.created_to, _MetricAccumulator()))
    return buckets


def _apply_time_bounds(stmt: Select, bounds: TimeBounds) -> Select:
    return stmt.where(
        GatewayRequest.created_at >= bounds.created_from,
        GatewayRequest.created_at <= bounds.created_to,
    )


def _timeseries_bucket_idx(bounds: TimeBounds, step: timedelta):
    """SQL bucket index aligned with ``_bucket_index`` (origin = bounds.created_from)."""
    step_sec = max(1, int(step.total_seconds()))
    origin = bounds.created_from
    epoch_row = func.extract("epoch", GatewayRequest.created_at)
    epoch_origin = func.extract("epoch", literal(origin, type_=DateTime(timezone=True)))
    return cast(
        func.floor((epoch_row - epoch_origin) / literal(step_sec)),
        Integer,
    ).label("bucket_idx")


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


@router.get("/by-provider", response_model=ProviderUsageResponse)
async def get_usage_by_provider(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
    window: Annotated[Window, Query()] = "30d",
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> ProviderUsageResponse:
    bounds = _time_bounds(
        window=window,
        created_from=created_from,
        created_to=created_to,
    )
    stmt = (
        select(
            GatewayRequest.provider.label("provider"),
            *_metric_columns(),
        )
        .group_by(GatewayRequest.provider)
        .order_by(func.coalesce(func.sum(GatewayRequest.estimated_cost), 0.0).desc())
    )
    stmt = _apply_time_bounds(stmt, bounds)
    rows = (await session.execute(stmt)).all()
    return ProviderUsageResponse(
        window=bounds.window,
        created_from=bounds.created_from,
        created_to=bounds.created_to,
        items=[
            ProviderUsageRow(
                provider=row._mapping["provider"],
                **_metrics_from_mapping(row).model_dump(),
            )
            for row in rows
        ],
    )


@router.get("/timeseries", response_model=UsageTimeseriesResponse)
async def get_usage_timeseries(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
    window: Annotated[Window, Query()] = "30d",
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> UsageTimeseriesResponse:
    bounds = _time_bounds(
        window=window,
        created_from=created_from,
        created_to=created_to,
    )
    interval, step = _timeseries_interval(window)
    buckets = _empty_buckets(bounds, step)
    n = len(buckets)
    bucket_idx = _timeseries_bucket_idx(bounds, step)
    stmt = _apply_time_bounds(
        select(bucket_idx, *_metric_columns()).select_from(GatewayRequest),
        bounds,
    ).group_by(bucket_idx)
    agg_rows = (await session.execute(stmt)).all()
    idx_metrics: dict[int, UsageMetrics] = {}
    for row in agg_rows:
        raw_idx = int(row._mapping["bucket_idx"] or 0)
        idx = max(0, min(raw_idx, n - 1))
        idx_metrics[idx] = _metrics_from_mapping(row)
    return UsageTimeseriesResponse(
        window=bounds.window,
        created_from=bounds.created_from,
        created_to=bounds.created_to,
        interval=interval,
        items=[
            UsageTimeseriesPoint(
                bucket_start=bucket_start,
                bucket_end=bucket_end,
                **(
                    idx_metrics[i].model_dump()
                    if i in idx_metrics
                    else _metrics_from_accumulator(acc).model_dump()
                ),
            )
            for i, (bucket_start, bucket_end, acc) in enumerate(buckets)
        ],
    )
