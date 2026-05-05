"""Test config: ensure ``backend`` is on the import path when pytest runs from
either the repo root or the backend dir, and isolate the pricing module
between tests so env-var overrides don't leak.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import tenacity

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Tests run with a required ENCRYPTION_KEY; set a deterministic test value if absent.
os.environ.setdefault("ENCRYPTION_KEY", "8A4Rfd9yzsttvGQY0Q_IeEjV_j9V2drZW8JfHK4HgxA=")


@pytest.fixture(autouse=True)
def _reset_pricing_cache():
    from app.llm import pricing

    pricing._pricing_cache = {}
    pricing._pricing_loaded = False
    pricing._unknown_model_warned = set()
    yield
    pricing._pricing_cache = {}
    pricing._pricing_loaded = False
    pricing._unknown_model_warned = set()


@pytest.fixture(autouse=True)
def _no_retry_wait():
    """Make tenacity retries instantaneous so retry-behaviour tests stay fast."""
    from app.llm import anthropic_adapter, openai_adapter

    targets = (
        openai_adapter._retried_openai_create,
        openai_adapter._retried_openai_stream,
        anthropic_adapter._retried_anthropic_create,
        anthropic_adapter._retried_anthropic_stream_begin,
    )
    originals = [t.retry.wait for t in targets]
    for t in targets:
        t.retry.wait = tenacity.wait_none()
    yield
    for t, w in zip(targets, originals):
        t.retry.wait = w


@pytest.fixture(autouse=True)
def _reset_provider_test_factory():
    from app.services.provider_config_service import reset_provider_factory_for_tests

    reset_provider_factory_for_tests()
    yield
    reset_provider_factory_for_tests()


@pytest.fixture(autouse=True)
def _reset_secret_crypto_cache():
    from app.services.secret_crypto import reset_fernet_for_tests

    reset_fernet_for_tests()
    yield
    reset_fernet_for_tests()


@pytest.fixture(autouse=True)
def _reset_settings_overrides():
    from app.core.config import settings

    original_allow_env_admin_fallback = settings.allow_env_admin_fallback
    original_enable_static = settings.enable_static_admin_fallback
    original_bootstrap = settings.allow_static_bootstrap_when_no_db_admins
    try:
        yield
    finally:
        settings.allow_env_admin_fallback = original_allow_env_admin_fallback
        settings.enable_static_admin_fallback = original_enable_static
        settings.allow_static_bootstrap_when_no_db_admins = original_bootstrap


@pytest.fixture(autouse=True)
def _reset_model_alias_config_cache():
    from app.llm.gateway_router import _reset_model_alias_config_for_tests

    _reset_model_alias_config_for_tests()
    yield
    _reset_model_alias_config_for_tests()


@pytest.fixture(autouse=True)
def _reset_admin_login_rate_limiter():
    from app.services.admin_login_rate_limiter import reset_admin_login_rate_limiter_for_tests

    reset_admin_login_rate_limiter_for_tests()
    yield
    reset_admin_login_rate_limiter_for_tests()
