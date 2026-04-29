"""Health and readiness endpoints."""

from __future__ import annotations

import logging
from importlib import metadata

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_engine
from app.llm.model_alias_config import ModelAliasConfigError, load_model_alias_config
from app.services.secret_crypto import SecretCryptoError, ensure_encryption_ready

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def _app_version() -> str:
    try:
        return metadata.version("conexus-backend")
    except metadata.PackageNotFoundError:
        return "unknown"


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "conexus",
        "version": _app_version(),
    }


async def _ready_checks() -> tuple[bool, dict[str, bool]]:
    """Return (all_ok, per-check booleans)."""
    checks: dict[str, bool] = {
        "db": False,
        "encryption": False,
        "model_aliases": False,
    }

    try:
        ensure_encryption_ready()
        checks["encryption"] = True
    except SecretCryptoError:
        logger.exception("readyz_check_encryption_failed")

    try:
        load_model_alias_config(settings.model_aliases_path)
        checks["model_aliases"] = True
    except (ModelAliasConfigError, OSError):
        logger.exception("readyz_check_model_aliases_failed")

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception:
        logger.exception("readyz_check_db_failed")

    return all(checks.values()), checks


@router.get("/readyz")
async def readyz() -> dict[str, object]:
    ok, checks = await _ready_checks()
    if not ok:
        if settings.app_env.lower() == "prod":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready"},
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks},
        )
    return {"status": "ready", "checks": checks}


@router.get("/health/ready")
async def health_ready() -> dict[str, object]:
    """Backward-compatible alias for ``GET /readyz``."""
    return await readyz()
