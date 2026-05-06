"""Unit tests for backend/app/core/errors.py.

Verifies the domain-error hierarchy: status codes, error codes, message
resolution, details propagation, and the ``to_envelope()`` JSON shape.
"""

from __future__ import annotations

import pytest

from app.core.errors import (
    AuthenticationError,
    ConexusDomainError,
    GatewayError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from app.services.gateway_service import GatewayClientError, GatewayLimitError, GatewayUpstreamError


# ── base class behaviour ──────────────────────────────────────────────


class TestConexusDomainError:
    def test_default_message_falls_back_to_code(self) -> None:
        # ConexusDomainError has a docstring, so message = docstring text.
        # Subclasses without docstrings fall through to cls.code.
        err = ConexusDomainError()
        assert err.message  # non-empty
        # Create a bare error-code-only subclass to test the final fallback.
        class _NoDoc(ConexusDomainError):
            code = "bare_error"

        bare = _NoDoc()
        assert bare.message == "bare_error"

    def test_explicit_message_is_preserved(self) -> None:
        err = ConexusDomainError("something went wrong")
        assert err.message == "something went wrong"
        assert str(err) == "something went wrong"

    def test_details_kwargs_are_stored_in_dict(self) -> None:
        err = ConexusDomainError("boom", field="name", limit=42)
        assert err.details == {"field": "name", "limit": 42}

    def test_details_kwargs_become_instance_attrs(self) -> None:
        err = ConexusDomainError("boom", field="name")
        assert err.field == "name"  # type: ignore[attr-defined]

    def test_is_exception(self) -> None:
        with pytest.raises(ConexusDomainError, match="explode"):
            raise ConexusDomainError("explode")


# ── to_envelope ───────────────────────────────────────────────────────


class TestToEnvelope:
    def test_envelope_shape_no_details(self) -> None:
        err = ValidationError("bad input")
        env = err.to_envelope()
        assert set(env) == {"error"}
        inner = env["error"]
        assert inner["code"] == "validation_error"
        assert inner["message"] == "bad input"
        assert "details" not in inner  # omitted when empty

    def test_envelope_includes_details_when_present(self) -> None:
        err = ValidationError("bad input", field="model", got="unknown")
        env = err.to_envelope()
        inner = env["error"]
        assert inner["details"] == {"field": "model", "got": "unknown"}

    def test_gateway_error_envelope(self) -> None:
        err = GatewayError("providers failed", provider="anthropic")
        env = err.to_envelope()
        assert env["error"]["code"] == "gateway_error"
        assert env["error"]["details"]["provider"] == "anthropic"


# ── subclass HTTP statuses & codes ────────────────────────────────────


@pytest.mark.parametrize(
    ("cls", "expected_status", "expected_code"),
    [
        (ValidationError, 400, "validation_error"),
        (AuthenticationError, 401, "authentication_required"),
        (PermissionDeniedError, 403, "permission_denied"),
        (ResourceNotFoundError, 404, "resource_not_found"),
        (GatewayError, 502, "gateway_error"),
        (ServiceUnavailableError, 503, "service_unavailable"),
    ],
)
def test_subclass_http_status_and_code(
    cls: type[ConexusDomainError], expected_status: int, expected_code: str
) -> None:
    err = cls("test")
    assert err.http_status == expected_status
    assert err.code == expected_code


def test_gateway_service_errors_inherit_conexus_domain_error() -> None:
    assert issubclass(GatewayClientError, ConexusDomainError)
    assert issubclass(GatewayLimitError, ConexusDomainError)
    assert issubclass(GatewayUpstreamError, ConexusDomainError)
    client = GatewayClientError("bad", code="bad_request", request_id="r1")
    assert client.http_status == 400
    assert client.code == "bad_request"
    lim = GatewayLimitError(
        "blocked",
        code="daily",
        request_id="r2",
        limit_type="daily",
        current_value=1.0,
        limit_value=2.0,
        window="d",
        reset_at=None,
    )
    assert lim.http_status == 429
    assert lim.limit_type == "daily"


# ── default messages from docstring ──────────────────────────────────


class TestDefaultDocstringMessages:
    def test_authentication_error_default_message_is_not_blank(self) -> None:
        err = AuthenticationError()
        assert err.message  # non-empty — resolved from docstring

    def test_service_unavailable_default_message(self) -> None:
        err = ServiceUnavailableError()
        assert err.message
