from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class LoginAttemptKey:
    username: str
    client_ip: str | None


_MAX_TRACKED_LOGIN_KEYS = 5000


class AdminLoginRateLimiter:
    def __init__(self, *, max_failures: int, window_seconds: int) -> None:
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._failures: dict[LoginAttemptKey, deque[float]] = {}

    def _evict_if_over_cap(self) -> None:
        while len(self._failures) >= _MAX_TRACKED_LOGIN_KEYS:
            self._failures.pop(next(iter(self._failures)))

    def _prune(self, now: float, q: deque[float]) -> None:
        cutoff = now - self._window_seconds
        while q and q[0] < cutoff:
            q.popleft()

    def _key(self, *, username: str, client_ip: str | None) -> LoginAttemptKey:
        return LoginAttemptKey(username=username.strip().lower(), client_ip=client_ip or None)

    def is_rate_limited(self, *, username: str, client_ip: str | None, now: float | None = None) -> bool:
        now_ts = time.time() if now is None else now
        key = self._key(username=username, client_ip=client_ip)
        q = self._failures.get(key)
        if not q:
            return False
        self._prune(now_ts, q)
        return len(q) >= self._max_failures

    def record_failure(self, *, username: str, client_ip: str | None, now: float | None = None) -> None:
        now_ts = time.time() if now is None else now
        key = self._key(username=username, client_ip=client_ip)
        q = self._failures.get(key)
        if q is None and len(self._failures) >= _MAX_TRACKED_LOGIN_KEYS:
            self._evict_if_over_cap()
        if q is None:
            q = deque()
            self._failures[key] = q
        self._prune(now_ts, q)
        q.append(now_ts)

    def clear(self, *, username: str, client_ip: str | None) -> None:
        key = self._key(username=username, client_ip=client_ip)
        self._failures.pop(key, None)


_rate_limiter: AdminLoginRateLimiter | None = None
# Config tuple (max_failures, window_seconds) used when the singleton was created.
_limiter_config: tuple[int, int] | None = None


def get_admin_login_rate_limiter(*, max_failures: int, window_seconds: int) -> AdminLoginRateLimiter:
    """Return the process-wide limiter.

    In-memory state is **single-process only** (not shared across workers or hosts).
    """
    global _rate_limiter, _limiter_config
    cfg = (max_failures, window_seconds)
    if _rate_limiter is None:
        _rate_limiter = AdminLoginRateLimiter(
            max_failures=max_failures,
            window_seconds=window_seconds,
        )
        _limiter_config = cfg
        return _rate_limiter
    if _limiter_config != cfg:
        raise RuntimeError(
            "admin login rate limiter was already initialized with different settings; "
            "this in-memory limiter is single-process — align callers with one config."
        )
    return _rate_limiter


def reset_admin_login_rate_limiter_for_tests() -> None:
    global _rate_limiter, _limiter_config
    _rate_limiter = None
    _limiter_config = None


def should_warn_admin_login_rate_limiter_in_memory_prod(
    *, app_env: str, admin_login_rate_limit_backend: str
) -> bool:
    """True when production runs the process-local limiter (not shared across workers/replicas)."""
    return (
        app_env.strip().lower() == "prod"
        and admin_login_rate_limit_backend.strip().lower() == "in_memory"
    )
