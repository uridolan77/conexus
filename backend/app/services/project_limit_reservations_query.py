"""Read current UTC usage window rows for admin / BO visibility."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProjectUsageWindow
from app.services.project_limits_service import _utc_day_bounds, _utc_month_bounds


@dataclass(frozen=True, slots=True)
class DailyUsageWindowSnapshot:
    window_start: datetime
    window_end: datetime
    request_count_reserved: int
    request_count_completed: int
    token_count_reserved: int
    token_count_completed: int


@dataclass(frozen=True, slots=True)
class MonthlyUsageWindowSnapshot:
    window_start: datetime
    window_end: datetime
    cost_reserved: float
    cost_completed: float


@dataclass(frozen=True, slots=True)
class ProjectLimitReservationsSnapshot:
    project_id: str
    daily: DailyUsageWindowSnapshot | None
    monthly: MonthlyUsageWindowSnapshot | None


async def load_project_limit_reservations_snapshot(
    session: AsyncSession,
    *,
    project_id: str,
    now: datetime,
) -> ProjectLimitReservationsSnapshot:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    day_start, day_end = _utc_day_bounds(now)
    month_start, month_end = _utc_month_bounds(now)

    daily_stmt = select(ProjectUsageWindow).where(
        ProjectUsageWindow.project_id == project_id,
        ProjectUsageWindow.window_kind == "daily",
        ProjectUsageWindow.window_start_utc == day_start,
    )
    daily_row = (await session.execute(daily_stmt)).scalar_one_or_none()
    daily_snap: DailyUsageWindowSnapshot | None = None
    if daily_row is not None:
        daily_snap = DailyUsageWindowSnapshot(
            window_start=daily_row.window_start_utc,
            window_end=daily_row.window_end_utc,
            request_count_reserved=daily_row.request_count_reserved,
            request_count_completed=daily_row.request_count_completed,
            token_count_reserved=daily_row.token_count_reserved,
            token_count_completed=daily_row.token_count_completed,
        )

    monthly_stmt = select(ProjectUsageWindow).where(
        ProjectUsageWindow.project_id == project_id,
        ProjectUsageWindow.window_kind == "monthly",
        ProjectUsageWindow.window_start_utc == month_start,
    )
    monthly_row = (await session.execute(monthly_stmt)).scalar_one_or_none()
    monthly_snap: MonthlyUsageWindowSnapshot | None = None
    if monthly_row is not None:
        monthly_snap = MonthlyUsageWindowSnapshot(
            window_start=monthly_row.window_start_utc,
            window_end=monthly_row.window_end_utc,
            cost_reserved=monthly_row.cost_reserved,
            cost_completed=monthly_row.cost_completed,
        )

    return ProjectLimitReservationsSnapshot(
        project_id=project_id,
        daily=daily_snap,
        monthly=monthly_snap,
    )
