"""Health endpoints (M0)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    # M0: liveness only. M1+ will check DB and (eventually) provider keys.
    return {"status": "ready"}
