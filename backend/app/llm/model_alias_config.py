from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class ModelAliasConfig:
    default_primary_model: str
    default_fallback_model: str
    aliases: dict[str, tuple[str, str]]  # alias -> (anthropic_model, openai_model)


class ModelAliasConfigError(ValueError):
    pass


def _require_non_blank(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ModelAliasConfigError(f"{field_name} must be a string")
    out = value.strip()
    if not out:
        raise ModelAliasConfigError(f"{field_name} must not be blank")
    return out


def load_model_alias_config(path: str | Path) -> ModelAliasConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"model aliases config not found: {config_path}")

    raw_text = config_path.read_text(encoding="utf-8")
    try:
        doc = yaml.safe_load(raw_text)
    except Exception as exc:
        raise ModelAliasConfigError("invalid YAML in model aliases config") from exc

    if not isinstance(doc, dict):
        raise ModelAliasConfigError("model aliases config must be a YAML mapping/object")

    default_primary_model = _require_non_blank(
        doc.get("default_primary_model"), field_name="default_primary_model"
    )
    default_fallback_model = _require_non_blank(
        doc.get("default_fallback_model"), field_name="default_fallback_model"
    )
    aliases_raw = doc.get("aliases")
    if not isinstance(aliases_raw, dict):
        raise ModelAliasConfigError("aliases must be a mapping")

    aliases: dict[str, tuple[str, str]] = {}
    seen_normalized: set[str] = set()
    for alias_name_raw, value in aliases_raw.items():
        alias_name = _require_non_blank(alias_name_raw, field_name="alias_name")
        normalized = alias_name.strip().lower()
        if normalized in seen_normalized:
            raise ModelAliasConfigError(f"duplicate alias name: {alias_name!r}")
        seen_normalized.add(normalized)

        if not isinstance(value, dict):
            raise ModelAliasConfigError(f"alias {alias_name!r} must be a mapping")
        anthropic_model = _require_non_blank(
            value.get("anthropic"), field_name=f"aliases.{alias_name}.anthropic"
        )
        openai_model = _require_non_blank(
            value.get("openai"), field_name=f"aliases.{alias_name}.openai"
        )
        aliases[alias_name] = (anthropic_model, openai_model)

    return ModelAliasConfig(
        default_primary_model=default_primary_model,
        default_fallback_model=default_fallback_model,
        aliases=aliases,
    )

