"""Pricing tests — behaviour copied from KGB pricing helper."""

from __future__ import annotations

import json

from app.llm.pricing import get_cost, reload_pricing


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


def test_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "PRICING_OVERRIDES_JSON",
        json.dumps({"my-model": {"input": 1.0, "output": 2.0}}),
    )
    reload_pricing()
    cost = get_cost("my-model", 1_000_000, 500_000)
    assert cost == 1.0 + 1.0  # 1M * 1 + 0.5M * 2
