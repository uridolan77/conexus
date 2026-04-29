"""Conexus FastAPI entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin_auth,
    admin_project_limits,
    admin_projects,
    admin_providers,
    admin_requests,
    admin_routing,
    admin_usage,
    gateway,
    health,
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.llm.dependencies import shutdown_provider
from app.services.secret_crypto import SecretCryptoError, ensure_encryption_ready

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


def _ensure_prod_secret_hardening() -> None:
    if settings.app_env.lower() != "prod":
        return
    problems: list[str] = []
    if settings.auth_secret == "replace-me-local":
        problems.append("AUTH_SECRET uses default")
    if settings.admin_password == "admin":
        problems.append("ADMIN_PASSWORD uses default")
    if problems:
        details = ", ".join(problems)
        raise RuntimeError(f"unsafe production config: {details}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _ensure_prod_secret_hardening()
    try:
        ensure_encryption_ready()
    except SecretCryptoError as exc:
        raise RuntimeError(
            "invalid ENCRYPTION_KEY: expected a valid Fernet key"
        ) from exc
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_base_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(gateway.router)
    app.include_router(admin_auth.router)
    app.include_router(admin_providers.router)
    app.include_router(admin_projects.router)
    app.include_router(admin_project_limits.router)
    app.include_router(admin_requests.router)
    app.include_router(admin_usage.router)
    app.include_router(admin_routing.router)
    logger.info("conexus_app_started env=%s", settings.app_env)
    return app


app = create_app()
