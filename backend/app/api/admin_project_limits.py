"""Admin project limit endpoints (M8A/M8C)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.models import Project, ProjectLimit
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.services.project_limits_service import get_project_limit_usage

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
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
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

