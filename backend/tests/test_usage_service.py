from __future__ import annotations

import json

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models
from app.services.usage_service import record_usage_event


@pytest_asyncio.fixture
async def sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield sm
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_record_usage_event_persists_complete_usage(sessionmaker) -> None:
    async with sessionmaker() as session:
        project = models.Project(name="p")
        session.add(project)
        await session.flush()
        gateway_request = models.GatewayRequest(
            request_id="req_1",
            project_id=project.id,
            requested_model="conexus-fast",
            status="completed",
        )
        session.add(gateway_request)
        await session.flush()

        row = await record_usage_event(
            session,
            gateway_request=gateway_request,
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=5,
            cost_usd=0.001,
            metadata={"fallback_used": False},
        )

        assert row is not None
        assert row.gateway_request_id == gateway_request.id
        assert row.project_id == project.id
        assert row.provider == "openai"
        assert row.model == "gpt-4o-mini"
        assert row.requested_model == "conexus-fast"
        assert row.prompt_tokens == 10
        assert row.completion_tokens == 5
        assert row.total_tokens == 15
        assert row.cost_usd == 0.001
        assert json.loads(row.metadata_json) == {"fallback_used": False}


@pytest.mark.asyncio
async def test_record_usage_event_is_idempotent_per_gateway_request(sessionmaker) -> None:
    async with sessionmaker() as session:
        project = models.Project(name="p")
        session.add(project)
        await session.flush()
        gateway_request = models.GatewayRequest(
            request_id="req_1",
            project_id=project.id,
            requested_model="conexus-fast",
            status="completed",
        )
        session.add(gateway_request)
        await session.flush()

        first = await record_usage_event(
            session,
            gateway_request=gateway_request,
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=5,
            cost_usd=0.001,
        )
        second = await record_usage_event(
            session,
            gateway_request=gateway_request,
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=99,
            completion_tokens=99,
            cost_usd=9.99,
        )

        assert first is not None
        assert second is not None
        assert second.id == first.id
        rows = list((await session.execute(select(models.UsageEvent))).scalars())
        assert len(rows) == 1
        assert rows[0].prompt_tokens == 10
        assert rows[0].completion_tokens == 5


@pytest.mark.asyncio
async def test_record_usage_event_rereads_existing_row_after_unique_race(
    sessionmaker, monkeypatch
) -> None:
    async with sessionmaker() as session:
        project = models.Project(name="p")
        session.add(project)
        await session.flush()
        gateway_request = models.GatewayRequest(
            request_id="req_1",
            project_id=project.id,
            requested_model="conexus-fast",
            status="completed",
        )
        session.add(gateway_request)
        await session.flush()
        existing = await record_usage_event(
            session,
            gateway_request=gateway_request,
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=5,
            cost_usd=0.001,
        )
        assert existing is not None
        await session.commit()

    async with sessionmaker() as session:
        gateway_request = (
            await session.execute(select(models.GatewayRequest))
        ).scalar_one()
        original_scalar = session.scalar
        calls = 0

        async def scalar_with_stale_first_read(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return None
            return await original_scalar(*args, **kwargs)

        monkeypatch.setattr(session, "scalar", scalar_with_stale_first_read)
        row = await record_usage_event(
            session,
            gateway_request=gateway_request,
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=99,
            completion_tokens=99,
            cost_usd=9.99,
        )

        assert row is not None
        assert row.id == existing.id
        rows = list((await session.execute(select(models.UsageEvent))).scalars())
        assert len(rows) == 1
        assert rows[0].prompt_tokens == 10


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prompt_tokens,completion_tokens,cost_usd",
    [
        (None, 5, 0.001),
        (10, None, 0.001),
        (10, 5, None),
    ],
)
async def test_record_usage_event_skips_incomplete_usage(
    sessionmaker, prompt_tokens, completion_tokens, cost_usd
) -> None:
    async with sessionmaker() as session:
        project = models.Project(name="p")
        session.add(project)
        await session.flush()
        gateway_request = models.GatewayRequest(
            request_id="req_1",
            project_id=project.id,
            requested_model="conexus-fast",
            status="completed",
        )
        session.add(gateway_request)
        await session.flush()

        row = await record_usage_event(
            session,
            gateway_request=gateway_request,
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
        )

        assert row is None
