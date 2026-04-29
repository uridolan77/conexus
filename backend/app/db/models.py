"""Conexus M2 schema — projects, API keys, request logs.

All timestamps are UTC.

Per docs/07_DATABASE_AUTH.md:
- API key secret is stored hashed (never plaintext); a short prefix is kept
  in the clear so we can look up the row before verifying.
- ``revoked_at`` is the only auth gate; we do not delete rows so audit logs
  stay intact.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    api_keys: Mapped[list[ProjectApiKey]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectLimit(Base):
    """Optional per-project limits/budgets (M8A).

    A row may not exist for older projects; callers should treat missing rows
    as limit_mode="disabled".
    """

    __tablename__ = "project_limits"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    monthly_cost_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_request_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_token_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="disabled"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class ProjectApiKey(Base):
    __tablename__ = "project_api_keys"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id"), nullable=False, index=True
    )
    # Short identifier shown next to the key in the BO (e.g. ``"a1b2c3d4"``).
    # Looked up first; the secret is then hash-compared.
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    secret_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped[Project] = relationship(back_populates="api_keys")


class GatewayRequest(Base):
    """A single gateway call, logged for monitoring + cost.

    Fields mirror docs/04_GATEWAY.md. ``status`` transitions are
    ``started → completed | failed``. Tokens / cost / completed_at are
    populated only on completion.
    """

    __tablename__ = "gateway_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    request_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    project_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("projects.id"), nullable=True, index=True
    )
    api_key_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("project_api_keys.id"), nullable=True
    )
    requested_model: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    key_mask: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
