"""Stale limit reservation detection and repair (v0.8)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.domain_enums import LimitReservationRepairKind
from app.db.models import GatewayRequest, ProjectGatewayLimitReservation, ProjectUsageWindow
from app.services.project_limit_reservation_service import (
    reconcile_gateway_request,
    release_orphan_limit_reservation,
)
from app.services.request_log_service import finish_request_failure

RepairMode = Literal["dry_run", "apply"]


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

REPAIR_KIND_NO_GATEWAY_REQUEST = LimitReservationRepairKind.NO_GATEWAY_REQUEST.value
REPAIR_KIND_FAILED = LimitReservationRepairKind.GATEWAY_REQUEST_FAILED.value
REPAIR_KIND_COMPLETED_WITHOUT_RECONCILE = (
    LimitReservationRepairKind.COMPLETED_WITHOUT_RECONCILE.value
)
REPAIR_KIND_STARTED_NOT_COMPLETED = LimitReservationRepairKind.STARTED_NOT_COMPLETED.value
REPAIR_KIND_UNKNOWN = LimitReservationRepairKind.UNKNOWN.value

ACTION_RELEASE = "release"
ACTION_RECONCILE_FROM_REQUEST = "reconcile_from_request"
ACTION_HOLD = "hold"
ACTION_MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True, slots=True)
class StaleReservationCandidate:
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


@dataclass(frozen=True, slots=True)
class DailyWindowSnapshot:
    request_count_reserved: int
    request_count_completed: int
    token_count_reserved: int
    token_count_completed: int


@dataclass(frozen=True, slots=True)
class MonthlyWindowSnapshot:
    cost_reserved: float
    cost_completed: float


@dataclass(frozen=True, slots=True)
class ReservationWindowDelta:
    daily_before: DailyWindowSnapshot
    daily_after: DailyWindowSnapshot
    monthly_before: MonthlyWindowSnapshot | None
    monthly_after: MonthlyWindowSnapshot | None


@dataclass(frozen=True, slots=True)
class ReservationRepairResult:
    reservation_id: str
    project_id: str
    repair_kind: str
    action: str
    applied: bool
    message: str
    before: ReservationWindowDelta
    after: ReservationWindowDelta | None


def _dialect_name(session: AsyncSession) -> str:
    return session.get_bind().dialect.name


def _classify_and_recommend(
    *,
    gr: GatewayRequest | None,
    age_seconds: int,
    force_after_seconds: int,
) -> tuple[str, str]:
    if gr is None:
        return REPAIR_KIND_NO_GATEWAY_REQUEST, ACTION_RELEASE

    st = (gr.status or "").lower()
    if st == "failed":
        return REPAIR_KIND_FAILED, ACTION_RECONCILE_FROM_REQUEST
    if st == "completed":
        return REPAIR_KIND_COMPLETED_WITHOUT_RECONCILE, ACTION_RECONCILE_FROM_REQUEST
    if st == "started":
        if gr.completed_at is not None:
            return REPAIR_KIND_UNKNOWN, ACTION_MANUAL_REVIEW
        if age_seconds >= force_after_seconds:
            return REPAIR_KIND_STARTED_NOT_COMPLETED, ACTION_RECONCILE_FROM_REQUEST
        return REPAIR_KIND_STARTED_NOT_COMPLETED, ACTION_MANUAL_REVIEW
    return REPAIR_KIND_UNKNOWN, ACTION_MANUAL_REVIEW


async def _lock_reservation_row(
    session: AsyncSession, reservation_id: str
) -> ProjectGatewayLimitReservation | None:
    dialect = _dialect_name(session)
    stmt = select(ProjectGatewayLimitReservation).where(
        ProjectGatewayLimitReservation.id == reservation_id
    )
    if dialect == "postgresql":
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def _load_gateway_for_reservation(
    session: AsyncSession, reservation_id: str
) -> GatewayRequest | None:
    stmt = select(GatewayRequest).where(GatewayRequest.limit_reservation_id == reservation_id)
    row = (await session.execute(stmt)).scalars().first()
    return row


async def _snap_usage_window(session: AsyncSession, window_id: str) -> ProjectUsageWindow:
    row = await session.get(ProjectUsageWindow, window_id)
    if row is None:
        raise ValueError(f"missing usage window {window_id}")
    return row


def _daily_snap(w: ProjectUsageWindow) -> DailyWindowSnapshot:
    return DailyWindowSnapshot(
        request_count_reserved=w.request_count_reserved,
        request_count_completed=w.request_count_completed,
        token_count_reserved=w.token_count_reserved,
        token_count_completed=w.token_count_completed,
    )


def _monthly_snap(w: ProjectUsageWindow) -> MonthlyWindowSnapshot:
    return MonthlyWindowSnapshot(cost_reserved=w.cost_reserved, cost_completed=w.cost_completed)


async def _build_delta_for_reservation(
    session: AsyncSession, res: ProjectGatewayLimitReservation
) -> ReservationWindowDelta:
    daily = await _snap_usage_window(session, res.daily_window_id)
    db = _daily_snap(daily)
    if res.monthly_window_id:
        monthly = await _snap_usage_window(session, res.monthly_window_id)
        mb = _monthly_snap(monthly)
        return ReservationWindowDelta(
            daily_before=db,
            daily_after=db,
            monthly_before=mb,
            monthly_after=mb,
        )
    return ReservationWindowDelta(
        daily_before=db,
        daily_after=db,
        monthly_before=None,
        monthly_after=None,
    )


def _preview_reconcile_delta(
    res: ProjectGatewayLimitReservation,
    before: ReservationWindowDelta,
    actual_tokens: int,
    actual_cost: float,
) -> ReservationWindowDelta:
    d0 = before.daily_before
    new_daily = DailyWindowSnapshot(
        request_count_reserved=max(0, d0.request_count_reserved - res.request_slots),
        request_count_completed=d0.request_count_completed + res.request_slots,
        token_count_reserved=max(0, d0.token_count_reserved - res.tokens_reserved),
        token_count_completed=d0.token_count_completed + max(0, actual_tokens),
    )
    if before.monthly_before is not None and res.monthly_window_id:
        m0 = before.monthly_before
        new_monthly = MonthlyWindowSnapshot(
            cost_reserved=max(0.0, m0.cost_reserved - res.cost_reserved),
            cost_completed=m0.cost_completed + max(0.0, actual_cost),
        )
        return ReservationWindowDelta(
            daily_before=before.daily_before,
            daily_after=new_daily,
            monthly_before=before.monthly_before,
            monthly_after=new_monthly,
        )
    return ReservationWindowDelta(
        daily_before=before.daily_before,
        daily_after=new_daily,
        monthly_before=None,
        monthly_after=None,
    )


def _preview_release_delta(
    res: ProjectGatewayLimitReservation,
    before: ReservationWindowDelta,
) -> ReservationWindowDelta:
    d0 = before.daily_before
    new_daily = DailyWindowSnapshot(
        request_count_reserved=max(0, d0.request_count_reserved - res.request_slots),
        request_count_completed=d0.request_count_completed,
        token_count_reserved=max(0, d0.token_count_reserved - res.tokens_reserved),
        token_count_completed=d0.token_count_completed,
    )
    if before.monthly_before is not None and res.monthly_window_id:
        m0 = before.monthly_before
        new_monthly = MonthlyWindowSnapshot(
            cost_reserved=max(0.0, m0.cost_reserved - res.cost_reserved),
            cost_completed=m0.cost_completed,
        )
        return ReservationWindowDelta(
            daily_before=before.daily_before,
            daily_after=new_daily,
            monthly_before=before.monthly_before,
            monthly_after=new_monthly,
        )
    return ReservationWindowDelta(
        daily_before=before.daily_before,
        daily_after=new_daily,
        monthly_before=None,
        monthly_after=None,
    )


@dataclass(frozen=True, slots=True)
class StaleReservationsSummary:
    total_count: int
    oldest_age_seconds: int | None


async def count_stale_reservations(
    session: AsyncSession,
    *,
    older_than_seconds: int,
    project_id: str | None,
    now: datetime,
) -> StaleReservationsSummary:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(seconds=older_than_seconds)

    filters = [
        ProjectGatewayLimitReservation.reconciled_at.is_(None),
        ProjectGatewayLimitReservation.created_at <= cutoff,
    ]
    if project_id is not None:
        filters.append(ProjectGatewayLimitReservation.project_id == project_id)

    cnt_stmt = select(func.count()).select_from(ProjectGatewayLimitReservation).where(*filters)
    total = int((await session.execute(cnt_stmt)).scalar_one() or 0)

    oldest_stmt = select(func.min(ProjectGatewayLimitReservation.created_at)).where(*filters)
    min_created = (await session.execute(oldest_stmt)).scalar_one_or_none()
    oldest_age: int | None = None
    if min_created is not None and total > 0:
        oldest_age = max(0, int((now - _as_utc_aware(min_created)).total_seconds()))

    return StaleReservationsSummary(total_count=total, oldest_age_seconds=oldest_age)


async def list_stale_reservations(
    session: AsyncSession,
    *,
    older_than_seconds: int,
    project_id: str | None,
    limit: int,
    now: datetime,
) -> list[StaleReservationCandidate]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(seconds=older_than_seconds)
    force_after = settings.limit_reservation_force_repair_after_seconds

    filters = [
        ProjectGatewayLimitReservation.reconciled_at.is_(None),
        ProjectGatewayLimitReservation.created_at <= cutoff,
    ]
    if project_id is not None:
        filters.append(ProjectGatewayLimitReservation.project_id == project_id)

    stmt = (
        select(ProjectGatewayLimitReservation)
        .where(*filters)
        .order_by(ProjectGatewayLimitReservation.created_at.asc())
        .limit(limit)
    )
    reservations = (await session.execute(stmt)).scalars().all()
    if not reservations:
        return []

    ids = [r.id for r in reservations]
    gr_stmt = select(GatewayRequest).where(GatewayRequest.limit_reservation_id.in_(ids))
    gr_rows = (await session.execute(gr_stmt)).scalars().all()
    gr_by_res: dict[str, GatewayRequest] = {}
    for g in gr_rows:
        if g.limit_reservation_id and g.limit_reservation_id not in gr_by_res:
            gr_by_res[g.limit_reservation_id] = g

    out: list[StaleReservationCandidate] = []
    for res in reservations:
        age_seconds = max(0, int((now - _as_utc_aware(res.created_at)).total_seconds()))
        gr = gr_by_res.get(res.id)
        kind, rec = _classify_and_recommend(
            gr=gr, age_seconds=age_seconds, force_after_seconds=force_after
        )
        out.append(
            StaleReservationCandidate(
                reservation_id=res.id,
                project_id=res.project_id,
                created_at=res.created_at,
                age_seconds=age_seconds,
                daily_window_id=res.daily_window_id,
                monthly_window_id=res.monthly_window_id,
                request_slots=res.request_slots,
                tokens_reserved=res.tokens_reserved,
                cost_reserved=res.cost_reserved,
                gateway_request_id=gr.id if gr else None,
                gateway_request_status=gr.status if gr else None,
                gateway_request_completed_at=gr.completed_at if gr else None,
                repair_kind=kind,
                recommended_action=rec,
            )
        )
    return out


async def repair_stale_reservation(
    session: AsyncSession,
    *,
    reservation_id: str,
    mode: RepairMode,
    now: datetime,
) -> ReservationRepairResult | None:
    """Repair one reservation. Returns ``None`` if reservation row does not exist."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    force_after = settings.limit_reservation_force_repair_after_seconds

    res = await _lock_reservation_row(session, reservation_id)
    if res is None:
        return None

    if res.reconciled_at is not None:
        before = await _build_delta_for_reservation(session, res)
        return ReservationRepairResult(
            reservation_id=res.id,
            project_id=res.project_id,
            repair_kind=REPAIR_KIND_UNKNOWN,
            action="already_reconciled",
            applied=False,
            message="Reservation already reconciled.",
            before=before,
            after=None,
        )

    before = await _build_delta_for_reservation(session, res)
    gr = await _load_gateway_for_reservation(session, reservation_id)
    age_seconds = max(0, int((now - _as_utc_aware(res.created_at)).total_seconds()))
    kind, _rec = _classify_and_recommend(
        gr=gr, age_seconds=age_seconds, force_after_seconds=force_after
    )

    # --- Started but not completed: skip until force age ---
    if kind == REPAIR_KIND_STARTED_NOT_COMPLETED and age_seconds < force_after:
        after = before
        return ReservationRepairResult(
            reservation_id=res.id,
            project_id=res.project_id,
            repair_kind=kind,
            action="repair_skipped",
            applied=False,
            message=(
                f"Request still in progress or awaiting manual review "
                f"(age {age_seconds}s < force threshold {force_after}s)."
            ),
            before=before,
            after=after,
        )

    # --- No gateway request: release only ---
    if kind == REPAIR_KIND_NO_GATEWAY_REQUEST:
        preview = _preview_release_delta(res, before)
        if mode == "dry_run":
            return ReservationRepairResult(
                reservation_id=res.id,
                project_id=res.project_id,
                repair_kind=kind,
                action="release_orphan",
                applied=False,
                message="Would release reserved counters without counting a completed request.",
                before=before,
                after=preview,
            )
        ok = await release_orphan_limit_reservation(session, reservation_id=res.id)
        if not ok:
            return ReservationRepairResult(
                reservation_id=res.id,
                project_id=res.project_id,
                repair_kind=kind,
                action="release_orphan",
                applied=False,
                message="Release skipped (already reconciled or missing reservation).",
                before=before,
                after=None,
            )
        await session.refresh(res)
        after = await _build_delta_for_reservation(session, res)
        return ReservationRepairResult(
            reservation_id=res.id,
            project_id=res.project_id,
            repair_kind=kind,
            action="release_orphan",
            applied=True,
            message="Released reserved counters; marked reservation reconciled.",
            before=before,
            after=after,
        )

    assert gr is not None

    # --- Force-fail stuck started request ---
    if kind == REPAIR_KIND_STARTED_NOT_COMPLETED and age_seconds >= force_after:
        preview_after_fail = _preview_reconcile_delta(res, before, 0, 0.0)
        if mode == "dry_run":
            return ReservationRepairResult(
                reservation_id=res.id,
                project_id=res.project_id,
                repair_kind=kind,
                action="force_fail_and_reconcile",
                applied=False,
                message="Would mark gateway request failed and reconcile reservation as failed.",
                before=before,
                after=preview_after_fail,
            )
        await finish_request_failure(
            session,
            gr,
            latency_ms=0,
            error_code="stale_reservation_repair",
            error_message="Marked failed by stale reservation repair (incomplete request).",
        )
        await reconcile_gateway_request(
            session,
            reservation_id=res.id,
            actual_tokens=0,
            actual_cost=0.0,
            status="failed",
        )
        res2 = await _lock_reservation_row(session, reservation_id)
        assert res2 is not None
        after = await _build_delta_for_reservation(session, res2)
        return ReservationRepairResult(
            reservation_id=res.id,
            project_id=res.project_id,
            repair_kind=kind,
            action="force_fail_and_reconcile",
            applied=True,
            message="Marked request failed and reconciled reservation.",
            before=before,
            after=after,
        )

    # --- Failed gateway request ---
    if kind == REPAIR_KIND_FAILED:
        preview = _preview_reconcile_delta(res, before, 0, 0.0)
        if mode == "dry_run":
            return ReservationRepairResult(
                reservation_id=res.id,
                project_id=res.project_id,
                repair_kind=kind,
                action="reconcile_failed_request",
                applied=False,
                message="Would reconcile as failed (zero tokens/cost).",
                before=before,
                after=preview,
            )
        await reconcile_gateway_request(
            session,
            reservation_id=res.id,
            actual_tokens=0,
            actual_cost=0.0,
            status="failed",
        )
        res2 = await session.get(ProjectGatewayLimitReservation, res.id)
        assert res2 is not None
        after = await _build_delta_for_reservation(session, res2)
        return ReservationRepairResult(
            reservation_id=res.id,
            project_id=res.project_id,
            repair_kind=kind,
            action="reconcile_failed_request",
            applied=True,
            message="Reconciled failed gateway request.",
            before=before,
            after=after,
        )

    # --- Completed without reconcile ---
    if kind == REPAIR_KIND_COMPLETED_WITHOUT_RECONCILE:
        actual_tokens = int(gr.total_tokens or 0)
        actual_cost = float(gr.estimated_cost or 0.0)
        preview = _preview_reconcile_delta(res, before, actual_tokens, actual_cost)
        if mode == "dry_run":
            return ReservationRepairResult(
                reservation_id=res.id,
                project_id=res.project_id,
                repair_kind=kind,
                action="reconcile_completed_request",
                applied=False,
                message="Would reconcile using logged tokens and estimated cost.",
                before=before,
                after=preview,
            )
        await reconcile_gateway_request(
            session,
            reservation_id=res.id,
            actual_tokens=actual_tokens,
            actual_cost=actual_cost,
            status="completed",
        )
        res2 = await session.get(ProjectGatewayLimitReservation, res.id)
        assert res2 is not None
        after = await _build_delta_for_reservation(session, res2)
        return ReservationRepairResult(
            reservation_id=res.id,
            project_id=res.project_id,
            repair_kind=kind,
            action="reconcile_completed_request",
            applied=True,
            message="Reconciled completed gateway request.",
            before=before,
            after=after,
        )

    preview = before
    return ReservationRepairResult(
        reservation_id=res.id,
        project_id=res.project_id,
        repair_kind=kind,
        action="repair_skipped",
        applied=False,
        message="Unknown or unsupported repair classification; no automatic repair applied.",
        before=before,
        after=preview,
    )
