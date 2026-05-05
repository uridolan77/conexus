"""Application settings loaded from environment variables.

Mirrors the env shape declared in ``.env.example`` at the repo root.
Keep settings flat for v1; nest them once we have many provider/budget knobs.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+asyncpg://conexus:conexus@localhost:5432/conexus",
        alias="DATABASE_URL",
    )

    backend_base_url: str = Field(
        default="http://localhost:8000", alias="BACKEND_BASE_URL"
    )
    frontend_base_url: str = Field(
        default="http://localhost:3000", alias="FRONTEND_BASE_URL"
    )
    adaptation_api_base_url: str | None = Field(
        default=None, alias="ADAPTATION_API_BASE_URL"
    )

    internal_adapter_api_key: str | None = Field(default=None, alias="INTERNAL_ADAPTER_API_KEY")

    adapter_profile_registry_enabled: bool = Field(
        default=True, alias="ADAPTER_PROFILE_REGISTRY_ENABLED"
    )
    adapter_profile_canary_routing_enabled: bool = Field(
        default=False, alias="ADAPTER_PROFILE_CANARY_ROUTING_ENABLED"
    )

    adapter_profile_observability_enabled: bool = Field(
        default=True, alias="ADAPTER_PROFILE_OBSERVABILITY_ENABLED"
    )

    cors_allowed_origins: str | None = Field(default=None, alias="CORS_ALLOWED_ORIGINS")
    frontend_origins: str | None = Field(default=None, alias="FRONTEND_ORIGINS")

    auth_secret: str = Field(default="replace-me-local", alias="AUTH_SECRET")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin", alias="ADMIN_PASSWORD")
    admin_session_ttl_hours: int = Field(default=12, alias="ADMIN_SESSION_TTL_HOURS")
    cookie_secure: bool | None = Field(default=None, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="lax", alias="COOKIE_SAMESITE")
    allow_env_admin_fallback: bool | None = Field(
        default=None, alias="ALLOW_ENV_ADMIN_FALLBACK"
    )
    enable_static_admin_fallback: bool = Field(
        default=False, alias="ENABLE_STATIC_ADMIN_FALLBACK"
    )
    allow_static_bootstrap_when_no_db_admins: bool = Field(
        default=True, alias="ALLOW_STATIC_BOOTSTRAP_WHEN_NO_DB_ADMINS"
    )
    gateway_hard_limit_distributed_lock_enabled: bool = Field(
        default=False, alias="GATEWAY_HARD_LIMIT_DISTRIBUTED_LOCK_ENABLED"
    )
    gateway_hard_limit_multi_worker_policy: str = Field(
        default="auto",
        alias="GATEWAY_HARD_LIMIT_MULTI_WORKER_POLICY",
        description='One of "auto" (prod=error, else=warn), "error", "warn", "ignore".',
    )
    allow_create_all: bool | None = Field(default=None, alias="ALLOW_CREATE_ALL")
    encryption_key: str = Field(..., alias="ENCRYPTION_KEY")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    llm_provider: str = Field(default="gateway", alias="LLM_PROVIDER")

    llm_request_timeout_seconds: int = Field(
        default=60, alias="LLM_REQUEST_TIMEOUT_SECONDS", ge=1
    )
    llm_stream_timeout_seconds: int = Field(
        default=180, alias="LLM_STREAM_TIMEOUT_SECONDS", ge=1
    )

    # Stale limit reservation repair (v0.8): classify unreconciled rows older than this.
    limit_reservation_stale_after_seconds: int = Field(
        default=900, alias="LIMIT_RESERVATION_STALE_AFTER_SECONDS", ge=60
    )
    # After this age, "started but not completed" reservations may be force-repaired as failed.
    limit_reservation_force_repair_after_seconds: int = Field(
        default=3600, alias="LIMIT_RESERVATION_FORCE_REPAIR_AFTER_SECONDS", ge=300
    )
    # When false, hard-limit admission uses only ProjectUsageWindow counters (no
    # per-request scans of gateway_requests). Enable legacy fallbacks until
    # windows are verified in production, then set to false in staging/prod.
    use_legacy_hard_limit_gateway_fallbacks: bool = Field(
        default=True, alias="USE_LEGACY_HARD_LIMIT_GATEWAY_FALLBACKS"
    )

    admin_login_max_failures: int = Field(default=5, alias="ADMIN_LOGIN_MAX_FAILURES", ge=1)
    admin_login_window_seconds: int = Field(
        default=600, alias="ADMIN_LOGIN_WINDOW_SECONDS", ge=30
    )
    # Only ``in_memory`` is implemented; values other than ``in_memory`` are rejected at
    # validation time. Redis/distributed limiting is not wired yet.
    admin_login_rate_limit_backend: str = Field(
        default="in_memory",
        alias="ADMIN_LOGIN_RATE_LIMIT_BACKEND",
        description='Login rate limit store: only "in_memory" is supported today.',
    )

    model_aliases_path: str = Field(
        default_factory=lambda: str(
            Path(__file__).resolve().parents[2] / "static_config" / "model_aliases.yaml"
        ),
        alias="MODEL_ALIASES_PATH",
    )

    @field_validator("model_aliases_path", mode="before")
    @classmethod
    def _resolve_model_aliases_path(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("MODEL_ALIASES_PATH must be a string")
        raw = value.strip()
        if not raw:
            raise ValueError("MODEL_ALIASES_PATH must not be empty")
        p = Path(raw)
        if p.is_absolute():
            return str(p)

        # Support common relative values from `.env` like:
        # - backend/static_config/model_aliases.yaml (repo-root relative)
        # - static_config/model_aliases.yaml (backend-root relative)
        backend_root = Path(__file__).resolve().parents[2]  # .../backend
        repo_root = backend_root.parent  # .../conexus

        candidates = [
            (repo_root / p),
            (backend_root / p),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        # Fall back to repo-root relative (helps error messages be stable)
        return str(repo_root / p)

    @field_validator("admin_login_rate_limit_backend", mode="before")
    @classmethod
    def _normalize_admin_login_rate_limit_backend(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("ADMIN_LOGIN_RATE_LIMIT_BACKEND must be a string")
        return value.strip().lower()

    @field_validator("admin_username")
    @classmethod
    def _validate_admin_username_no_pipe(cls, value: str) -> str:
        if "|" in value:
            raise ValueError(
                "ADMIN_USERNAME must not contain '|' (reserved for admin session token encoding)"
            )
        return value

    @field_validator("admin_login_rate_limit_backend")
    @classmethod
    def _validate_admin_login_rate_limit_backend(cls, value: str) -> str:
        allowed = {"in_memory"}  # extend with ``redis`` when implemented
        if value not in allowed:
            raise ValueError(
                'ADMIN_LOGIN_RATE_LIMIT_BACKEND must be "in_memory" '
                "(distributed backends are not wired yet)"
            )
        return value

    @field_validator("cookie_samesite", mode="before")
    @classmethod
    def _normalize_cookie_samesite(cls, value: object) -> str:
        if value is None:
            return "lax"
        if not isinstance(value, str):
            raise TypeError("COOKIE_SAMESITE must be a string")
        return value.strip().lower()

    @field_validator("cookie_samesite")
    @classmethod
    def _validate_cookie_samesite(cls, value: str) -> str:
        allowed = {"lax", "strict", "none"}
        if value not in allowed:
            raise ValueError("COOKIE_SAMESITE must be one of: lax, strict, none")
        return value

    @model_validator(mode="after")
    def _validate_cookie_policy(self) -> "Settings":
        # Browsers require SameSite=None cookies to also be Secure.
        if self.app_env.lower() == "prod" and self.cookie_samesite == "none":
            if not self.effective_cookie_secure:
                raise ValueError(
                    "In APP_ENV=prod, COOKIE_SAMESITE=none requires COOKIE_SECURE=true"
                )
        return self

    @property
    def effective_allow_env_admin_fallback(self) -> bool:
        if self.allow_env_admin_fallback is not None:
            return self.allow_env_admin_fallback
        if self.enable_static_admin_fallback:
            return True
        return self.allow_static_bootstrap_when_no_db_admins and self.app_env.lower() != "prod"

    @property
    def effective_gateway_hard_limit_multi_worker_policy(self) -> str:
        raw = self.gateway_hard_limit_multi_worker_policy.strip().lower()
        if raw in ("error", "warn", "ignore"):
            return raw
        if raw in ("auto", ""):
            return "error" if self.app_env.lower() == "prod" else "warn"
        return "warn"

    @property
    def effective_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.app_env.lower() == "prod"

    @property
    def effective_allow_create_all(self) -> bool:
        if self.allow_create_all is not None:
            return self.allow_create_all
        # Default: keep dev/test convenient; prod should run Alembic explicitly.
        return self.app_env.lower() != "prod"

    @property
    def effective_cors_origins(self) -> list[str]:
        raw = (self.cors_allowed_origins or self.frontend_origins or "").strip()
        if raw:
            origins = [o.strip() for o in raw.split(",") if o.strip()]
        else:
            origins = [self.frontend_base_url]

        if self.app_env.lower() != "prod":
            for local in ("http://localhost:3000", "http://127.0.0.1:3000"):
                if local not in origins:
                    origins.append(local)
        return origins


settings = Settings()
