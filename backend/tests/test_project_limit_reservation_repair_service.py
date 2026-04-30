"""Tests for stale limit reservation listing and repair."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from app.db import models
from app.services.project_limit_reservation_service import reserve_gateway_request
from app.services.project_limit_reservation_repair_service import (
    list_stale_reservations,
    repair_stale_reservation,
)
from app.services.request_log_service import finish_request_failure, start_request


@pytest_asyncio.fixture
async def db_engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

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
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_list_stale_no_gateway_request(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=10,
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
            assert r.reservation_id
            rid = r.reservation_id  # type: ignore[assignment]
            await session.execute(
                update(models.ProjectGatewayLimitReservation)
                .where(models.ProjectGatewayLimitReservation.id == rid)
                .values(created_at=now - timedelta(minutes=30))
            )

    async with db_sessionmaker() as session:
        rows = await list_stale_reservations(
            session,
            older_than_seconds=60,
            project_id=None,
            limit=100,
            now=now,
        )
        assert len(rows) == 1
        assert rows[0].reservation_id == rid
        assert rows[0].repair_kind == "no_gateway_request"
        assert rows[0].recommended_action == "release"


@pytest.mark.asyncio
async def test_repair_no_gateway_releases_and_idempotent(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=10,
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
            rid = r.reservation_id  # type: ignore[assignment]
            await session.execute(
                update(models.ProjectGatewayLimitReservation)
                .where(models.ProjectGatewayLimitReservation.id == rid)
                .values(created_at=now - timedelta(minutes=30))
            )

    async with db_sessionmaker() as session:
        async with session.begin():
            dry = await repair_stale_reservation(
                session, reservation_id=rid, mode="dry_run", now=now
            )
            assert dry is not None
            assert dry.applied is False
            res_row = await session.get(models.ProjectGatewayLimitReservation, rid)
            assert res_row is not None
            assert res_row.reconciled_at is None

    async with db_sessionmaker() as session:
        async with session.begin():
            applied = await repair_stale_reservation(
                session, reservation_id=rid, mode="apply", now=now
            )
            assert applied is not None
            assert applied.applied is True

    async with db_sessionmaker() as session:
        async with session.begin():
            again = await repair_stale_reservation(
                session, reservation_id=rid, mode="apply", now=now
            )
            assert again is not None
            assert again.action == "already_reconciled"


@pytest.mark.asyncio
async def test_repair_failed_request_reconciles(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=10,
            daily_token_limit=10_000,
            monthly_cost_limit=None,
        )
        session.add(lim)
        await session.commit()

    now = datetime.now(timezone.utc)
    rid: str
    req_internal_id: str
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
            rid = r.reservation_id  # type: ignore[assignment]
            gr = await start_request(
                session,
                request_id="abc123",
                project_id=proj.id,
                api_key_id=None,
                requested_model="gpt-4o-mini",
                limit_reservation_id=rid,
            )
            req_internal_id = gr.id
            await finish_request_failure(
                session,
                gr,
                latency_ms=1,
                error_code="test",
                error_message="fail",
            )
            await session.execute(
                update(models.ProjectGatewayLimitReservation)
                .where(models.ProjectGatewayLimitReservation.id == rid)
                .values(created_at=now - timedelta(minutes=30))
            )
            await session.execute(
                update(models.ProjectGatewayLimitReservation)
                .where(models.ProjectGatewayLimitReservation.id == rid)
                .values(reconciled_at=None)
            )
            await session.execute(
                update(models.GatewayRequest)
                .where(models.GatewayRequest.id == req_internal_id)
                .values(status="failed")
            )

    async with db_sessionmaker() as session:
        rows = await list_stale_reservations(
            session,
            older_than_seconds=60,
            project_id=None,
            limit=100,
            now=now,
        )
        assert any(x.reservation_id == rid and x.repair_kind == "gateway_request_failed" for x in rows)

    async with db_sessionmaker() as session:
        async with session.begin():
            out = await repair_stale_reservation(
                session, reservation_id=rid, mode="apply", now=now
            )
            assert out is not None
            assert out.applied is True
            assert out.action == "reconcile_failed_request"


@pytest.mark.asyncio
async def test_repair_completed_without_reconcile(db_sessionmaker) -> None:
    async with db_sessionmaker() as session:
        proj = models.Project(name="p")
        session.add(proj)
        await session.flush()
        lim = models.ProjectLimit(
            project_id=proj.id,
            limit_mode="hard",
            daily_request_limit=10,
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
            rid = r.reservation_id  # type: ignore[assignment]
            gr = await start_request(
                session,
                request_id="def456",
                project_id=proj.id,
                api_key_id=None,
                requested_model="gpt-4o-mini",
                limit_reservation_id=rid,
            )
            gr.status = "completed"
            gr.completed_at = now
            gr.total_tokens = 42
            gr.estimated_cost = 0.01
            await session.flush()
            await session.execute(
                update(models.ProjectGatewayLimitReservation)
                .where(models.ProjectGatewayLimitReservation.id == rid)
                .values(created_at=now - timedelta(minutes=30))
            )

    async with db_sessionmaker() as session:
        async with session.begin():
            out = await repair_stale_reservation(
                session, reservation_id=rid, mode="apply", now=now
            )
            assert out is not None
            assert out.applied is True
            assert out.action == "reconcile_completed_request"

    async with db_sessionmaker() as session:
        w = (
            await session.execute(
                select(models.ProjectUsageWindow).where(
                    models.ProjectUsageWindow.project_id == proj.id,
                    models.ProjectUsageWindow.window_kind == "daily",
                )
            )
        ).scalar_one()
        assert w.token_count_completed == 42


@pytest.mark.asyncio
async def test_started_not_completed_skipped_under_force_threshold(db_sessionmaker) -> None:
    from app.core.config import settings

    prev = settings.limit_reservation_force_repair_after_seconds
    settings.limit_reservation_force_repair_after_seconds = 3600
    try:
        async with db_sessionmaker() as session:
            proj = models.Project(name="p")
            session.add(proj)
            await session.flush()
            lim = models.ProjectLimit(
                project_id=proj.id,
                limit_mode="hard",
                daily_request_limit=10,
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
                rid = r.reservation_id  # type: ignore[assignment]
                await start_request(
                    session,
                    request_id="ghi789",
                    project_id=proj.id,
                    api_key_id=None,
                    requested_model="gpt-4o-mini",
                    limit_reservation_id=rid,
                )
                await session.execute(
                    update(models.ProjectGatewayLimitReservation)
                    .where(models.ProjectGatewayLimitReservation.id == rid)
                    .values(created_at=now - timedelta(minutes=30))
                )

        async with db_sessionmaker() as session:
            async with session.begin():
                out = await repair_stale_reservation(
                    session, reservation_id=rid, mode="apply", now=now
                )
                assert out is not None
                assert out.applied is False
                assert out.action == "repair_skipped"
    finally:
        settings.limit_reservation_force_repair_after_seconds = prev
