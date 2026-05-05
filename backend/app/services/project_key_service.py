"""Project API key generation and verification.

Key format (docs/07_DATABASE_AUTH.md):

    cx_live_<prefix>_<secret>

- ``cx_live`` — environment-aware prefix; literal for now, may become
  ``cx_test`` in non-prod environments later.
- ``<prefix>`` — 8 hex chars, stored in the clear so we can index a row.
- ``<secret>`` — 32 hex chars (~128 bits of entropy). Never stored in
  the clear — only its sha256 lives in the DB.

The shown-once plaintext key returned from :func:`create_api_key` is the
only opportunity to reveal the secret to the operator.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project, ProjectApiKey

_KEY_PREFIX = "cx_live"
_PREFIX_BYTES = 4  # 8 hex chars
_SECRET_BYTES = 16  # 32 hex chars
_LAST_USED_TOUCH_INTERVAL = timedelta(seconds=60)


@dataclass(slots=True)
class IssuedKey:
    """The full plaintext key plus the persisted DB row.

    The plaintext is only available at creation time and is the value the
    operator must copy. After this point only the hash + prefix exist.
    """

    plaintext: str
    api_key: ProjectApiKey


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _parse_key(token: str) -> tuple[str, str] | None:
    parts = token.split("_")
    if len(parts) != 4:
        return None
    head, env, prefix, secret = parts
    if f"{head}_{env}" != _KEY_PREFIX:
        return None
    if not prefix or not secret:
        return None
    return prefix, secret


def _should_touch_last_used_at(
    last_used_at: datetime | None, *, now: datetime
) -> bool:
    if last_used_at is None:
        return True
    if last_used_at.tzinfo is None:
        last_used_at = last_used_at.replace(tzinfo=timezone.utc)
    return now - last_used_at >= _LAST_USED_TOUCH_INTERVAL


async def create_api_key(
    session: AsyncSession,
    *,
    project: Project,
    label: str | None = None,
) -> IssuedKey:
    """Generate a new API key, persist its hash, and return the plaintext."""
    prefix = secrets.token_hex(_PREFIX_BYTES)
    secret = secrets.token_hex(_SECRET_BYTES)
    plaintext = f"{_KEY_PREFIX}_{prefix}_{secret}"
    api_key = ProjectApiKey(
        project_id=project.id,
        prefix=prefix,
        secret_hash=_hash_secret(secret),
        label=label,
    )
    session.add(api_key)
    await session.flush()
    return IssuedKey(plaintext=plaintext, api_key=api_key)


async def verify_api_key(
    session: AsyncSession, token: str
) -> tuple[Project, ProjectApiKey] | None:
    """Resolve a plaintext key to its project + key row.

    Returns ``None`` when the key is malformed, unknown, or revoked.
    The hash comparison is constant-time.
    """
    parsed = _parse_key(token)
    if parsed is None:
        return None
    prefix, secret = parsed
    stmt = (
        select(ProjectApiKey, Project)
        .join(Project, Project.id == ProjectApiKey.project_id)
        .where(ProjectApiKey.prefix == prefix)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    api_key, project = row
    if api_key.revoked_at is not None:
        return None
    if not hmac.compare_digest(api_key.secret_hash, _hash_secret(secret)):
        return None
    now = datetime.now(timezone.utc)
    if _should_touch_last_used_at(api_key.last_used_at, now=now):
        api_key.last_used_at = now
        await session.flush()
    return project, api_key


async def revoke_api_key(session: AsyncSession, api_key: ProjectApiKey) -> None:
    api_key.revoked_at = datetime.now(timezone.utc)
    await session.flush()
