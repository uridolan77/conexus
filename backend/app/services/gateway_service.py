"""Gateway service — glues auth, provider call, and request logging.

Flow (docs/04_GATEWAY.md):

    create request_id
    reserve hard limits (v0.7+, separate commit when applicable)
    insert gateway_requests row (own session, commits before provider call)
    call provider
    insert finish row update (own session)
    reconcile limit reservation (same session as finish when possible)
    return normalized response

Request-log writes own their own short-lived sessions so a provider failure
does not corrupt an enclosing request transaction, and so the failure log
row never depends on a fragile commit-inside-error-path.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from datetime import datetime, timezone

from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import GatewayRequest, Project, ProjectApiKey
from app.core.config import settings
from app.llm import LLMProvider, get_cost
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderError,
    ProviderUnavailableError,
    UnknownModelError,
)
from app.llm.types import ChatMessage, ChatResult, ChatStreamChunk
from app.services.request_log_service import (
    finish_request_failure,
    finish_request_success,
    new_request_id,
    start_request,
)
from app.services.project_limits_service import LimitBlock, get_project_limits
from app.services.project_limit_reservation_service import (
    reconcile_gateway_request,
    reserve_gateway_request,
)

logger = logging.getLogger(__name__)

# Serialize hard-limit reservation per project so concurrent asyncio tasks cannot
# interleave between reserve and start_request (SQLite has no row lock; Postgres
# still benefits from fewer aborted transactions).
_project_reserve_locks: dict[str, asyncio.Lock] = {}


def _project_reserve_lock(project_id: str) -> asyncio.Lock:
    lock = _project_reserve_locks.get(project_id)
    if lock is None:
        lock = asyncio.Lock()
        _project_reserve_locks[project_id] = lock
    return lock


class _LimitReservedBlocked(Exception):
    __slots__ = ("block",)

    def __init__(self, block: LimitBlock) -> None:
        self.block = block


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
                if limits is None or limits.limit_mode != "hard":
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


class GatewayClientError(Exception):
    """Caller-visible 4xx — bad model, bad input."""

    def __init__(self, message: str, *, code: str, request_id: str) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id


class GatewayUpstreamError(Exception):
    """Caller-visible 502/503 — all providers failed."""

    def __init__(self, message: str, *, code: str, request_id: str) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id


class GatewayLimitError(Exception):
    """Caller-visible 429 — project hard limit exceeded."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        request_id: str,
        limit_type: str,
        current_value: float,
        limit_value: float,
        window: str,
        reset_at: datetime | None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id
        self.limit_type = limit_type
        self.current_value = current_value
        self.limit_value = limit_value
        self.window = window
        self.reset_at = reset_at


@dataclass(slots=True)
class GatewayResponse:
    request_id: str
    result: ChatResult
    cost_usd: float


@dataclass(slots=True)
class GatewayStreamResponse:
    request_id: str
    stream: AsyncIterator[ChatStreamChunk]


async def _with_log_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    func: Callable[[AsyncSession], Awaitable[None]],
) -> None:
    """Run *func* in a fresh session and commit it.

    Each call to the request-log service uses its own session so log writes
    cannot be rolled back by an enclosing request transaction.
    """
    async with sessionmaker() as session:
        await func(session)
        await session.commit()


async def _load_row(
    session: AsyncSession, *, request_id: str
) -> GatewayRequest:
    stmt = select(GatewayRequest).where(GatewayRequest.request_id == request_id)
    return (await session.execute(stmt)).scalar_one()


async def run_chat_completion(
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    provider: LLMProvider,
    project: Project,
    api_key: ProjectApiKey,
    model: str,
    messages: list[ChatMessage],
    max_tokens: int,
    temperature: float,
) -> GatewayResponse:
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
        await start_request(
            session,
            request_id=request_id,
            project_id=project.id,
            api_key_id=api_key.id,
            requested_model=model,
            limit_reservation_id=limit_reservation_id,
        )

    try:
        await _with_log_session(sessionmaker, _start)
    except BaseException:
        await _reconcile_reservation(
            sessionmaker,
            limit_reservation_id=limit_reservation_id,
            actual_tokens=0,
            actual_cost=0.0,
            status="failed",
        )
        raise

    started = time.monotonic()
    try:
        try:
            async with asyncio.timeout(settings.llm_request_timeout_seconds):
                result = await provider.chat(
                    messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
        except TimeoutError as exc:
            await _record_failure(
                sessionmaker,
                request_id=request_id,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_code="ProviderUnavailableError",
                error_message="Upstream request timed out.",
                limit_reservation_id=limit_reservation_id,
            )
            raise ProviderUnavailableError(
                "Upstream request timed out.",
                provider=getattr(provider, "provider_name", "unknown"),
            ) from exc
    except UnknownModelError as exc:
        await _record_failure(
            sessionmaker,
            request_id=request_id,
            latency_ms=int((time.monotonic() - started) * 1000),
            error_code="unknown_model",
            error_message=str(exc),
            limit_reservation_id=limit_reservation_id,
        )
        raise GatewayClientError(
            str(exc), code="unknown_model", request_id=request_id
        ) from exc
    except AllProvidersFailedError as exc:
        await _record_failure(
            sessionmaker,
            request_id=request_id,
            latency_ms=int((time.monotonic() - started) * 1000),
            error_code="all_providers_failed",
            error_message=str(exc),
            limit_reservation_id=limit_reservation_id,
        )
        raise GatewayUpstreamError(
            str(exc), code="all_providers_failed", request_id=request_id
        ) from exc
    except ProviderError as exc:
        code = type(exc).__name__
        await _record_failure(
            sessionmaker,
            request_id=request_id,
            latency_ms=int((time.monotonic() - started) * 1000),
            error_code=code,
            error_message=str(exc),
            limit_reservation_id=limit_reservation_id,
        )
        raise GatewayUpstreamError(
            str(exc), code=code, request_id=request_id
        ) from exc

    latency_ms = int((time.monotonic() - started) * 1000)
    cost = get_cost(
        result.model, result.usage.input_tokens, result.usage.output_tokens
    )
    total_tokens = result.usage.input_tokens + result.usage.output_tokens

    async def _finish(session: AsyncSession) -> None:
        row = await _load_row(session, request_id=request_id)
        await finish_request_success(
            session, row,
            provider=result.provider,
            model=result.model,
            latency_ms=latency_ms,
            prompt_tokens=result.usage.input_tokens,
            completion_tokens=result.usage.output_tokens,
            estimated_cost=cost,
            fallback_used=result.fallback_used,
        )
        if limit_reservation_id:
            await reconcile_gateway_request(
                session,
                reservation_id=limit_reservation_id,
                actual_tokens=total_tokens,
                actual_cost=cost,
                status="completed",
            )

    await _with_log_session(sessionmaker, _finish)

    logger.info(
        "gateway_request_ok request_id=%s project_id=%s limit_reservation_id=%s "
        "provider=%s model=%s latency_ms=%d tokens_in=%d tokens_out=%d cost_usd=%.6f fallback=%s",
        request_id,
        project.id,
        limit_reservation_id or "",
        result.provider,
        result.model,
        latency_ms,
        result.usage.input_tokens,
        result.usage.output_tokens,
        cost,
        result.fallback_used,
    )
    return GatewayResponse(request_id=request_id, result=result, cost_usd=cost)


async def run_chat_completion_stream(
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    provider: LLMProvider,
    project: Project,
    api_key: ProjectApiKey,
    model: str,
    messages: list[ChatMessage],
    max_tokens: int,
    temperature: float,
) -> GatewayStreamResponse:
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
        await start_request(
            session,
            request_id=request_id,
            project_id=project.id,
            api_key_id=api_key.id,
            requested_model=model,
            limit_reservation_id=limit_reservation_id,
        )

    try:
        await _with_log_session(sessionmaker, _start)
    except BaseException:
        await _reconcile_reservation(
            sessionmaker,
            limit_reservation_id=limit_reservation_id,
            actual_tokens=0,
            actual_cost=0.0,
            status="failed",
        )
        raise

    started = time.monotonic()
    upstream_stream = provider.stream_chat(
        messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    async def _wrapped() -> AsyncIterator[ChatStreamChunk]:
        aiter = upstream_stream.__aiter__()
        seen_provider: str | None = None
        seen_model: str | None = None
        seen_fallback_used = False
        final_usage = None
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        aiter.__anext__(),
                        timeout=settings.llm_stream_timeout_seconds,
                    )
                except StopAsyncIteration:
                    break
                except TimeoutError as exc:
                    await _record_failure(
                        sessionmaker,
                        request_id=request_id,
                        latency_ms=int((time.monotonic() - started) * 1000),
                        error_code="ProviderUnavailableError",
                        error_message="Upstream stream timed out.",
                        limit_reservation_id=limit_reservation_id,
                    )
                    raise ProviderUnavailableError(
                        "Upstream stream timed out.",
                        provider=getattr(provider, "provider_name", "unknown"),
                    ) from exc

                seen_provider = chunk.provider
                seen_model = chunk.model
                seen_fallback_used = seen_fallback_used or chunk.fallback_used
                if chunk.usage is not None:
                    final_usage = chunk.usage
                yield chunk

            latency_ms = int((time.monotonic() - started) * 1000)
            cost = (
                get_cost(
                    seen_model or model,
                    final_usage.input_tokens,
                    final_usage.output_tokens,
                )
                if final_usage is not None
                else None
            )
            total_tokens = (
                final_usage.input_tokens + final_usage.output_tokens
                if final_usage is not None
                else 0
            )
            actual_cost = float(cost or 0.0)

            async def _finish(session: AsyncSession) -> None:
                row = await _load_row(session, request_id=request_id)
                await finish_request_success(
                    session,
                    row,
                    provider=seen_provider or "unknown",
                    model=seen_model or model,
                    latency_ms=latency_ms,
                    prompt_tokens=final_usage.input_tokens if final_usage else None,
                    completion_tokens=final_usage.output_tokens if final_usage else None,
                    estimated_cost=cost,
                    fallback_used=seen_fallback_used,
                )
                if limit_reservation_id:
                    await reconcile_gateway_request(
                        session,
                        reservation_id=limit_reservation_id,
                        actual_tokens=total_tokens,
                        actual_cost=actual_cost,
                        status="completed",
                    )

            await _with_log_session(sessionmaker, _finish)
        except UnknownModelError as exc:
            await _record_failure(
                sessionmaker,
                request_id=request_id,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_code="unknown_model",
                error_message=str(exc),
                limit_reservation_id=limit_reservation_id,
            )
            raise GatewayClientError(
                str(exc), code="unknown_model", request_id=request_id
            ) from exc
        except AllProvidersFailedError as exc:
            await _record_failure(
                sessionmaker,
                request_id=request_id,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_code="all_providers_failed",
                error_message=str(exc),
                limit_reservation_id=limit_reservation_id,
            )
            raise GatewayUpstreamError(
                str(exc), code="all_providers_failed", request_id=request_id
            ) from exc
        except ProviderError as exc:
            code = type(exc).__name__
            await _record_failure(
                sessionmaker,
                request_id=request_id,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_code=code,
                error_message=str(exc),
                limit_reservation_id=limit_reservation_id,
            )
            raise GatewayUpstreamError(
                str(exc), code=code, request_id=request_id
            ) from exc
        except Exception as exc:
            code = type(exc).__name__
            await _record_failure(
                sessionmaker,
                request_id=request_id,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_code=code,
                error_message="stream failed",
                limit_reservation_id=limit_reservation_id,
            )
            raise

    return GatewayStreamResponse(request_id=request_id, stream=_wrapped())


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
            session, row,
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
                status="failed",
            )

    await _with_log_session(sessionmaker, _do)
