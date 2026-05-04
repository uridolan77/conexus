"""Provider configuration service for M3 BO flows."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GatewayModelAlias, ProviderConfig
from app.llm.anthropic_adapter import AnthropicProvider
from app.llm.errors import ProviderError
from app.llm.openai_adapter import OpenAIProvider
from app.services.secret_crypto import decrypt_secret, encrypt_secret


class _ProviderLike(Protocol):
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> Any: ...

    async def aclose(self) -> None: ...


ProviderFactory = Callable[[str, str], _ProviderLike]


def _default_provider_factory(provider_name: str, api_key: str) -> _ProviderLike:
    if provider_name == "openai":
        return OpenAIProvider(api_key=api_key)
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key)
    raise ValueError(f"unsupported provider: {provider_name}")


_provider_factory: ProviderFactory = _default_provider_factory


def set_provider_factory_for_tests(factory: ProviderFactory) -> None:
    global _provider_factory
    _provider_factory = factory


def reset_provider_factory_for_tests() -> None:
    global _provider_factory
    _provider_factory = _default_provider_factory


@dataclass(slots=True)
class ProviderTestResult:
    status: str
    latency_ms: int
    error: str | None = None


def mask_api_key(secret: str) -> str:
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}...{secret[-4:]}"


def sanitize_error(message: str, secret: str) -> str:
    sanitized = message.replace(secret, "[redacted]")
    if len(sanitized) > 240:
        return sanitized[:240]
    return sanitized


async def list_provider_configs(session: AsyncSession) -> list[ProviderConfig]:
    stmt = select(ProviderConfig).order_by(ProviderConfig.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def list_enabled_provider_configs(session: AsyncSession) -> list[ProviderConfig]:
    stmt = (
        select(ProviderConfig)
        .where(ProviderConfig.is_active.is_(True), ProviderConfig.revoked_at.is_(None))
        .order_by(ProviderConfig.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_active_gateway_model_alias(
    session: AsyncSession, alias: str
) -> GatewayModelAlias | None:
    stmt = select(GatewayModelAlias).where(
        GatewayModelAlias.alias == alias,
        GatewayModelAlias.status == "active",
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_provider_config(
    session: AsyncSession,
    *,
    provider: str,
    api_key: str,
    label: str | None,
) -> ProviderConfig:
    row = ProviderConfig(
        provider=provider,
        label=label,
        api_key_encrypted=encrypt_secret(api_key),
        key_mask=mask_api_key(api_key),
        is_active=True,
    )
    session.add(row)
    await session.flush()
    return row


async def revoke_provider_config(
    session: AsyncSession, row: ProviderConfig
) -> ProviderConfig:
    from datetime import datetime, timezone

    row.is_active = False
    row.revoked_at = datetime.now(timezone.utc)
    await session.flush()
    return row


async def test_provider_config(
    session: AsyncSession,
    row: ProviderConfig,
    *,
    model: str,
) -> ProviderTestResult:
    from datetime import datetime, timezone

    started = time.monotonic()
    secret = decrypt_secret(row.api_key_encrypted)
    provider_name = row.provider.lower()

    provider = _provider_factory(provider_name, secret)
    try:
        await provider.chat(
            [{"role": "user", "content": "Reply with OK."}],
            model=model,
            max_tokens=8,
            temperature=0,
        )
    except Exception as exc:
        msg = sanitize_error(str(exc), secret)
        row.last_test_status = "failed"
        row.last_test_error = msg
        row.last_tested_at = datetime.now(timezone.utc)
        await session.flush()
        if isinstance(exc, ProviderError):
            return ProviderTestResult(
                status="failed",
                latency_ms=int((time.monotonic() - started) * 1000),
                error=msg,
            )
        return ProviderTestResult(
            status="failed",
            latency_ms=int((time.monotonic() - started) * 1000),
            error="provider test failed",
        )
    finally:
        await provider.aclose()

    row.last_test_status = "ok"
    row.last_test_error = None
    row.last_tested_at = datetime.now(timezone.utc)
    await session.flush()
    return ProviderTestResult(
        status="ok",
        latency_ms=int((time.monotonic() - started) * 1000),
        error=None,
    )
