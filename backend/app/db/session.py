"""Async SQLAlchemy engine + session factory.

Local/dev startup can still call ``Base.metadata.create_all`` for convenience,
but production schema changes are represented by Alembic revisions under
``app/db/migrations``. Run migrations before starting prod with
``ALLOW_CREATE_ALL=false``.

Tests override ``DATABASE_URL`` with ``sqlite+aiosqlite:///:memory:`` (or a
file path) so the gateway tests don't need a Postgres container.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.engine.url import make_url
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
        url = make_url(settings.database_url)
        is_sqlite = url.get_backend_name() == "sqlite"

        engine_kwargs: dict[str, object] = {
            "echo": False,
            "pool_pre_ping": True,
            "future": True,
        }
        # SQLite test engines may not accept queue-pool sizing options. Apply
        # pool config only where it is expected to work (e.g. Postgres).
        if not is_sqlite:
            if settings.db_pool_size is not None:
                engine_kwargs["pool_size"] = settings.db_pool_size
            if settings.db_max_overflow is not None:
                engine_kwargs["max_overflow"] = settings.db_max_overflow
            if settings.db_pool_timeout is not None:
                engine_kwargs["pool_timeout"] = settings.db_pool_timeout

        _engine = create_async_engine(
            settings.database_url,
            **engine_kwargs,
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
