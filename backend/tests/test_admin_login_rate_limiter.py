from __future__ import annotations

import pytest

from app.services.admin_login_rate_limiter import (
    get_admin_login_rate_limiter,
    reset_admin_login_rate_limiter_for_tests,
)


def test_same_config_returns_same_limiter() -> None:
    reset_admin_login_rate_limiter_for_tests()
    try:
        a = get_admin_login_rate_limiter(max_failures=3, window_seconds=60)
        b = get_admin_login_rate_limiter(max_failures=3, window_seconds=60)
        assert a is b
    finally:
        reset_admin_login_rate_limiter_for_tests()


def test_different_config_after_init_raises() -> None:
    reset_admin_login_rate_limiter_for_tests()
    try:
        get_admin_login_rate_limiter(max_failures=3, window_seconds=60)
        with pytest.raises(RuntimeError, match="already initialized"):
            get_admin_login_rate_limiter(max_failures=5, window_seconds=60)
    finally:
        reset_admin_login_rate_limiter_for_tests()
