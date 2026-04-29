"""Provider candidate metadata for future runtime config resolution."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ProviderConfig

ProviderCandidateSource = Literal["bo_config", "env"]


class ProviderCandidate(BaseModel):
    provider: str
    source: ProviderCandidateSource
    config_id: str | None
    label: str | None
    key_mask: str | None
    is_active: bool
    last_test_status: str | None
    last_tested_at: datetime | None


async def list_provider_candidates(session: AsyncSession) -> list[ProviderCandidate]:
    stmt = (
        select(ProviderConfig)
        .where(
            ProviderConfig.is_active.is_(True),
            ProviderConfig.revoked_at.is_(None),
        )
        .order_by(ProviderConfig.provider.asc(), ProviderConfig.created_at.desc())
    )
    rows = list((await session.execute(stmt)).scalars())
    candidates = [
        ProviderCandidate(
            provider=row.provider,
            source="bo_config",
            config_id=row.id,
            label=row.label,
            key_mask=row.key_mask,
            is_active=row.is_active,
            last_test_status=row.last_test_status,
            last_tested_at=row.last_tested_at,
        )
        for row in rows
    ]
    candidates.extend(_env_candidates())
    return candidates


def _env_candidates() -> list[ProviderCandidate]:
    output: list[ProviderCandidate] = []
    if settings.anthropic_api_key:
        output.append(_env_candidate("anthropic"))
    if settings.openai_api_key:
        output.append(_env_candidate("openai"))
    return output


def _env_candidate(provider: str) -> ProviderCandidate:
    return ProviderCandidate(
        provider=provider,
        source="env",
        config_id=None,
        label="Environment fallback",
        key_mask=None,
        is_active=True,
        last_test_status=None,
        last_tested_at=None,
    )
