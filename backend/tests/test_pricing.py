"""Pricing tests — behaviour copied from KGB pricing helper."""

from __future__ import annotations

import json
from pathlib import Path

from app.llm.model_alias_config import (
    ModelAliasConfig,
    load_model_alias_config,
    resolve_pricing_model_candidates,
)
from app.llm.pricing import (
    estimate_hard_monthly_reservation_cost_usd,
    estimate_reservation_cost_usd,
    get_cost,
    model_has_explicit_rates,
    reload_pricing,
)

_MODEL_ALIASES_PATH = Path(__file__).resolve().parents[1] / "static_config" / "model_aliases.yaml"


def test_known_anthropic_cost() -> None:
    reload_pricing()
    # Sonnet 4: $3/M input + $15/M output.
    cost = get_cost("claude-sonnet-4-20250514", 1_000_000, 1_000_000)
    assert cost == 18.0


def test_known_openai_cost() -> None:
    reload_pricing()
    # gpt-4o-mini: $0.15/M input + $0.60/M output.
    cost = get_cost("gpt-4o-mini", 1_000_000, 1_000_000)
    assert cost == 0.75


def test_unknown_model_falls_back_to_sonnet_rates() -> None:
    reload_pricing()
    # Falls back to (3.0, 15.0) per 1M tokens.
    cost = get_cost("totally-made-up-model-unique-xyz", 1_000_000, 0)
    assert cost == 3.0


def test_default_pricing_loads_from_package_without_pricing_config_path(monkeypatch) -> None:
    monkeypatch.delenv("PRICING_CONFIG_PATH", raising=False)
    reload_pricing(path=None)
    assert model_has_explicit_rates("gpt-4o-mini") is True


def test_model_has_explicit_rates() -> None:
    reload_pricing()
    assert model_has_explicit_rates("gpt-4o-mini") is True
    assert model_has_explicit_rates("totally-made-up-model-xyz") is False


def test_estimate_reservation_cost_usd_known_model() -> None:
    reload_pricing()
    est = estimate_reservation_cost_usd("gpt-4o-mini", 1_000_000)
    assert est is not None
    assert est == get_cost("gpt-4o-mini", 0, 1_000_000)


def test_estimate_reservation_cost_usd_unknown_model_returns_none() -> None:
    reload_pricing()
    assert estimate_reservation_cost_usd("unknown-model-for-reservation-test", 1000) is None


def test_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "PRICING_OVERRIDES_JSON",
        json.dumps({"my-model": {"input": 1.0, "output": 2.0}}),
    )
    reload_pricing()
    cost = get_cost("my-model", 1_000_000, 500_000)
    assert cost == 1.0 + 1.0  # 1M * 1 + 0.5M * 2


def test_resolve_pricing_model_candidates_alias_and_concrete() -> None:
    cfg = load_model_alias_config(_MODEL_ALIASES_PATH)
    assert resolve_pricing_model_candidates("gpt-4o-mini", cfg) == ["gpt-4o-mini"]
    c = resolve_pricing_model_candidates("conexus-default", cfg)
    assert len(c) == 2
    assert c[0] != c[1]


def test_estimate_hard_monthly_conexus_default_not_pricing_unavailable() -> None:
    reload_pricing()
    cfg = load_model_alias_config(_MODEL_ALIASES_PATH)
    est = estimate_hard_monthly_reservation_cost_usd("conexus-default", 1_000_000, alias_cfg=cfg)
    assert est is not None
    assert est > 0


def test_estimate_hard_monthly_alias_uses_conservative_max_candidate() -> None:
    reload_pricing()
    cfg = load_model_alias_config(_MODEL_ALIASES_PATH)
    cands = resolve_pricing_model_candidates("conexus-default", cfg)
    parts = [estimate_reservation_cost_usd(m, 1_000_000) for m in cands]
    assert None not in parts
    est = estimate_hard_monthly_reservation_cost_usd("conexus-default", 1_000_000, alias_cfg=cfg)
    assert est == max(parts)


def test_estimate_hard_monthly_explicit_model_unchanged_single_estimate() -> None:
    reload_pricing()
    cfg = load_model_alias_config(_MODEL_ALIASES_PATH)
    est = estimate_hard_monthly_reservation_cost_usd("gpt-4o-mini", 500_000, alias_cfg=cfg)
    assert est == estimate_reservation_cost_usd("gpt-4o-mini", 500_000)


def test_estimate_hard_monthly_alias_blocks_if_any_candidate_unpriced() -> None:
    reload_pricing()
    cfg = ModelAliasConfig(
        default_primary_model="claude-sonnet-4-20250514",
        default_fallback_model="gpt-4o",
        aliases={
            "xalias": ("definitely-not-a-priced-model-zz", "gpt-4o-mini"),
        },
    )
    assert estimate_hard_monthly_reservation_cost_usd("xalias", 1000, alias_cfg=cfg) is None


def test_estimate_hard_monthly_concrete_unknown_priced_model_blocks() -> None:
    reload_pricing()
    cfg = load_model_alias_config(_MODEL_ALIASES_PATH)
    assert (
        estimate_hard_monthly_reservation_cost_usd("unknown-model-xyz-unpriced", 100, alias_cfg=cfg)
        is None
    )
