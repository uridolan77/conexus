"""Application settings loaded from environment variables.

Mirrors the env shape declared in ``.env.example`` at the repo root.
Keep settings flat for v1; nest them once we have many provider/budget knobs.
"""

from __future__ import annotations

from pydantic import Field
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

    auth_secret: str = Field(default="replace-me-local", alias="AUTH_SECRET")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin", alias="ADMIN_PASSWORD")
    admin_session_ttl_hours: int = Field(default=12, alias="ADMIN_SESSION_TTL_HOURS")
    allow_env_admin_fallback: bool | None = Field(
        default=None, alias="ALLOW_ENV_ADMIN_FALLBACK"
    )
    encryption_key: str = Field(..., alias="ENCRYPTION_KEY")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    llm_provider: str = Field(default="gateway", alias="LLM_PROVIDER")

    @property
    def effective_allow_env_admin_fallback(self) -> bool:
        if self.allow_env_admin_fallback is not None:
            return self.allow_env_admin_fallback
        return self.app_env.lower() != "prod"


settings = Settings()
