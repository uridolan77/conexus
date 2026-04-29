"""Project limit lookup + enforcement helpers (M8A)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GatewayRequest, ProjectLimit


@dataclass(frozen=True, slots=True)
class LimitBlock:
    error_code: str
    error_message: str


def _utc_day_bounds(now: datetime) -> tuple[datetime, datetime]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _utc_month_bounds(now: datetime) -> tuple[datetime, datetime]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return start, end


async def get_project_limits(
    session: AsyncSession, *, project_id: str
) -> ProjectLimit | None:
    stmt = select(ProjectLimit).where(ProjectLimit.project_id == project_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def check_hard_limits(
    session: AsyncSession,
    *,
    project_id: str,
    limits: ProjectLimit,
    now: datetime,
) -> LimitBlock | None:
    """Return a LimitBlock if *limits* are exceeded, else None.

    Semantics:
    - Daily request limit counts *all* gateway_requests rows (including failed).
    - Token and cost sums ignore NULLs via COALESCE(SUM(...), 0).
    - Windows use UTC boundaries.
    """

    if limits.limit_mode != "hard":
        return None

    day_start, day_end = _utc_day_bounds(now)
    month_start, month_end = _utc_month_bounds(now)

    if limits.daily_request_limit is not None:
        stmt = (
            select(func.count(GatewayRequest.id))
            .where(
                GatewayRequest.project_id == project_id,
                GatewayRequest.created_at >= day_start,
                GatewayRequest.created_at < day_end,
            )
            .select_from(GatewayRequest)
        )
        count = int((await session.execute(stmt)).scalar_one() or 0)
        if count >= limits.daily_request_limit:
            return LimitBlock(
                error_code="daily_request_limit_exceeded",
                error_message="Daily request limit exceeded for this project.",
            )

    if limits.daily_token_limit is not None:
        stmt = (
            select(func.coalesce(func.sum(GatewayRequest.total_tokens), 0))
            .where(
                GatewayRequest.project_id == project_id,
                GatewayRequest.created_at >= day_start,
                GatewayRequest.created_at < day_end,
            )
            .select_from(GatewayRequest)
        )
        total_tokens = int((await session.execute(stmt)).scalar_one() or 0)
        if total_tokens >= limits.daily_token_limit:
            return LimitBlock(
                error_code="daily_token_limit_exceeded",
                error_message="Daily token limit exceeded for this project.",
            )

    if limits.monthly_cost_limit is not None:
        stmt = (
            select(func.coalesce(func.sum(GatewayRequest.estimated_cost), 0.0))
            .where(
                GatewayRequest.project_id == project_id,
                GatewayRequest.created_at >= month_start,
                GatewayRequest.created_at < month_end,
            )
            .select_from(GatewayRequest)
        )
        estimated_cost = float((await session.execute(stmt)).scalar_one() or 0.0)
        if estimated_cost >= limits.monthly_cost_limit:
            return LimitBlock(
                error_code="monthly_cost_limit_exceeded",
                error_message="Monthly cost limit exceeded for this project.",
            )

    return None

