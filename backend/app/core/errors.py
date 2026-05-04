"""Conexus domain-error hierarchy.

Every error that crosses a subsystem boundary — LLM gateway, services,
API route — should inherit from :class:`ConexusDomainError`.  A global
FastAPI exception handler can translate it into the canonical JSON envelope::

    {
        "error": {
            "code":    "gateway_error",
            "message": "All configured LLM providers failed",
            "details": {}
        }
    }

Class-level attributes drive the HTTP mapping:

* :attr:`code`        — stable snake_case identifier for frontend copy.
* :attr:`http_status` — HTTP status the handler should return.

Instance-level ``message`` and ``details`` may be overridden per raise::

    raise GatewayError("Anthropic returned 503", provider="anthropic")
"""

from __future__ import annotations

from typing import Any


class ConexusDomainError(Exception):
    """Base class for every domain error surfaced through the HTTP API.

    Subclasses set class-level :attr:`code` and :attr:`http_status`.
    Raise with ``(message, **details)``; the ``**details`` become both
    :attr:`details` dict and instance attributes.
    """

    code: str = "domain_error"
    http_status: int = 500

    def __init__(self, message: str = "", /, **details: Any) -> None:
        self.message: str = message or self.__class__.__doc__ or self.code
        self.details: dict[str, Any] = dict(details)
        for k, v in details.items():
            setattr(self, k, v)
        super().__init__(self.message)

    def to_envelope(self) -> dict[str, Any]:
        """Return the canonical ``{"error": {...}}`` dict for JSON serialisation."""
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return {"error": payload}


# ── 4xx — client errors ───────────────────────────────────────────────


class ValidationError(ConexusDomainError):
    """Request input failed a syntactic or semantic validation check.

    Returns HTTP 400.
    """

    code = "validation_error"
    http_status = 400


class AuthenticationError(ConexusDomainError):
    """Request requires valid authentication credentials.

    Returns HTTP 401.
    """

    code = "authentication_required"
    http_status = 401


class PermissionDeniedError(ConexusDomainError):
    """Authenticated caller lacks the role/scope required for this action.

    Returns HTTP 403.
    """

    code = "permission_denied"
    http_status = 403


class ResourceNotFoundError(ConexusDomainError):
    """Requested resource does not exist or is not visible to the caller.

    Returns HTTP 404.
    """

    code = "resource_not_found"
    http_status = 404


# ── 5xx — server / upstream errors ────────────────────────────────────


class GatewayError(ConexusDomainError):
    """All configured LLM providers failed to produce a response.

    Returns HTTP 502.
    """

    code = "gateway_error"
    http_status = 502


class ServiceUnavailableError(ConexusDomainError):
    """A required internal service is temporarily unavailable.

    Returns HTTP 503.
    """

    code = "service_unavailable"
    http_status = 503


__all__ = [
    "AuthenticationError",
    "ConexusDomainError",
    "GatewayError",
    "PermissionDeniedError",
    "ResourceNotFoundError",
    "ServiceUnavailableError",
    "ValidationError",
]
