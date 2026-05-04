"""LLM provider factory for the gateway layer.

Single entry-point for constructing a :class:`~app.llm.gateway_router.GatewayProvider`
with optionally injectable primary/fallback adapters.

Primary use-cases:

1. **Production** — call ``make_gateway_provider()`` with no arguments; adapters
   are created from ``settings`` (same behaviour as ``GatewayProvider()``).

2. **Tests** — pass explicit ``LLMProvider`` stubs to avoid hitting real API
   keys or making network calls::

       from app.llm.provider_factory import make_gateway_provider

       gateway = make_gateway_provider(primary=stub_anthropic, fallback=stub_openai)
       result  = await gateway.chat([...], model="conexus-fast")
"""

from __future__ import annotations

from app.llm.base import LLMProvider
from app.llm.gateway_router import GatewayProvider

# Sentinel used to distinguish "not passed" from ``None`` (which explicitly
# disables a provider).
_UNSET: object = object()


def make_gateway_provider(
    *,
    primary: LLMProvider | None | object = _UNSET,
    fallback: LLMProvider | None | object = _UNSET,
) -> GatewayProvider:
    """Return a configured :class:`GatewayProvider`.

    Parameters
    ----------
    primary:
        Primary :class:`~app.llm.base.LLMProvider` to use.  When omitted,
        defaults to :class:`~app.llm.anthropic_adapter.AnthropicProvider`
        if ``ANTHROPIC_API_KEY`` is set, otherwise ``None`` (disabled).
    fallback:
        Fallback provider. When omitted, defaults to
        :class:`~app.llm.openai_adapter.OpenAIProvider` if ``OPENAI_API_KEY``
        is set, otherwise ``None``.
    """
    kwargs: dict[str, object] = {}
    if primary is not _UNSET:
        kwargs["primary"] = primary
    if fallback is not _UNSET:
        kwargs["fallback"] = fallback
    return GatewayProvider(**kwargs)  # type: ignore[arg-type]
