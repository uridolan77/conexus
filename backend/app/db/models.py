"""Conexus persistence schema: auth, request logs, usage, BO, and adapter state.

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
    UniqueConstraint,
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


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    roles_json: Mapped[str] = mapped_column(Text, nullable=False, default='["Admin"]')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    actor_admin_user_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("admin_users.id"), nullable=True, index=True
    )
    actor_username: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    actor_admin_user: Mapped[AdminUser | None] = relationship()


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


class ProjectUsageWindow(Base):
    """Aggregated reserved/completed usage per UTC window for strict limit admission."""

    __tablename__ = "project_usage_windows"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "window_kind",
            "window_start_utc",
            name="uq_project_usage_windows_project_kind_start",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id"), nullable=False, index=True
    )
    window_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    window_start_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    window_end_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    request_count_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_count_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_reserved: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_completed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class ProjectGatewayLimitReservation(Base):
    """Per-gateway-call reservation snapshot for reconcile after provider completes."""

    __tablename__ = "project_gateway_limit_reservations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id"), nullable=False, index=True
    )
    daily_window_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("project_usage_windows.id"), nullable=False
    )
    monthly_window_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("project_usage_windows.id"), nullable=True
    )
    request_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tokens_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_reserved: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
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
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    gateway_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    adapter_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domain_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    adaptation_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    limit_reservation_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("project_gateway_limit_reservations.id"), nullable=True
    )


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    gateway_request_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("gateway_requests.id"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    requested_model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )


class GatewayModelAlias(Base):
    __tablename__ = "gateway_model_aliases"
    __table_args__ = (
        UniqueConstraint("alias", name="uq_gateway_model_aliases_alias"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    alias: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    primary_provider: Mapped[str] = mapped_column(String(40), nullable=False)
    primary_model: Mapped[str] = mapped_column(String(120), nullable=False)
    fallback_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fallback_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class GatewayAdapterProfile(Base):
    __tablename__ = "gateway_adapter_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    gateway_profile_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    adapter_profile_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    domain_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    profile_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Registered", index=True)
    source_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    semantic_context_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    slod_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GatewayAdapterProfileActivation(Base):
    __tablename__ = "gateway_adapter_profile_activations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    domain_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    gateway_profile_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    canary_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_gateway_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


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
