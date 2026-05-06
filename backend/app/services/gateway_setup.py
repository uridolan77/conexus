"""Reservation, adapter resolution, and gateway request-log startup (shared sync/stream)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.domain_enums import (
    GatewayAdaptationMode,
    GatewayAdapterProfileActivationStatus,
    GatewayRequestStatus,
    ProjectLimitMode,
)
from app.db.models import (
    GatewayAdapterProfile,
    GatewayAdapterProfileActivation,
    GatewayRequest,
    Project,
    ProjectApiKey,
)
from app.services.gateway_errors import GatewayClientError, GatewayLimitError
from app.services.project_limit_reservation_service import (
    reconcile_gateway_request,
    reserve_gateway_request,
)
from app.services.project_limits_service import LimitBlock, get_project_limits
from app.services.request_log_service import (
    finish_request_failure,
    finish_request_success,
    new_request_id,
    start_request,
)
from app.services.usage_service import record_usage_event

logger = logging.getLogger(__name__)

_MAX_PROJECT_RESERVE_LOCK_ENTRIES = 10_000
_project_reserve_locks: OrderedDict[str, asyncio.Lock] = OrderedDict()


def _project_reserve_lock(project_id: str) -> asyncio.Lock:
    lock = _project_reserve_locks.get(project_id)
    if lock is not None:
        _project_reserve_locks.move_to_end(project_id)
        return lock
    while len(_project_reserve_locks) >= _MAX_PROJECT_RESERVE_LOCK_ENTRIES:
        evicted = False
        for k in list(_project_reserve_locks.keys()):
            candidate = _project_reserve_locks[k]
            if not candidate.locked():
                del _project_reserve_locks[k]
                evicted = True
                break
        if not evicted:
            stale_key, stale_lock = _project_reserve_locks.popitem(last=False)
            if stale_lock.locked():
                _project_reserve_locks[stale_key] = stale_lock
                _project_reserve_locks.move_to_end(stale_key)
                logger.warning(
                    "project_reserve_locks_cap_all_busy evicted_reinserted key=%s size=%d",
                    stale_key,
                    len(_project_reserve_locks),
                )
            else:
                evicted = True
    new_lock = asyncio.Lock()
    _project_reserve_locks[project_id] = new_lock
    return new_lock


class _LimitReservedBlocked(Exception):
    __slots__ = ("block",)

    def __init__(self, block: LimitBlock) -> None:
        self.block = block


async def _resolve_adapter_profile_association(
    session: AsyncSession,
    *,
    request_id: str,
    project_id: str,
    api_key_id: str,
    domain_key: str | None,
    explicit_gateway_profile_id: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Return (gateway_profile_id, adapter_profile_id, domain_key, adaptation_mode)."""
    explicit = (explicit_gateway_profile_id or "").strip() or None
    domain = (domain_key or "").strip() or None

    if explicit is not None:
        row = await session.scalar(
            select(GatewayAdapterProfile).where(GatewayAdapterProfile.gateway_profile_id == explicit)
        )
        if row is None:
            raise GatewayClientError(
                "Unknown gatewayProfileId.",
                code="unknown_gateway_profile_id",
                request_id=request_id,
            )
        return (
            row.gateway_profile_id,
            row.adapter_profile_id,
            row.domain_key,
            GatewayAdaptationMode.EXPLICIT,
        )

    if domain is None:
        return (None, None, None, None)

    active = await session.scalar(
        select(GatewayAdapterProfileActivation).where(
            GatewayAdapterProfileActivation.domain_key == domain,
            GatewayAdapterProfileActivation.status == GatewayAdapterProfileActivationStatus.ACTIVE,
        ).order_by(desc(GatewayAdapterProfileActivation.created_at))
    )
    canary = await session.scalar(
        select(GatewayAdapterProfileActivation).where(
            GatewayAdapterProfileActivation.domain_key == domain,
            GatewayAdapterProfileActivation.status == GatewayAdapterProfileActivationStatus.CANARY,
        ).order_by(desc(GatewayAdapterProfileActivation.created_at))
    )
    if active is None:
        return (None, None, domain, GatewayAdaptationMode.DOMAIN_ONLY)

    selected_gateway_profile_id = active.gateway_profile_id
    mode: GatewayAdaptationMode = GatewayAdaptationMode.ACTIVE
    if (
        settings.adapter_profile_canary_routing_enabled
        and canary is not None
        and canary.canary_percent is not None
        and 1 <= canary.canary_percent <= 50
    ):
        h = hashlib.sha256(f"{project_id}:{api_key_id}:{request_id}".encode("utf-8")).digest()
        bucket = int.from_bytes(h[:2], "big") % 100
        if bucket < canary.canary_percent:
            selected_gateway_profile_id = canary.gateway_profile_id
            mode = GatewayAdaptationMode.CANARY

    selected = await session.scalar(
        select(GatewayAdapterProfile).where(
            GatewayAdapterProfile.gateway_profile_id == selected_gateway_profile_id
        )
    )
    return (
        selected_gateway_profile_id,
        None if selected is None else selected.adapter_profile_id,
        domain,
        mode,
    )


async def _reserve_hard_limit_or_raise(
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    project_id: str,
    model: str,
    max_tokens: int,
    estimated_prompt_tokens: int | None,
) -> str | None:
    """Return reservation id when hard limits apply and reservation succeeds."""
    async with _project_reserve_lock(project_id):
        async with sessionmaker() as session:
            async with session.begin():
                limits = await get_project_limits(session, project_id=project_id)
                if limits is None or limits.limit_mode != ProjectLimitMode.HARD:
                    return None
                r = await reserve_gateway_request(
                    session,
                    project_id=project_id,
                    limits=limits,
                    model=model,
                    requested_max_tokens=max_tokens,
                    estimated_prompt_tokens=estimated_prompt_tokens,
                    now=datetime.now(timezone.utc),
                )
                if not r.allowed:
                    assert r.block is not None
                    raise _LimitReservedBlocked(r.block)
                assert r.reservation_id is not None
                return r.reservation_id


async def _reconcile_reservation(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    limit_reservation_id: str | None,
    actual_tokens: int,
    actual_cost: float,
    status: str,
) -> None:
    if not limit_reservation_id:
        return
    async with sessionmaker() as session:
        async with session.begin():
            await reconcile_gateway_request(
                session,
                reservation_id=limit_reservation_id,
                actual_tokens=actual_tokens,
                actual_cost=actual_cost,
                status=status,
            )


async def _with_log_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    func: Callable[[AsyncSession], Awaitable[None]],
) -> None:
    """Run *func* in a fresh session and commit it."""
    async with sessionmaker() as session:
        await func(session)
        await session.commit()


async def _load_row(
    session: AsyncSession, *, request_id: str
) -> GatewayRequest:
    stmt = select(GatewayRequest).where(GatewayRequest.request_id == request_id)
    return (await session.execute(stmt)).scalar_one()


async def _finish_success_with_accounting(
    session: AsyncSession,
    *,
    request_id: str,
    provider: str,
    model: str,
    latency_ms: int,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    estimated_cost: float | None,
    fallback_used: bool,
    limit_reservation_id: str | None,
) -> GatewayRequest:
    """Complete the gateway row and its dependent accounting rows together."""
    row = await _load_row(session, request_id=request_id)
    await finish_request_success(
        session,
        row,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=estimated_cost,
        fallback_used=fallback_used,
    )
    await record_usage_event(
        session,
        gateway_request=row,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=estimated_cost,
    )
    if limit_reservation_id:
        await reconcile_gateway_request(
            session,
            reservation_id=limit_reservation_id,
            actual_tokens=(
                prompt_tokens + completion_tokens
                if prompt_tokens is not None and completion_tokens is not None
                else 0
            ),
            actual_cost=float(estimated_cost or 0.0),
            status="completed",
        )
    return row


async def _record_failure(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    request_id: str,
    latency_ms: int,
    error_code: str,
    error_message: str,
    limit_reservation_id: str | None = None,
) -> None:
    async def _do(session: AsyncSession) -> None:
        row = await _load_row(session, request_id=request_id)
        await finish_request_failure(
            session,
            row,
            latency_ms=latency_ms,
            error_code=error_code,
            error_message=error_message,
        )
        if limit_reservation_id:
            await reconcile_gateway_request(
                session,
                reservation_id=limit_reservation_id,
                actual_tokens=0,
                actual_cost=0.0,
                status=GatewayRequestStatus.FAILED,
            )

    await _with_log_session(sessionmaker, _do)


async def reserve_and_start_gateway_chat_request(
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    project: Project,
    api_key: ProjectApiKey,
    model: str,
    max_tokens: int,
    domain_key: str | None,
    explicit_gateway_profile_id: str | None,
) -> tuple[str, str | None]:
    """Reserve hard limits, insert ``started`` gateway row, or raise limit/client errors."""
    request_id = new_request_id()

    try:
        limit_reservation_id = await _reserve_hard_limit_or_raise(
            sessionmaker=sessionmaker,
            project_id=project.id,
            model=model,
            max_tokens=max_tokens,
            estimated_prompt_tokens=None,
        )
    except _LimitReservedBlocked as exc:
        blocked = exc.block

        async def _log_blocked(log_session: AsyncSession) -> None:
            row = await start_request(
                log_session,
                request_id=request_id,
                project_id=project.id,
                api_key_id=api_key.id,
                requested_model=model,
            )
            await finish_request_failure(
                log_session,
                row,
                latency_ms=0,
                error_code=blocked.error_code,
                error_message=blocked.error_message,
            )

        await _with_log_session(sessionmaker, _log_blocked)
        raise GatewayLimitError(
            blocked.error_message,
            code=blocked.error_code,
            request_id=request_id,
            limit_type=blocked.limit_type,
            current_value=blocked.current_value,
            limit_value=blocked.limit_value,
            window=blocked.window,
            reset_at=blocked.reset_at,
        ) from None

    async def _start(session: AsyncSession) -> None:
        gateway_profile_id, adapter_profile_id, domain_key_out, adaptation_mode = (
            await _resolve_adapter_profile_association(
                session,
                request_id=request_id,
                project_id=project.id,
                api_key_id=api_key.id,
                domain_key=domain_key,
                explicit_gateway_profile_id=explicit_gateway_profile_id,
            )
        )
        await start_request(
            session,
            request_id=request_id,
            project_id=project.id,
            api_key_id=api_key.id,
            requested_model=model,
            limit_reservation_id=limit_reservation_id,
            gateway_profile_id=gateway_profile_id,
            adapter_profile_id=adapter_profile_id,
            domain_key=domain_key_out,
            adaptation_mode=adaptation_mode,
        )

    try:
        await _with_log_session(sessionmaker, _start)
    except GatewayClientError as exc:
        error_code = exc.code
        error_message = str(exc)

        async def _log_client_error(log_session: AsyncSession) -> None:
            row = await start_request(
                log_session,
                request_id=request_id,
                project_id=project.id,
                api_key_id=api_key.id,
                requested_model=model,
                limit_reservation_id=limit_reservation_id,
                gateway_profile_id=(explicit_gateway_profile_id or "").strip() or None,
                adapter_profile_id=None,
                domain_key=(domain_key or "").strip() or None,
                adaptation_mode=GatewayAdaptationMode.EXPLICIT,
            )
            await finish_request_failure(
                log_session,
                row,
                latency_ms=0,
                error_code=error_code,
                error_message=error_message,
            )

        await _with_log_session(sessionmaker, _log_client_error)
        await _reconcile_reservation(
            sessionmaker,
            limit_reservation_id=limit_reservation_id,
            actual_tokens=0,
            actual_cost=0.0,
            status=GatewayRequestStatus.FAILED,
        )
        raise
    except BaseException:
        await _reconcile_reservation(
            sessionmaker,
            limit_reservation_id=limit_reservation_id,
            actual_tokens=0,
            actual_cost=0.0,
            status=GatewayRequestStatus.FAILED,
        )
        raise

    return request_id, limit_reservation_id
