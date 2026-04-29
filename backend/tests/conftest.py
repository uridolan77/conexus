"""Test config: ensure ``backend`` is on the import path when pytest runs from
either the repo root or the backend dir, and isolate the pricing module
between tests so env-var overrides don't leak.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import tenacity

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


@pytest.fixture(autouse=True)
def _reset_pricing_cache():
    from app.llm import pricing

    pricing._pricing_cache = {}
    pricing._pricing_loaded = False
    yield
    pricing._pricing_cache = {}
    pricing._pricing_loaded = False


@pytest.fixture(autouse=True)
def _no_retry_wait():
    """Make tenacity retries instantaneous so retry-behaviour tests stay fast."""
    from app.llm import anthropic_adapter, openai_adapter

    targets = (
        openai_adapter._retried_openai_create,
        anthropic_adapter._retried_anthropic_create,
    )
    originals = [t.retry.wait for t in targets]
    for t in targets:
        t.retry.wait = tenacity.wait_none()
    yield
    for t, w in zip(targets, originals):
        t.retry.wait = w
