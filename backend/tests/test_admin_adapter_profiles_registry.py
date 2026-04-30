"""Unit tests for admin adapter profile registry — metadata redaction."""

from __future__ import annotations

import json

from app.api.admin_adapter_profiles_registry import _is_sensitive_key, _parse_metadata, _redact_metadata


class TestIsSensitiveKey:
    def test_api_key(self):
        assert _is_sensitive_key("api_key")
        assert _is_sensitive_key("API_KEY")
        assert _is_sensitive_key("apiKey")
        assert _is_sensitive_key("apikey")

    def test_token(self):
        assert _is_sensitive_key("token")
        assert _is_sensitive_key("access_token")

    def test_secret(self):
        assert _is_sensitive_key("secret")
        assert _is_sensitive_key("client_secret")

    def test_password(self):
        assert _is_sensitive_key("password")
        assert _is_sensitive_key("PASSWORD")

    def test_authorization(self):
        assert _is_sensitive_key("authorization")
        assert _is_sensitive_key("Authorization")

    def test_bearer(self):
        assert _is_sensitive_key("bearer")
        assert _is_sensitive_key("Bearer")

    def test_key_standalone(self):
        assert _is_sensitive_key("key")
        assert _is_sensitive_key("KEY")

    def test_safe_keys(self):
        assert not _is_sensitive_key("model")
        assert not _is_sensitive_key("provider")
        assert not _is_sensitive_key("composite_score")
        assert not _is_sensitive_key("domain_key")  # contains 'key' but as suffix
        assert not _is_sensitive_key("label")
        assert not _is_sensitive_key("name")


class TestRedactMetadata:
    def test_none_passthrough(self):
        assert _redact_metadata(None) is None

    def test_primitives_passthrough(self):
        assert _redact_metadata("hello") == "hello"
        assert _redact_metadata(42) == 42
        assert _redact_metadata(True) is True

    def test_redacts_api_key(self):
        result = _redact_metadata({"api_key": "sk-abc123"})
        assert result == {"api_key": "[REDACTED]"}

    def test_redacts_token(self):
        result = _redact_metadata({"token": "tok_xyz"})
        assert result == {"token": "[REDACTED]"}

    def test_redacts_secret(self):
        result = _redact_metadata({"secret": "mysecret"})
        assert result == {"secret": "[REDACTED]"}

    def test_redacts_password(self):
        result = _redact_metadata({"password": "hunter2"})
        assert result == {"password": "[REDACTED]"}

    def test_preserves_safe_keys(self):
        result = _redact_metadata({"model": "gpt-4o", "score": 0.95, "label": "prod"})
        assert result == {"model": "gpt-4o", "score": 0.95, "label": "prod"}

    def test_mixed_safe_and_sensitive(self):
        result = _redact_metadata({"model": "gpt-4o", "api_key": "secret", "label": "prod"})
        assert result["model"] == "gpt-4o"
        assert result["api_key"] == "[REDACTED]"
        assert result["label"] == "prod"

    def test_recursive_dict(self):
        result = _redact_metadata({"outer": {"api_key": "secret", "name": "ok"}})
        assert result["outer"]["api_key"] == "[REDACTED]"
        assert result["outer"]["name"] == "ok"

    def test_recursive_list(self):
        result = _redact_metadata([{"token": "t1"}, {"name": "safe"}])
        assert result[0]["token"] == "[REDACTED]"
        assert result[1]["name"] == "safe"

    def test_does_not_mutate_input(self):
        original = {"api_key": "real-key"}
        _redact_metadata(original)
        assert original["api_key"] == "real-key"


class TestParseMetadata:
    def test_none_returns_none(self):
        assert _parse_metadata(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_metadata("") is None

    def test_valid_json_parsed_and_redacted(self):
        payload = json.dumps({"model": "gpt-4o", "api_key": "sk-secret"})
        result = _parse_metadata(payload)
        assert isinstance(result, dict)
        assert result["model"] == "gpt-4o"
        assert result["api_key"] == "[REDACTED]"

    def test_invalid_json_returns_raw_string(self):
        result = _parse_metadata("not-json")
        assert result == "not-json"

    def test_nested_sensitive_key_redacted(self):
        payload = json.dumps({"config": {"token": "tok123", "label": "prod"}})
        result = _parse_metadata(payload)
        assert result["config"]["token"] == "[REDACTED]"
        assert result["config"]["label"] == "prod"
