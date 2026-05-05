"""Unit tests for adaptation admin proxy helpers."""

from __future__ import annotations

from app.services.adaptation_proxy_service import (
    strip_browser_identity_and_roles_fields,
    trim_optional_reason,
)


def test_strip_browser_identity_removes_snake_and_camel_variants() -> None:
    body: dict[str, object] = {
        "requestedByUserId": "evil",
        "requested_by_user_id": "evil2",
        "CreatedByUserId": "evil3",
        "roles": ["admin"],
        "ApproverRoles": ["x"],
        "safeField": "keep",
    }
    strip_browser_identity_and_roles_fields(body)
    assert body == {"safeField": "keep"}


def test_trim_optional_reason_drops_blank_reason() -> None:
    body: dict[str, object] = {"reason": "  \t  "}
    trim_optional_reason(body)
    assert "reason" not in body


def test_trim_optional_reason_keeps_non_blank() -> None:
    body: dict[str, object] = {"reason": "  outage  "}
    trim_optional_reason(body)
    assert body["reason"] == "  outage  ".strip()
