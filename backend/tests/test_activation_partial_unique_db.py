"""DB-level uniqueness for adapter activations (SQLite create_all)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.domain_enums import GatewayAdapterProfileActivationStatus
from app.db import models
from app.db.models import GatewayAdapterProfileActivation


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_partial_unique_rejects_second_active_same_domain(db_engine) -> None:
    sm = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with sm() as session:
        session.add_all(
            [
                GatewayAdapterProfileActivation(
                    domain_key="d1",
                    gateway_profile_id="gw-a",
                    status=GatewayAdapterProfileActivationStatus.ACTIVE,
                ),
                GatewayAdapterProfileActivation(
                    domain_key="d1",
                    gateway_profile_id="gw-b",
                    status=GatewayAdapterProfileActivationStatus.ACTIVE,
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_partial_unique_allows_active_different_domains(db_engine) -> None:
    sm = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with sm() as session:
        session.add_all(
            [
                GatewayAdapterProfileActivation(
                    domain_key="d1",
                    gateway_profile_id="gw-a",
                    status=GatewayAdapterProfileActivationStatus.ACTIVE,
                ),
                GatewayAdapterProfileActivation(
                    domain_key="d2",
                    gateway_profile_id="gw-b",
                    status=GatewayAdapterProfileActivationStatus.ACTIVE,
                ),
            ]
        )
        await session.commit()
