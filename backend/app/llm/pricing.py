"""LLM pricing — single source of truth for per-model token costs.

Copied from ``KGB/backend/app/llm/pricing.py`` with Conexus packaging changes:

- Default ``pricing.yaml`` is loaded from the installed ``app.static_config``
  package via ``importlib.resources`` (works when the backend is installed as a
  wheel).
- ``PRICING_CONFIG_PATH`` env var still overrides the bundled default file.
- ``PRICING_OVERRIDES_JSON`` env var injects per-model overrides (useful in tests).
- Unknown models fall back to Sonnet 4 rates so estimates are conservative
  rather than zero; the first use of each unknown model name logs a warning.
"""

from __future__ import annotations

import json
import logging
import os
from importlib import resources
from pathlib import Path

import yaml

from app.llm.model_alias_config import ModelAliasConfig, resolve_pricing_model_candidates

logger = logging.getLogger(__name__)

_pricing_cache: dict[str, tuple[float, float]] = {}
_pricing_loaded: bool = False
_unknown_model_warned: set[str] = set()


def _open_default_pricing_file():
    return resources.files("app").joinpath("static_config", "pricing.yaml").open(
        "r", encoding="utf-8"
    )


def _load_pricing(path: Path | None = None) -> dict[str, tuple[float, float]]:
    path_label: str
    if path is None:
        env_path = os.environ.get("PRICING_CONFIG_PATH", "").strip()
        if env_path:
            config_path = Path(env_path)
            path_label = str(config_path)
            fh = config_path.open(encoding="utf-8")
        else:
            path_label = "app.static_config/pricing.yaml"
            fh = _open_default_pricing_file()
    else:
        path_label = str(path)
        fh = path.open(encoding="utf-8")

    with fh:
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

    logger.info("pricing_loaded path=%s models=%d", path_label, len(table))
    return table


def reload_pricing(path: Path | None = None) -> None:
    """Force a reload of the pricing config from disk."""
    global _pricing_cache, _pricing_loaded, _unknown_model_warned
    _pricing_cache = _load_pricing(path)
    _pricing_loaded = True
    _unknown_model_warned = set()


def _ensure_loaded() -> None:
    global _pricing_loaded
    if not _pricing_loaded:
        reload_pricing()


_FALLBACK_INPUT_PER_1M = 3.0
_FALLBACK_OUTPUT_PER_1M = 15.0


def get_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the USD cost for *model* given the token counts."""
    _ensure_loaded()
    if model not in _pricing_cache and model not in _unknown_model_warned:
        _unknown_model_warned.add(model)
        logger.warning(
            "pricing_unknown_model_using_fallback_rates model=%s",
            model,
        )
    inp_price, out_price = _pricing_cache.get(
        model, (_FALLBACK_INPUT_PER_1M, _FALLBACK_OUTPUT_PER_1M)
    )
    return (input_tokens * inp_price + output_tokens * out_price) / 1_000_000


def model_has_explicit_rates(model: str) -> bool:
    """True if *model* appears in the loaded pricing table (not only fallback defaults)."""
    _ensure_loaded()
    return model in _pricing_cache


def estimate_reservation_cost_usd(model: str, reserved_total_tokens: int) -> float | None:
    """Upper-bound style USD estimate for admission when *reserved_total_tokens* is a budget cap.

    Uses known rates only. Returns ``None`` if the model is not in the pricing table
    (hard monthly cost limits must then block — see gateway reservation policy).
    """
    if reserved_total_tokens <= 0:
        return 0.0
    if not model_has_explicit_rates(model):
        return None
    # Conservative: price all reserved tokens at output-token rates.
    return get_cost(model, 0, reserved_total_tokens)


def estimate_hard_monthly_reservation_cost_usd(
    requested_model: str,
    reserved_total_tokens: int,
    *,
    alias_cfg: ModelAliasConfig,
) -> float | None:
    """Monthly hard-cap reservation: explicit requested model keeps single-model estimate.

    If the requested name is not in the pricing table, expand Conexus aliases to
    underlying Anthropic/OpenAI models and take the **maximum** per-candidate
    reservation estimate (most conservative). If any candidate lacks explicit
    pricing, return ``None`` (block with ``pricing_unavailable_for_hard_cost_limit``).
    """
    _ensure_loaded()
    if reserved_total_tokens <= 0:
        return 0.0
    rm = requested_model.strip()
    if model_has_explicit_rates(rm):
        return estimate_reservation_cost_usd(rm, reserved_total_tokens)

    candidates = resolve_pricing_model_candidates(requested_model, alias_cfg)
    max_est: float | None = None
    for c in candidates:
        est = estimate_reservation_cost_usd(c, reserved_total_tokens)
        if est is None:
            return None
        max_est = est if max_est is None else max(max_est, est)
    return max_est
