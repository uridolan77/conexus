"""Health endpoints (M0)."""

from __future__ import annotations

from fastapi import HTTPException, status
from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    # Cheap readiness check: can we talk to the database?
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        # Do not expose DB URL/credentials in the response.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready"},
        )
    return {"status": "ready"}
