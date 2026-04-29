"""Conexus FastAPI entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api import health
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Conexus",
        version="0.0.1",
        docs_url="/docs",
        redoc_url=None,
    )
    app.include_router(health.router)
    logger.info("conexus_app_started", extra={"env": settings.app_env})
    return app


app = create_app()
