from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog
from app.services.admin_auth_service import AdminSession


_REDACT_KEYS = {
    "api_key",
    "apiKey",
    "api_key_encrypted",
    "authorization",
    "cookie",
    "cookies",
    "set-cookie",
    "secret",
    "secret_hash",
    "password",
    "password_hash",
    "prompt",
    "response",
    "messages",
    "input",
    "output",
}


def _sanitize_json_value(value: Any, *, _depth: int = 0) -> Any:
    if _depth > 6:
        return "[truncated]"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if key in _REDACT_KEYS:
                out[key] = "[redacted]"
                continue
            out[key] = _sanitize_json_value(v, _depth=_depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize_json_value(v, _depth=_depth + 1) for v in value[:200]]
    return str(value)


def _json_dumps_safe(value: Any) -> str:
    return json.dumps(_sanitize_json_value(value), ensure_ascii=False, separators=(",", ":"))


async def log_admin_action(
    session: AsyncSession,
    *,
    actor: AdminSession | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: Any | None = None,
) -> AuditLog:
    actor_admin_user_id = actor.admin_user_id if actor else None
    actor_username = actor.username if actor else None

    row = AuditLog(
        actor_admin_user_id=actor_admin_user_id,
        actor_username=actor_username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=_json_dumps_safe(metadata) if metadata is not None else None,
    )
    session.add(row)
    await session.flush()
    return row

