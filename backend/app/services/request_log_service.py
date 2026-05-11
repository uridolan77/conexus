"""Gateway request log service — start_request / finish_request.

Two-phase logging so a row exists even when the provider call crashes
mid-flight:

1. :func:`start_request` writes the row with status ``"started"`` before any
   provider call.
2. :func:`finish_request_success` / :func:`finish_request_failure` patch in
   latency, tokens, cost, error, and the terminal status.

The two writes share a request_id (uuid4 hex) so the BO can correlate
logs for a single client call.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GatewayRequest

_CLIENT_REQUEST_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def new_request_id() -> str:
    return uuid.uuid4().hex


def is_valid_client_request_id(value: str) -> bool:
    """True if *value* is safe to store as ``gateway_requests.request_id`` (caller-supplied)."""
    return bool(_CLIENT_REQUEST_ID_RE.fullmatch(value))


async def start_request(
    session: AsyncSession,
    *,
    request_id: str,
    project_id: str | None,
    api_key_id: str | None,
    requested_model: str,
    limit_reservation_id: str | None = None,
    gateway_profile_id: str | None = None,
    adapter_profile_id: str | None = None,
    domain_key: str | None = None,
    adaptation_mode: str | None = None,
) -> GatewayRequest:
    row = GatewayRequest(
        request_id=request_id,
        project_id=project_id,
        api_key_id=api_key_id,
        requested_model=requested_model,
        status="started",
        limit_reservation_id=limit_reservation_id,
        gateway_profile_id=gateway_profile_id,
        adapter_profile_id=adapter_profile_id,
        domain_key=domain_key,
        adaptation_mode=adaptation_mode,
    )
    session.add(row)
    await session.flush()
    return row


async def finish_request_success(
    session: AsyncSession,
    row: GatewayRequest,
    *,
    provider: str,
    model: str,
    latency_ms: int,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    estimated_cost: float | None,
    fallback_used: bool,
) -> None:
    row.provider = provider
    row.model = model
    row.status = "completed"
    row.latency_ms = latency_ms
    row.prompt_tokens = prompt_tokens
    row.completion_tokens = completion_tokens
    if prompt_tokens is not None and completion_tokens is not None:
        row.total_tokens = prompt_tokens + completion_tokens
    else:
        row.total_tokens = None
    row.estimated_cost = estimated_cost
    row.fallback_used = fallback_used
    row.completed_at = datetime.now(timezone.utc)
    await session.flush()


async def finish_request_failure(
    session: AsyncSession,
    row: GatewayRequest,
    *,
    latency_ms: int,
    error_code: str,
    error_message: str,
) -> None:
    row.status = "failed"
    row.latency_ms = latency_ms
    row.error_code = error_code
    row.error_message = error_message
    row.completed_at = datetime.now(timezone.utc)
    await session.flush()
