from __future__ import annotations

import pytest

from app.core.config import Settings


def test_effective_allow_env_admin_fallback_defaults_false_in_prod() -> None:
    s = Settings.model_construct(app_env="prod", encryption_key="x")
    assert s.effective_allow_env_admin_fallback is False


def test_effective_cookie_secure_defaults_true_in_prod_false_elsewhere() -> None:
    prod = Settings.model_construct(app_env="prod", encryption_key="x")
    local = Settings.model_construct(app_env="local", encryption_key="x")
    assert prod.effective_cookie_secure is True
    assert local.effective_cookie_secure is False


def test_effective_allow_create_all_defaults_false_in_prod_true_elsewhere() -> None:
    prod = Settings.model_construct(app_env="prod", encryption_key="x")
    local = Settings.model_construct(app_env="local", encryption_key="x")
    assert prod.effective_allow_create_all is False
    assert local.effective_allow_create_all is True


def test_effective_cors_origins_parses_comma_list_and_adds_locals_outside_prod() -> None:
    s = Settings.model_construct(
        app_env="local",
        encryption_key="x",
        cors_allowed_origins="https://bo.example.com, https://bo2.example.com",
    )
    assert "https://bo.example.com" in s.effective_cors_origins
    assert "https://bo2.example.com" in s.effective_cors_origins
    assert "http://localhost:3000" in s.effective_cors_origins
    assert "http://127.0.0.1:3000" in s.effective_cors_origins


def test_effective_cors_origins_does_not_add_local_origins_in_prod() -> None:
    s = Settings.model_construct(
        app_env="prod",
        encryption_key="x",
        cors_allowed_origins="https://bo.example.com",
    )
    assert s.effective_cors_origins == ["https://bo.example.com"]


def test_cookie_samesite_normalized_to_lowercase() -> None:
    s = Settings.model_validate(
        {"APP_ENV": "local", "ENCRYPTION_KEY": "x", "COOKIE_SAMESITE": "StRiCt"}
    )
    assert s.cookie_samesite == "strict"


@pytest.mark.parametrize("value", ["lax", "strict", "none", " LAX "])
def test_cookie_samesite_allowed_values(value: str) -> None:
    s = Settings.model_validate(
        {"APP_ENV": "local", "ENCRYPTION_KEY": "x", "COOKIE_SAMESITE": value}
    )
    assert s.cookie_samesite in {"lax", "strict", "none"}


def test_cookie_samesite_invalid_value_rejected() -> None:
    with pytest.raises(ValueError):
        Settings.model_validate(
            {"APP_ENV": "local", "ENCRYPTION_KEY": "x", "COOKIE_SAMESITE": "invalid"}
        )


def test_prod_cookie_samesite_none_requires_secure_true() -> None:
    with pytest.raises(ValueError):
        Settings.model_validate(
            {
                "APP_ENV": "prod",
                "ENCRYPTION_KEY": "x",
                "COOKIE_SAMESITE": "none",
                "COOKIE_SECURE": False,
            }
        )

    ok = Settings.model_validate(
        {
            "APP_ENV": "prod",
            "ENCRYPTION_KEY": "x",
            "COOKIE_SAMESITE": "none",
            "COOKIE_SECURE": True,
        }
    )
    assert ok.cookie_samesite == "none"


def test_llm_timeouts_validate_min_value() -> None:
    with pytest.raises(ValueError):
        Settings.model_validate(
            {"APP_ENV": "local", "ENCRYPTION_KEY": "x", "LLM_REQUEST_TIMEOUT_SECONDS": 0}
        )
    with pytest.raises(ValueError):
        Settings.model_validate(
            {"APP_ENV": "local", "ENCRYPTION_KEY": "x", "LLM_STREAM_TIMEOUT_SECONDS": 0}
        )

