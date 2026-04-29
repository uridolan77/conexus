"""Conexus FastAPI entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import gateway, health
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.llm.dependencies import shutdown_provider

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    logger.info("conexus_db_ready url=%s", _redacted_db_url(settings.database_url))
    try:
        yield
    finally:
        await shutdown_provider()


def _redacted_db_url(url: str) -> str:
    # Hide credentials in logs.
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            _, host = rest.split("@", 1)
            return f"{scheme}://***@{host}"
    return url


def create_app() -> FastAPI:
    app = FastAPI(
        title="Conexus",
        version="0.0.1",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(gateway.router)
    logger.info("conexus_app_started env=%s", settings.app_env)
    return app


app = create_app()
