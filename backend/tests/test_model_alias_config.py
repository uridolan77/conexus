from __future__ import annotations

import pytest

from app.llm.model_alias_config import ModelAliasConfigError, load_model_alias_config


def test_model_alias_config_loads_valid_yaml(tmp_path) -> None:
    p = tmp_path / "aliases.yaml"
    p.write_text(
        """
default_primary_model: claude-x
default_fallback_model: gpt-y
aliases:
  conexus-default:
    anthropic: claude-x
    openai: gpt-y
  conexus-fast:
    anthropic: claude-fast
    openai: gpt-fast
""".lstrip(),
        encoding="utf-8",
    )

    cfg = load_model_alias_config(p)
    assert cfg.default_primary_model == "claude-x"
    assert cfg.default_fallback_model == "gpt-y"
    assert cfg.aliases["conexus-default"] == ("claude-x", "gpt-y")


def test_model_alias_config_missing_file_fails_clearly(tmp_path) -> None:
    with pytest.raises(ModelAliasConfigError):
        load_model_alias_config(tmp_path / "missing.yaml")


def test_model_alias_config_invalid_yaml_fails_clearly(tmp_path) -> None:
    p = tmp_path / "aliases.yaml"
    p.write_text("default_primary_model: [\n", encoding="utf-8")
    with pytest.raises(ModelAliasConfigError):
        load_model_alias_config(p)


@pytest.mark.parametrize(
    "yaml_text",
    [
        "default_fallback_model: gpt-y\naliases: {}\n",
        "default_primary_model: claude-x\naliases: {}\n",
        "default_primary_model: claude-x\ndefault_fallback_model: gpt-y\n",
    ],
)
def test_model_alias_config_missing_required_fields_fails(tmp_path, yaml_text: str) -> None:
    p = tmp_path / "aliases.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    with pytest.raises(ModelAliasConfigError):
        load_model_alias_config(p)


def test_model_alias_config_alias_missing_provider_fields_fails(tmp_path) -> None:
    p = tmp_path / "aliases.yaml"
    p.write_text(
        """
default_primary_model: claude-x
default_fallback_model: gpt-y
aliases:
  conexus-default:
    anthropic: claude-x
""".lstrip(),
        encoding="utf-8",
    )
    with pytest.raises(ModelAliasConfigError):
        load_model_alias_config(p)

