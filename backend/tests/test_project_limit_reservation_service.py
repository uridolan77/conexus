"""Unit tests for project limit reservation + reconcile."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db import models
from app.services.project_limit_reservation_service import (
    reconcile_gateway_request,
    release_orphan_limit_reservation,
    reserve_gateway_request,
)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_sessionmaker(db_engine):
    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_reserve_blocks_at_daily_request_limit(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=1,
            daily_token_limit=None,
            monthly_cost_limit=None,
        )
        session.add(lim)
        await session.commit()

    now = datetime.now(timezone.utc)
    async with db_sessionmaker() as session:
        async with session.begin():
            lim2 = (
                await session.execute(
                    select(models.ProjectLimit).where(models.ProjectLimit.project_id == proj.id)
                )
            ).scalar_one()
            r1 = await reserve_gateway_request(
                session,
                project_id=proj.id,
                limits=lim2,
                model="gpt-4o-mini",
                requested_max_tokens=100,
                estimated_prompt_tokens=None,
                now=now,
            )
            assert r1.allowed and r1.reservation_id
            r2 = await reserve_gateway_request(
                session,
                project_id=proj.id,
                limits=lim2,
                model="gpt-4o-mini",
                requested_max_tokens=100,
                estimated_prompt_tokens=None,
                now=now,
            )
            assert not r2.allowed
            assert r2.block is not None
            assert r2.block.error_code == "daily_request_limit_exceeded"


@pytest.mark.asyncio
async def test_reconcile_moves_reserved_to_completed(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=100,
            daily_token_limit=10_000,
            monthly_cost_limit=None,
        )
        session.add(lim)
        await session.commit()

    now = datetime.now(timezone.utc)
    rid: str
    async with db_sessionmaker() as session:
        async with session.begin():
            lim2 = (
                await session.execute(
                    select(models.ProjectLimit).where(models.ProjectLimit.project_id == proj.id)
                )
            ).scalar_one()
            r = await reserve_gateway_request(
                session,
                project_id=proj.id,
                limits=lim2,
                model="gpt-4o-mini",
                requested_max_tokens=50,
                estimated_prompt_tokens=None,
                now=now,
            )
            assert r.allowed and r.reservation_id
            rid = r.reservation_id  # type: ignore[assignment]

    async with db_sessionmaker() as session:
        async with session.begin():
            await reconcile_gateway_request(
                session,
                reservation_id=rid,
                actual_tokens=30,
                actual_cost=0.0,
                status="completed",
            )

    async with db_sessionmaker() as session:
        w = (
            await session.execute(
                select(models.ProjectUsageWindow).where(
                    models.ProjectUsageWindow.project_id == proj.id,
                    models.ProjectUsageWindow.window_kind == "daily",
                )
            )
        ).scalar_one()
        assert w.request_count_reserved == 0
        assert w.request_count_completed == 1
        assert w.token_count_reserved == 0
        assert w.token_count_completed == 30


@pytest.mark.asyncio
async def test_release_orphan_does_not_increment_completed_requests(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=100,
            daily_token_limit=10_000,
            monthly_cost_limit=None,
        )
        session.add(lim)
        await session.commit()

    now = datetime.now(timezone.utc)
    rid: str
    async with db_sessionmaker() as session:
        async with session.begin():
            lim2 = (
                await session.execute(
                    select(models.ProjectLimit).where(models.ProjectLimit.project_id == proj.id)
                )
            ).scalar_one()
            r = await reserve_gateway_request(
                session,
                project_id=proj.id,
                limits=lim2,
                model="gpt-4o-mini",
                requested_max_tokens=10,
                estimated_prompt_tokens=None,
                now=now,
            )
            assert r.reservation_id
            rid = r.reservation_id  # type: ignore[assignment]

    async with db_sessionmaker() as session:
        async with session.begin():
            ok = await release_orphan_limit_reservation(session, reservation_id=rid)
            assert ok is True

    async with db_sessionmaker() as session:
        w = (
            await session.execute(
                select(models.ProjectUsageWindow).where(
                    models.ProjectUsageWindow.project_id == proj.id,
                    models.ProjectUsageWindow.window_kind == "daily",
                )
            )
        ).scalar_one()
        assert w.request_count_reserved == 0
        assert w.request_count_completed == 0
        res = await session.get(models.ProjectGatewayLimitReservation, rid)
        assert res is not None
        assert res.reconciled_at is not None


@pytest.mark.asyncio
async def test_reconcile_idempotent(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=100,
            daily_token_limit=10_000,
            monthly_cost_limit=None,
        )
        session.add(lim)
        await session.commit()

    now = datetime.now(timezone.utc)
    rid: str
    async with db_sessionmaker() as session:
        async with session.begin():
            lim2 = (
                await session.execute(
                    select(models.ProjectLimit).where(models.ProjectLimit.project_id == proj.id)
                )
            ).scalar_one()
            r = await reserve_gateway_request(
                session,
                project_id=proj.id,
                limits=lim2,
                model="gpt-4o-mini",
                requested_max_tokens=10,
                estimated_prompt_tokens=None,
                now=now,
            )
            assert r.allowed and r.reservation_id
            rid = r.reservation_id  # type: ignore[assignment]

    for _ in range(2):
        async with db_sessionmaker() as session:
            async with session.begin():
                await reconcile_gateway_request(
                    session,
                    reservation_id=rid,
                    actual_tokens=5,
                    actual_cost=0.0,
                    status="completed",
                )

    async with db_sessionmaker() as session:
        w = (
            await session.execute(
                select(models.ProjectUsageWindow).where(
                    models.ProjectUsageWindow.project_id == proj.id,
                    models.ProjectUsageWindow.window_kind == "daily",
                )
            )
        ).scalar_one()
        assert w.request_count_completed == 1
        assert w.token_count_completed == 5


@pytest.mark.asyncio
async def test_reserve_monthly_hard_allows_conexus_default_alias_when_priced(
    db_sessionmaker,
) -> None:
    """Integration: alias expands to underlying models with explicit pricing."""
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            monthly_cost_limit=1e9,
            daily_request_limit=10_000,
            daily_token_limit=100_000_000,
        )
        session.add(lim)
        await session.commit()

    now = datetime.now(timezone.utc)
    async with db_sessionmaker() as session:
        async with session.begin():
            lim2 = (
                await session.execute(
                    select(models.ProjectLimit).where(models.ProjectLimit.project_id == proj.id)
                )
            ).scalar_one()
            r = await reserve_gateway_request(
                session,
                project_id=proj.id,
                limits=lim2,
                model="conexus-default",
                requested_max_tokens=4096,
                estimated_prompt_tokens=None,
                now=now,
            )
            assert r.allowed and r.reservation_id


@pytest.mark.asyncio
async def test_reserve_ignores_gateway_request_rows_when_legacy_fallback_disabled(
    db_sessionmaker,
) -> None:
    """With USE_LEGACY_HARD_LIMIT_GATEWAY_FALLBACKS=false, admission uses windows only."""
    now = datetime(2026, 5, 6, 15, 30, tzinfo=timezone.utc)
    async with db_sessionmaker() as session:
        proj = models.Project(name="legacy-off")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=1,
            daily_token_limit=None,
            monthly_cost_limit=None,
        )
        session.add(lim)
        session.add_all(
            [
                models.GatewayRequest(
                    request_id="orphan-1",
                    project_id=proj.id,
                    requested_model="m",
                    status="completed",
                    total_tokens=1,
                    estimated_cost=0.0,
                    fallback_used=False,
                    created_at=now,
                    completed_at=now,
                ),
                models.GatewayRequest(
                    request_id="orphan-2",
                    project_id=proj.id,
                    requested_model="m",
                    status="completed",
                    total_tokens=1,
                    estimated_cost=0.0,
                    fallback_used=False,
                    created_at=now - timedelta(minutes=1),
                    completed_at=now - timedelta(minutes=1),
                ),
            ]
        )
        await session.commit()

    prev = settings.use_legacy_hard_limit_gateway_fallbacks
    settings.use_legacy_hard_limit_gateway_fallbacks = False
    try:
        async with db_sessionmaker() as session:
            async with session.begin():
                lim2 = (
                    await session.execute(
                        select(models.ProjectLimit).where(models.ProjectLimit.project_id == proj.id)
                    )
                ).scalar_one()
                r = await reserve_gateway_request(
                    session,
                    project_id=proj.id,
                    limits=lim2,
                    model="gpt-4o-mini",
                    requested_max_tokens=100,
                    estimated_prompt_tokens=None,
                    now=now,
                )
                assert r.allowed and r.reservation_id
    finally:
        settings.use_legacy_hard_limit_gateway_fallbacks = prev
