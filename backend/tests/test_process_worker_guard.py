"""Worker-count guard for hard-limit single-process locks."""

from __future__ import annotations

import logging

import pytest

from app.core.config import Settings
from app.core.process_worker_guard import (
    detected_worker_process_count,
    enforce_hard_limit_worker_safety,
)


def test_detected_worker_process_count_reads_web_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEB_CONCURRENCY", "3")
    assert detected_worker_process_count() == 3


def test_enforce_hard_limit_worker_safety_error_on_multi_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    log = logging.getLogger("test_worker_guard")
    settings = Settings.model_construct(
        app_env="prod",
        encryption_key="x",
        gateway_hard_limit_distributed_lock_enabled=False,
        gateway_hard_limit_multi_worker_policy="error",
    )
    with pytest.raises(RuntimeError, match="Detected 2 worker"):
        enforce_hard_limit_worker_safety(settings=settings, log=log)


def test_enforce_hard_limit_worker_safety_warn_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    log = logging.getLogger("test_worker_guard_warn")
    settings = Settings.model_construct(
        app_env="prod",
        encryption_key="x",
        gateway_hard_limit_distributed_lock_enabled=False,
        gateway_hard_limit_multi_worker_policy="warn",
    )
    enforce_hard_limit_worker_safety(settings=settings, log=log)


def test_enforce_skipped_when_distributed_lock_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    log = logging.getLogger("test_worker_guard_skip")
    settings = Settings.model_construct(
        app_env="prod",
        encryption_key="x",
        gateway_hard_limit_distributed_lock_enabled=True,
        gateway_hard_limit_multi_worker_policy="error",
    )
    enforce_hard_limit_worker_safety(settings=settings, log=log)
