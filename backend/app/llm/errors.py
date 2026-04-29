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
