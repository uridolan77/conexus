"""Project API key generation/verification tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models
from app.services.project_key_service import (
    create_api_key,
    revoke_api_key,
    verify_api_key,
)


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
async def test_create_and_verify(sessionmaker) -> None:
    async with sessionmaker() as session:
        project = models.Project(name="p")
        session.add(project)
        await session.flush()
        issued = await create_api_key(session, project=project)
        await session.commit()

    assert issued.plaintext.startswith("cx_live_")
    assert issued.plaintext.count("_") == 3
    assert issued.api_key.secret_hash != issued.plaintext

    async with sessionmaker() as session:
        result = await verify_api_key(session, issued.plaintext)
        assert result is not None
        proj, key = result
        assert proj.id == issued.api_key.project_id
        assert key.id == issued.api_key.id


@pytest.mark.asyncio
async def test_verify_unknown_key_returns_none(sessionmaker) -> None:
    async with sessionmaker() as session:
        assert (
            await verify_api_key(
                session,
                "cx_live_00000000_11111111111111111111111111111111",
            )
            is None
        )


@pytest.mark.asyncio
async def test_verify_malformed_key_returns_none(sessionmaker) -> None:
    async with sessionmaker() as session:
        assert await verify_api_key(session, "garbage") is None
        assert await verify_api_key(session, "cx_live_only") is None
        assert await verify_api_key(session, "wrong_prefix_aa_bb") is None


@pytest.mark.asyncio
async def test_revoked_key_fails_verification(sessionmaker) -> None:
    async with sessionmaker() as session:
        project = models.Project(name="p")
        session.add(project)
        await session.flush()
        issued = await create_api_key(session, project=project)
        await session.commit()

    async with sessionmaker() as session:
        key = await session.get(models.ProjectApiKey, issued.api_key.id)
        await revoke_api_key(session, key)
        await session.commit()

    async with sessionmaker() as session:
        assert await verify_api_key(session, issued.plaintext) is None


@pytest.mark.asyncio
async def test_wrong_secret_with_real_prefix_fails(sessionmaker) -> None:
    async with sessionmaker() as session:
        project = models.Project(name="p")
        session.add(project)
        await session.flush()
        issued = await create_api_key(session, project=project)
        await session.commit()

    parts = issued.plaintext.split("_")
    tampered = "_".join(parts[:3] + ["0" * 32])
    async with sessionmaker() as session:
        assert await verify_api_key(session, tampered) is None


@pytest.mark.asyncio
async def test_revoke_sets_timestamp(sessionmaker) -> None:
    async with sessionmaker() as session:
        project = models.Project(name="p")
        session.add(project)
        await session.flush()
        issued = await create_api_key(session, project=project)
        before = datetime.now(timezone.utc)
        await revoke_api_key(session, issued.api_key)
        await session.commit()
        assert issued.api_key.revoked_at is not None
        assert issued.api_key.revoked_at >= before
