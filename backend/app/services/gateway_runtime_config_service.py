"""Runtime provider resolution for gateway requests.

Resolution policy (M2/M3 smoke readiness):

1. BO provider configs (active + not revoked) take precedence per provider.
2. Environment keys are used as fallback when BO config for a provider is absent
   or unusable.
3. If neither source yields a usable provider for the selected runtime mode,
   return ``None`` so caller can keep current default behavior.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.llm import LLMProvider
from app.llm.anthropic_adapter import AnthropicProvider
from app.llm.gateway_router import GatewayProvider
from app.llm.openai_adapter import OpenAIProvider
from app.services.provider_config_service import list_enabled_provider_configs
from app.services.secret_crypto import SecretCryptoError, decrypt_secret

logger = logging.getLogger(__name__)


def _provider_from_env(provider_name: str) -> LLMProvider | None:
    if provider_name == "openai" and settings.openai_api_key:
        return OpenAIProvider(api_key=settings.openai_api_key)
    if provider_name == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider(api_key=settings.anthropic_api_key)
    return None


async def _providers_from_bo(session: AsyncSession) -> dict[str, LLMProvider]:
    rows = await list_enabled_provider_configs(session)

    # list_enabled_provider_configs returns newest first. Keep the first usable
    # row per provider for deterministic precedence.
    providers: dict[str, LLMProvider] = {}
    for row in rows:
        provider_name = (row.provider or "").strip().lower()
        if provider_name in providers:
            continue
        if provider_name not in ("openai", "anthropic"):
            continue
        try:
            secret = decrypt_secret(row.api_key_encrypted)
        except SecretCryptoError:
            logger.warning(
                "gateway_bo_provider_secret_decrypt_failed config_id=%s provider=%s",
                row.id,
                provider_name,
            )
            continue
        if provider_name == "openai":
            providers[provider_name] = OpenAIProvider(api_key=secret)
        elif provider_name == "anthropic":
            providers[provider_name] = AnthropicProvider(api_key=secret)

    return providers


async def resolve_request_provider(session: AsyncSession) -> LLMProvider | None:
    """Resolve request-scoped provider from BO configs and env fallback.

    Returns:
        - request-scoped provider instance when resolution succeeds, or
        - None to let caller use existing default provider behavior.
    """

    bo = await _providers_from_bo(session)

    chosen = settings.llm_provider.lower()
    if chosen == "openai":
        return bo.get("openai") or _provider_from_env("openai")
    if chosen == "anthropic":
        return bo.get("anthropic") or _provider_from_env("anthropic")
    if chosen == "gateway":
        primary = bo.get("anthropic") or _provider_from_env("anthropic")
        fallback = bo.get("openai") or _provider_from_env("openai")
        if primary is None and fallback is None:
            return None
        return GatewayProvider(primary=primary, fallback=fallback)

    return None
