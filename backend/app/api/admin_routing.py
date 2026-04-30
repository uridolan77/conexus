"""Admin routing policy endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
from app.core.config import settings
from app.llm.gateway_router import get_known_provider_prefixes
from app.llm.model_alias_config import load_model_alias_config
from app.services.provider_candidate_service import (
    ProviderCandidate,
    list_provider_candidates,
)
from app.services.routing_policy_service import RoutingPolicy, get_default_routing_policy

router = APIRouter(prefix="/admin/routing", tags=["admin"])


@router.get("/policy", response_model=RoutingPolicy)
async def get_routing_policy(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
) -> RoutingPolicy:
    return get_default_routing_policy()


@router.get("/provider-candidates", response_model=list[ProviderCandidate])
async def get_provider_candidates(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProviderCandidate]:
    return await list_provider_candidates(session)


@router.get("/model-aliases")
async def get_model_aliases_endpoint(
    _admin: Annotated[AdminSession, Depends(get_admin_session)],
) -> dict[str, object]:
    cfg = load_model_alias_config(settings.model_aliases_path)
    aliases = {
        name: {"anthropic": models[0], "openai": models[1]}
        for name, models in cfg.aliases.items()
    }
    known_prefixes = get_known_provider_prefixes()
    return {
        "default_primary_model": cfg.default_primary_model,
        "default_fallback_model": cfg.default_fallback_model,
        "aliases": aliases,
        "known_provider_prefixes": {
            provider: list(prefixes) for provider, prefixes in known_prefixes.items()
        },
    }
