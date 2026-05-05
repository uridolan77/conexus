"""Process/worker count introspection for deployment safety checks."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


def detected_worker_process_count() -> int:
    """Best-effort worker count from common hosting env vars.

    Uvicorn ``--workers N`` does not always set env vars; callers may also pass
    ``GATEWAY_ASSUMED_WEB_CONCURRENCY`` when the process supervisor does not
    expose ``WEB_CONCURRENCY``.
    """
    override = os.environ.get("GATEWAY_ASSUMED_WEB_CONCURRENCY", "").strip()
    if override.isdigit():
        return max(1, int(override))
    for key in ("WEB_CONCURRENCY", "UVICORN_WORKERS"):
        raw = os.environ.get(key, "").strip()
        if raw.isdigit():
            return max(1, int(raw))
    return 1


def enforce_hard_limit_worker_safety(*, settings: "Settings", log: logging.Logger) -> None:
    """Fail fast or log loudly when multiple workers run with single-process limit locks."""
    workers = detected_worker_process_count()
    if settings.gateway_hard_limit_distributed_lock_enabled or workers <= 1:
        return
    policy = settings.effective_gateway_hard_limit_multi_worker_policy
    if policy == "ignore":
        return
    msg = (
        f"Detected {workers} worker processes (WEB_CONCURRENCY / UVICORN_WORKERS / "
        "GATEWAY_ASSUMED_WEB_CONCURRENCY) but hard-limit admission uses per-process "
        "asyncio locks that are not shared across workers. Run a single worker, enable "
        "GATEWAY_HARD_LIMIT_DISTRIBUTED_LOCK_ENABLED when coordinated reservations exist, "
        "or set GATEWAY_HARD_LIMIT_MULTI_WORKER_POLICY=ignore (unsafe)."
    )
    if policy == "error":
        raise RuntimeError(msg)
    log.error("gateway_hard_limit_multi_worker_unsafe policy=%s %s", policy, msg)
