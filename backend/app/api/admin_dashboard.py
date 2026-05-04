"""Admin dashboard summary endpoint for BO home."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import GatewayRequest, Project
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession

router = APIRouter(prefix="/admin/dashboard", tags=["admin"])


class DashboardLatestError(BaseModel):
    request_id: str
    project_id: str | None
    project_name: str | None
    requested_model: str
    provider: str | None
    model: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class DashboardSummary(BaseModel):
    requests_today: int
    success_rate: float
    failed_requests: int
    average_latency_ms: float | None
    estimated_cost_today: float
    latest_errors: list[DashboardLatestError]


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DashboardSummary:
    today_start = _today_start_utc()
    metrics_stmt = select(
        func.count(GatewayRequest.id).label("requests_today"),
        func.coalesce(
            func.sum(case((GatewayRequest.status == "completed", 1), else_=0)),
            0,
        ).label("completed_requests"),
        func.coalesce(
            func.sum(case((GatewayRequest.status == "failed", 1), else_=0)),
            0,
        ).label("failed_requests"),
        func.avg(GatewayRequest.latency_ms).label("average_latency_ms"),
        func.coalesce(func.sum(GatewayRequest.estimated_cost), 0.0).label(
            "estimated_cost_today"
        ),
    ).where(GatewayRequest.created_at >= today_start)
    metrics = (await session.execute(metrics_stmt)).one()._mapping

    requests_today = int(metrics["requests_today"] or 0)
    completed_requests = int(metrics["completed_requests"] or 0)
    failed_requests = int(metrics["failed_requests"] or 0)
    latest_errors_stmt = (
        select(GatewayRequest, Project.name.label("project_name"))
        .outerjoin(Project, GatewayRequest.project_id == Project.id)
        .where(GatewayRequest.status == "failed")
        .order_by(GatewayRequest.created_at.desc())
        .limit(5)
    )
    latest_error_rows = (await session.execute(latest_errors_stmt)).all()

    return DashboardSummary(
        requests_today=requests_today,
        success_rate=completed_requests / requests_today if requests_today else 0.0,
        failed_requests=failed_requests,
        average_latency_ms=(
            float(metrics["average_latency_ms"])
            if metrics["average_latency_ms"] is not None
            else None
        ),
        estimated_cost_today=float(metrics["estimated_cost_today"] or 0.0),
        latest_errors=[
            DashboardLatestError(
                request_id=row.request_id,
                project_id=row.project_id,
                project_name=project_name,
                requested_model=row.requested_model,
                provider=row.provider,
                model=row.model,
                error_code=row.error_code,
                error_message=row.error_message,
                created_at=row.created_at,
            )
            for row, project_name in latest_error_rows
        ],
    )
