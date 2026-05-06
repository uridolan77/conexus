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
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.domain_enums import GatewayRequestStatus
from app.llm import LLMProvider, get_cost
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderError,
    ProviderUnavailableError,
    UnknownModelError,
)
from app.llm.types import ChatMessage, ChatStreamChunk
from app.db.models import Project, ProjectApiKey
from app.services.gateway_context import GatewayResponse, GatewayStreamResponse
from app.services.gateway_errors import GatewayClientError, GatewayLimitError, GatewayUpstreamError
from app.services.gateway_setup import (
    _finish_success_with_accounting,
    _record_failure,
    _with_log_session,
    reserve_and_start_gateway_chat_request,
)

logger = logging.getLogger(__name__)

# Re-export for callers/tests that import from ``gateway_service``.
__all__ = (
    "GatewayClientError",
    "GatewayLimitError",
    "GatewayUpstreamError",
    "GatewayResponse",
    "GatewayStreamResponse",
    "run_chat_completion",
    "run_chat_completion_stream",
)


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
    domain_key: str | None = None,
    explicit_gateway_profile_id: str | None = None,
) -> GatewayResponse:
    request_id, limit_reservation_id = await reserve_and_start_gateway_chat_request(
        sessionmaker=sessionmaker,
        project=project,
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        domain_key=domain_key,
        explicit_gateway_profile_id=explicit_gateway_profile_id,
    )

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

    async def _finish(session: AsyncSession) -> None:
        await _finish_success_with_accounting(
            session,
            request_id=request_id,
            provider=result.provider,
            model=result.model,
            latency_ms=latency_ms,
            prompt_tokens=result.usage.input_tokens,
            completion_tokens=result.usage.output_tokens,
            estimated_cost=cost,
            fallback_used=result.fallback_used,
            limit_reservation_id=limit_reservation_id,
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
    domain_key: str | None = None,
    explicit_gateway_profile_id: str | None = None,
) -> GatewayStreamResponse:
    request_id, limit_reservation_id = await reserve_and_start_gateway_chat_request(
        sessionmaker=sessionmaker,
        project=project,
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        domain_key=domain_key,
        explicit_gateway_profile_id=explicit_gateway_profile_id,
    )

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

            async def _finish(session: AsyncSession) -> None:
                await _finish_success_with_accounting(
                    session,
                    request_id=request_id,
                    provider=seen_provider or "unknown",
                    model=seen_model or model,
                    latency_ms=latency_ms,
                    prompt_tokens=final_usage.input_tokens if final_usage else None,
                    completion_tokens=final_usage.output_tokens if final_usage else None,
                    estimated_cost=cost,
                    fallback_used=seen_fallback_used,
                    limit_reservation_id=limit_reservation_id,
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
        except asyncio.CancelledError:
            await asyncio.shield(
                _record_failure(
                    sessionmaker,
                    request_id=request_id,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error_code="stream_cancelled",
                    error_message="stream cancelled",
                    limit_reservation_id=limit_reservation_id,
                )
            )
            raise
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
