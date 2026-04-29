"""Test config: ensure ``backend`` is on the import path when pytest runs from
either the repo root or the backend dir, and isolate the pricing module
between tests so env-var overrides don't leak.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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
