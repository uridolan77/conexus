"""Read-only routing policy description for the back office."""

from __future__ import annotations

from pydantic import BaseModel

from app.llm.gateway_router import get_known_provider_prefixes, get_model_aliases


class AliasRoute(BaseModel):
    alias: str
    primary_provider: str
    primary_model: str
    fallback_provider: str
    fallback_model: str


class DirectRoute(BaseModel):
    provider: str
    model_prefixes: list[str]
    fallback_enabled: bool


class RoutingPolicy(BaseModel):
    id: str
    name: str
    mode: str
    default_alias: str
    aliases: list[AliasRoute]
    direct_routes: list[DirectRoute]


def get_default_routing_policy() -> RoutingPolicy:
    aliases = [
        AliasRoute(
            alias=alias,
            primary_provider="anthropic",
            primary_model=anthropic_model,
            fallback_provider="openai",
            fallback_model=openai_model,
        )
        for alias, (anthropic_model, openai_model) in sorted(get_model_aliases().items())
    ]
    prefixes = get_known_provider_prefixes()
    return RoutingPolicy(
        id="default",
        name="Default gateway policy",
        mode="static",
        default_alias="conexus-default",
        aliases=aliases,
        direct_routes=[
            DirectRoute(
                provider="anthropic",
                model_prefixes=list(prefixes["anthropic"]),
                fallback_enabled=False,
            ),
            DirectRoute(
                provider="openai",
                model_prefixes=list(prefixes["openai"]),
                fallback_enabled=False,
            ),
        ],
    )
