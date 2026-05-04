"""Usage event persistence for successful gateway calls."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GatewayRequest, UsageEvent


async def record_usage_event(
    session: AsyncSession,
    *,
    gateway_request: GatewayRequest,
    provider: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cost_usd: float | None,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent | None:
    """Persist a normalized usage ledger row when complete usage exists."""
    existing = await session.scalar(
        select(UsageEvent).where(
            UsageEvent.gateway_request_id == gateway_request.id
        )
    )
    if existing is not None:
        return existing

    if (
        gateway_request.project_id is None
        or prompt_tokens is None
        or completion_tokens is None
        or cost_usd is None
    ):
        return None

    row = UsageEvent(
        gateway_request_id=gateway_request.id,
        project_id=gateway_request.project_id,
        provider=provider,
        model=model,
        requested_model=gateway_request.requested_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=cost_usd,
        metadata_json=json.dumps(metadata, sort_keys=True) if metadata else None,
    )
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
        return row
    except IntegrityError:
        existing = await session.scalar(
            select(UsageEvent).where(
                UsageEvent.gateway_request_id == gateway_request.id
            )
        )
        if existing is not None:
            return existing
        raise
