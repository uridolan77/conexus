"""Pricing tests — behaviour copied from KGB pricing helper."""

from __future__ import annotations

import json

from app.llm.pricing import (
    estimate_reservation_cost_usd,
    get_cost,
    model_has_explicit_rates,
    reload_pricing,
)


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
    cost = get_cost("totally-made-up-model", 1_000_000, 0)
    assert cost == 3.0


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
