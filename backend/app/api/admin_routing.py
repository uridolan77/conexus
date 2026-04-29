"""Admin routing policy endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_auth import get_admin_session
from app.db.session import get_session
from app.services.admin_auth_service import AdminSession
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
