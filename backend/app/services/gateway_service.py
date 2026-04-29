"""Gateway service — glues auth, provider call, and request logging.

Flow (docs/04_GATEWAY.md):

    create request_id
    start gateway_requests row
    call provider
    finish gateway_requests row
    return normalized response

The provider is whatever ``app.llm.make_provider`` returns; in tests we
inject a stub via FastAPI dependency override.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project, ProjectApiKey
from app.llm import LLMProvider, get_cost
from app.llm.errors import (
    AllProvidersFailedError,
    ProviderError,
    UnknownModelError,
)
from app.llm.types import ChatMessage, ChatResult
from app.services.request_log_service import (
    finish_request_failure,
    finish_request_success,
    new_request_id,
    start_request,
)

logger = logging.getLogger(__name__)


class GatewayClientError(Exception):
    """Caller-visible 4xx — bad model, bad input."""

    def __init__(self, message: str, *, code: str = "bad_request") -> None:
        super().__init__(message)
        self.code = code


class GatewayUpstreamError(Exception):
    """Caller-visible 502/503 — all providers failed."""

    def __init__(self, message: str, *, code: str = "upstream_error") -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class GatewayResponse:
    request_id: str
    result: ChatResult
    cost_usd: float


async def run_chat_completion(
    *,
    session: AsyncSession,
    provider: LLMProvider,
    project: Project,
    api_key: ProjectApiKey,
    model: str,
    messages: list[ChatMessage],
    max_tokens: int,
    temperature: float,
) -> GatewayResponse:
    request_id = new_request_id()
    row = await start_request(
        session,
        request_id=request_id,
        project_id=project.id,
        api_key_id=api_key.id,
        requested_model=model,
    )

    started = time.monotonic()
    try:
        result = await provider.chat(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except UnknownModelError as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        await finish_request_failure(
            session, row,
            latency_ms=latency_ms,
            error_code="unknown_model",
            error_message=str(exc),
        )
        # Commit the failure row explicitly so the session-level rollback that
        # follows the upcoming raise does not erase the audit trail.
        await session.commit()
        raise GatewayClientError(str(exc), code="unknown_model") from exc
    except AllProvidersFailedError as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        await finish_request_failure(
            session, row,
            latency_ms=latency_ms,
            error_code="all_providers_failed",
            error_message=str(exc),
        )
        await session.commit()
        raise GatewayUpstreamError(str(exc), code="all_providers_failed") from exc
    except ProviderError as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        code = type(exc).__name__
        await finish_request_failure(
            session, row,
            latency_ms=latency_ms,
            error_code=code,
            error_message=str(exc),
        )
        await session.commit()
        raise GatewayUpstreamError(str(exc), code=code) from exc

    latency_ms = int((time.monotonic() - started) * 1000)
    cost = get_cost(
        result.model, result.usage.input_tokens, result.usage.output_tokens
    )
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
    logger.info(
        "gateway_request_ok request_id=%s project_id=%s provider=%s model=%s "
        "latency_ms=%d tokens_in=%d tokens_out=%d cost_usd=%.6f fallback=%s",
        request_id,
        project.id,
        result.provider,
        result.model,
        latency_ms,
        result.usage.input_tokens,
        result.usage.output_tokens,
        cost,
        result.fallback_used,
    )
    return GatewayResponse(request_id=request_id, result=result, cost_usd=cost)
