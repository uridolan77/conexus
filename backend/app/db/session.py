"""Async SQLAlchemy engine + session factory.

V1 keeps the schema small enough that we can ``Base.metadata.create_all`` on
startup. Alembic comes back when M3 introduces multi-environment migrations.

Tests override ``DATABASE_URL`` with ``sqlite+aiosqlite:///:memory:`` (or a
file path) so the gateway tests don't need a Postgres container.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _sessionmaker


def reset_engine() -> None:
    """Drop the cached engine + sessionmaker.

    Used by tests after they swap ``settings.database_url`` so that the next
    ``get_engine()`` call rebuilds against the new URL.
    """
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None


async def init_db(*, allow_create_all: bool = True) -> None:
    """Create all tables on startup (optional).

    M2 schema only — projects, project_api_keys, gateway_requests. Real
    migrations land in a later milestone.
    """
    from app.db import models  # noqa: F401  ensure models are registered

    engine = get_engine()
    async with engine.begin() as conn:
        if allow_create_all:
            await conn.run_sync(models.Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a session and committing on success."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_db_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """FastAPI dependency that yields the process-scoped sessionmaker.

    Used by the gateway service so that request-log writes can manage their
    own short-lived sessions, independent of any request-level transaction.
    """
    return get_sessionmaker()
