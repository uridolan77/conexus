"""Normalised gateway errors.

Replaces KGB's ``app.api.errors.GatewayError`` / ``BudgetExceededError``
with a small set of provider-shaped exceptions the gateway can map to
HTTP responses.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for provider-related errors."""

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class ProviderRateLimitError(ProviderError):
    """Provider returned 429 (or equivalent)."""


class ProviderUnavailableError(ProviderError):
    """Provider returned a transient 5xx / connection error."""


class AllProvidersFailedError(ProviderError):
    """No configured provider could serve the request."""

    def __init__(self, message: str = "All configured LLM providers failed"):
        super().__init__(message)


class UnknownModelError(ValueError):
    """Caller asked for a model alias the gateway does not know.

    Distinct from ``ProviderError`` so callers can distinguish a client
    misconfiguration (typo, unsupported alias) from a runtime provider
    failure. Subclasses ``ValueError`` so framework default handlers map
    it to a 4xx rather than a 5xx.
    """

    def __init__(
        self,
        model: str,
        *,
        known_aliases: list[str] | None = None,
        provider_prefixes: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        parts: list[str] = [f"unknown model alias: {model!r}."]
        if known_aliases:
            parts.append(f"Known aliases: {', '.join(sorted(known_aliases))}.")
        if provider_prefixes:
            bits = [
                f"{name}: {', '.join(prefs)}"
                for name, prefs in sorted(provider_prefixes.items())
            ]
            parts.append(f"Accepted provider model prefixes: {'; '.join(bits)}.")
        super().__init__(" ".join(parts))
        self.model = model
