"""LLM pricing — single source of truth for per-model token costs.

Copied from ``KGB/backend/app/llm/pricing.py`` with one change: the bundled
default file path now points at ``backend/app/static_config/pricing.yaml``
inside the Conexus repo. Behaviour is otherwise identical:

- YAML config is loaded lazily on first ``get_cost`` call.
- ``PRICING_CONFIG_PATH`` env var overrides the bundled default file.
- ``PRICING_OVERRIDES_JSON`` env var injects per-model overrides
  (useful in tests).
- Unknown models fall back to Sonnet 4 rates so estimates are conservative
  rather than zero.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_PRICING_PATH = (
    Path(__file__).resolve().parent.parent / "static_config" / "pricing.yaml"
)

_pricing_cache: dict[str, tuple[float, float]] = {}
_pricing_loaded: bool = False


def _load_pricing(path: Path | None = None) -> dict[str, tuple[float, float]]:
    config_path = path
    if config_path is None:
        env_path = os.environ.get("PRICING_CONFIG_PATH", "").strip()
        config_path = Path(env_path) if env_path else _DEFAULT_PRICING_PATH

    with config_path.open() as fh:
        raw: dict[str, dict[str, dict[str, float]]] = yaml.safe_load(fh) or {}

    table: dict[str, tuple[float, float]] = {}
    for _provider, models in raw.items():
        for model_name, prices in models.items():
            table[model_name] = (float(prices["input"]), float(prices["output"]))

    overrides_json = os.environ.get("PRICING_OVERRIDES_JSON", "").strip()
    if overrides_json:
        overrides: dict[str, dict[str, float]] = json.loads(overrides_json)
        for model_name, prices in overrides.items():
            table[model_name] = (float(prices["input"]), float(prices["output"]))

    logger.info("pricing_loaded path=%s models=%d", config_path, len(table))
    return table


def reload_pricing(path: Path | None = None) -> None:
    """Force a reload of the pricing config from disk."""
    global _pricing_cache, _pricing_loaded
    _pricing_cache = _load_pricing(path)
    _pricing_loaded = True


def _ensure_loaded() -> None:
    global _pricing_loaded
    if not _pricing_loaded:
        reload_pricing()


_FALLBACK_INPUT_PER_1M = 3.0
_FALLBACK_OUTPUT_PER_1M = 15.0


def get_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the USD cost for *model* given the token counts."""
    _ensure_loaded()
    inp_price, out_price = _pricing_cache.get(
        model, (_FALLBACK_INPUT_PER_1M, _FALLBACK_OUTPUT_PER_1M)
    )
    return (input_tokens * inp_price + output_tokens * out_price) / 1_000_000
