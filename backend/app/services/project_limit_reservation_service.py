"""DB-backed project limit reservations (strict daily requests; token/cost approximate)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.domain_enums import ProjectLimitMode
from app.db.models import (
    GatewayRequest,
    ProjectGatewayLimitReservation,
    ProjectLimit,
    ProjectUsageWindow,
)
from app.llm.gateway_router import get_model_alias_config
from app.llm.pricing import estimate_hard_monthly_reservation_cost_usd
from app.services.project_limits_service import (
    LimitBlock,
    _utc_day_bounds,
    _utc_month_bounds,
)

logger = logging.getLogger(__name__)


async def _legacy_daily_request_count(
    session: AsyncSession,
    *,
    project_id: str,
    day_start: datetime,
    day_end: datetime,
) -> int:
    stmt = (
        select(func.count(GatewayRequest.id))
        .where(
            GatewayRequest.project_id == project_id,
            GatewayRequest.created_at >= day_start,
            GatewayRequest.created_at < day_end,
        )
        .select_from(GatewayRequest)
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def _legacy_daily_token_sum(
    session: AsyncSession,
    *,
    project_id: str,
    day_start: datetime,
    day_end: datetime,
) -> int:
    stmt = (
        select(func.coalesce(func.sum(GatewayRequest.total_tokens), 0))
        .where(
            GatewayRequest.project_id == project_id,
            GatewayRequest.created_at >= day_start,
            GatewayRequest.created_at < day_end,
        )
        .select_from(GatewayRequest)
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def _legacy_monthly_cost_sum(
    session: AsyncSession,
    *,
    project_id: str,
    month_start: datetime,
    month_end: datetime,
) -> float:
    stmt = (
        select(func.coalesce(func.sum(GatewayRequest.estimated_cost), 0.0))
        .where(
            GatewayRequest.project_id == project_id,
            GatewayRequest.created_at >= month_start,
            GatewayRequest.created_at < month_end,
        )
        .select_from(GatewayRequest)
    )
    return float((await session.execute(stmt)).scalar_one() or 0.0)


@dataclass(frozen=True, slots=True)
class LimitReservationResult:
    allowed: bool
    reservation_id: str | None
    block: LimitBlock | None


def _dialect_name(session: AsyncSession) -> str:
    return session.get_bind().dialect.name


def _reserved_tokens(
    requested_max_tokens: int, estimated_prompt_tokens: int | None
) -> int:
    mt = max(0, requested_max_tokens)
    if estimated_prompt_tokens is not None:
        return mt + max(0, estimated_prompt_tokens)
    return mt


async def _lock_window_by_id(session: AsyncSession, window_id: str) -> ProjectUsageWindow:
    dialect = _dialect_name(session)
    stmt = select(ProjectUsageWindow).where(ProjectUsageWindow.id == window_id)
    if dialect == "postgresql":
        stmt = stmt.with_for_update()
    row = (await session.execute(stmt)).scalar_one()
    return row


async def _get_or_create_window(
    session: AsyncSession,
    *,
    project_id: str,
    window_kind: str,
    window_start: datetime,
    window_end: datetime,
) -> ProjectUsageWindow:
    dialect = _dialect_name(session)
    tbl = ProjectUsageWindow.__table__
    for _attempt in range(16):
        stmt = select(ProjectUsageWindow).where(
            ProjectUsageWindow.project_id == project_id,
            ProjectUsageWindow.window_kind == window_kind,
            ProjectUsageWindow.window_start_utc == window_start,
        )
        if dialect == "postgresql":
            stmt = stmt.with_for_update()
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is not None:
            return row

        wid = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        row_values = {
            "id": wid,
            "project_id": project_id,
            "window_kind": window_kind,
            "window_start_utc": window_start,
            "window_end_utc": window_end,
            "request_count_reserved": 0,
            "request_count_completed": 0,
            "token_count_reserved": 0,
            "token_count_completed": 0,
            "cost_reserved": 0.0,
            "cost_completed": 0.0,
            "created_at": now,
            "updated_at": now,
        }
        conflict_cols = [tbl.c.project_id, tbl.c.window_kind, tbl.c.window_start_utc]
        if dialect == "sqlite":
            ins = sqlite_insert(tbl).values(**row_values).on_conflict_do_nothing(
                index_elements=conflict_cols
            )
        else:
            ins = pg_insert(tbl).values(**row_values).on_conflict_do_nothing(
                index_elements=conflict_cols
            )
        await session.execute(ins)
        await session.flush()

        stmt = select(ProjectUsageWindow).where(
            ProjectUsageWindow.project_id == project_id,
            ProjectUsageWindow.window_kind == window_kind,
            ProjectUsageWindow.window_start_utc == window_start,
        )
        if dialect == "postgresql":
            stmt = stmt.with_for_update()
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is not None:
            return row

    raise RuntimeError("failed to allocate project_usage_windows row")


async def reserve_gateway_request(
    session: AsyncSession,
    *,
    project_id: str,
    limits: ProjectLimit,
    model: str,
    requested_max_tokens: int,
    estimated_prompt_tokens: int | None,
    now: datetime,
) -> LimitReservationResult:
    if limits.limit_mode != ProjectLimitMode.HARD:
        return LimitReservationResult(True, None, None)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    day_start, day_end = _utc_day_bounds(now)
    month_start, month_end = _utc_month_bounds(now)

    reserved_tokens = _reserved_tokens(requested_max_tokens, estimated_prompt_tokens)

    estimated_cost: float | None = None
    if limits.monthly_cost_limit is not None:
        estimated_cost = estimate_hard_monthly_reservation_cost_usd(
            model,
            reserved_tokens,
            alias_cfg=get_model_alias_config(),
        )
        if estimated_cost is None:
            return LimitReservationResult(
                False,
                None,
                LimitBlock(
                    error_code="pricing_unavailable_for_hard_cost_limit",
                    error_message=(
                        "Monthly cost limit is enabled but this model is not in the "
                        "pricing table; configure pricing or relax limits."
                    ),
                    limit_type="monthly_cost_limit",
                    current_value=0.0,
                    limit_value=float(limits.monthly_cost_limit),
                    window="utc_month",
                    reset_at=month_end,
                ),
            )

    daily = await _get_or_create_window(
        session,
        project_id=project_id,
        window_kind="daily",
        window_start=day_start,
        window_end=day_end,
    )

    if settings.use_legacy_hard_limit_gateway_fallbacks:
        legacy_requests = await _legacy_daily_request_count(
            session, project_id=project_id, day_start=day_start, day_end=day_end
        )
        legacy_tokens = await _legacy_daily_token_sum(
            session, project_id=project_id, day_start=day_start, day_end=day_end
        )
        legacy_cost = await _legacy_monthly_cost_sum(
            session, project_id=project_id, month_start=month_start, month_end=month_end
        )
    else:
        legacy_requests = 0
        legacy_tokens = 0
        legacy_cost = 0.0

    if limits.daily_request_limit is not None:
        if legacy_requests + daily.request_count_reserved >= limits.daily_request_limit:
            return LimitReservationResult(
                False,
                None,
                LimitBlock(
                    error_code="daily_request_limit_exceeded",
                    error_message="Daily request limit exceeded for this project.",
                    limit_type="daily_request_limit",
                    current_value=float(legacy_requests + daily.request_count_reserved),
                    limit_value=float(limits.daily_request_limit),
                    window="utc_day",
                    reset_at=day_end,
                ),
            )

    if limits.daily_token_limit is not None:
        committed_tokens = legacy_tokens + daily.token_count_reserved
        if committed_tokens + reserved_tokens > limits.daily_token_limit:
            return LimitReservationResult(
                False,
                None,
                LimitBlock(
                    error_code="daily_token_limit_exceeded",
                    error_message="Daily token limit exceeded for this project.",
                    limit_type="daily_token_limit",
                    current_value=float(committed_tokens),
                    limit_value=float(limits.daily_token_limit),
                    window="utc_day",
                    reset_at=day_end,
                ),
            )

    monthly: ProjectUsageWindow | None = None
    cost_to_reserve = float(estimated_cost or 0.0)
    if limits.monthly_cost_limit is not None:
        monthly = await _get_or_create_window(
            session,
            project_id=project_id,
            window_kind="monthly",
            window_start=month_start,
            window_end=month_end,
        )
        committed_cost = legacy_cost + monthly.cost_reserved
        if committed_cost + cost_to_reserve > limits.monthly_cost_limit:
            return LimitReservationResult(
                False,
                None,
                LimitBlock(
                    error_code="monthly_cost_limit_exceeded",
                    error_message="Monthly cost limit exceeded for this project.",
                    limit_type="monthly_cost_limit",
                    current_value=float(committed_cost),
                    limit_value=float(limits.monthly_cost_limit),
                    window="utc_month",
                    reset_at=month_end,
                ),
            )

    daily.request_count_reserved += 1
    daily.token_count_reserved += reserved_tokens
    if monthly is not None:
        monthly.cost_reserved += cost_to_reserve

    res = ProjectGatewayLimitReservation(
        project_id=project_id,
        daily_window_id=daily.id,
        monthly_window_id=monthly.id if monthly is not None else None,
        request_slots=1,
        tokens_reserved=reserved_tokens,
        cost_reserved=cost_to_reserve,
    )
    session.add(res)
    await session.flush()

    return LimitReservationResult(True, res.id, None)


async def reconcile_gateway_request(
    session: AsyncSession,
    *,
    reservation_id: str,
    actual_tokens: int,
    actual_cost: float,
    status: str,
) -> None:
    _ = status
    dialect = _dialect_name(session)
    stmt = select(ProjectGatewayLimitReservation).where(
        ProjectGatewayLimitReservation.id == reservation_id
    )
    if dialect == "postgresql":
        stmt = stmt.with_for_update()
    res = (await session.execute(stmt)).scalar_one_or_none()
    if res is None:
        logger.warning("reconcile_missing_reservation reservation_id=%s", reservation_id)
        return
    if res.reconciled_at is not None:
        return

    window_ids = [res.daily_window_id]
    if res.monthly_window_id:
        window_ids.append(res.monthly_window_id)
    window_ids.sort()

    windows: dict[str, ProjectUsageWindow] = {}
    for wid in window_ids:
        windows[wid] = await _lock_window_by_id(session, wid)

    daily = windows[res.daily_window_id]
    daily.request_count_reserved = max(0, daily.request_count_reserved - res.request_slots)
    daily.request_count_completed += res.request_slots
    daily.token_count_reserved = max(0, daily.token_count_reserved - res.tokens_reserved)
    daily.token_count_completed += max(0, actual_tokens)

    if res.monthly_window_id:
        monthly = windows[res.monthly_window_id]
        monthly.cost_reserved = max(0.0, monthly.cost_reserved - res.cost_reserved)
        monthly.cost_completed += max(0.0, actual_cost)

    res.reconciled_at = datetime.now(timezone.utc)
    await session.flush()


async def release_orphan_limit_reservation(
    session: AsyncSession,
    *,
    reservation_id: str,
) -> bool:
    """Release reserved daily/monthly counters without incrementing completed requests.

    Used when a reservation row exists but no gateway request was ever started
    (process crashed after reserve, before ``start_request``).
    """
    dialect = _dialect_name(session)
    stmt = select(ProjectGatewayLimitReservation).where(
        ProjectGatewayLimitReservation.id == reservation_id
    )
    if dialect == "postgresql":
        stmt = stmt.with_for_update()
    res = (await session.execute(stmt)).scalar_one_or_none()
    if res is None:
        return False
    if res.reconciled_at is not None:
        return False

    window_ids = [res.daily_window_id]
    if res.monthly_window_id:
        window_ids.append(res.monthly_window_id)
    window_ids.sort()

    windows: dict[str, ProjectUsageWindow] = {}
    for wid in window_ids:
        windows[wid] = await _lock_window_by_id(session, wid)

    daily = windows[res.daily_window_id]
    daily.request_count_reserved = max(0, daily.request_count_reserved - res.request_slots)
    daily.token_count_reserved = max(0, daily.token_count_reserved - res.tokens_reserved)

    if res.monthly_window_id:
        monthly = windows[res.monthly_window_id]
        monthly.cost_reserved = max(0.0, monthly.cost_reserved - res.cost_reserved)

    res.reconciled_at = datetime.now(timezone.utc)
    await session.flush()
    return True
