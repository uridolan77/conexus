"""Contract asset smoke tests (OpenAPI + JSON Schema + examples).

These tests intentionally avoid importing FastAPI app code so they stay lightweight.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_SCHEMA_FILES = sorted(
    (REPO_ROOT / "contracts" / "json-schema").glob("*.schema.json"),
    key=lambda p: p.name,
)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_openapi_yaml_loads() -> None:
    path = REPO_ROOT / "contracts" / "openapi" / "conexus.v1.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["openapi"] == "3.1.0"
    assert "/v1/chat/completions" in doc["paths"]
    assert "/health" in doc["paths"]


@pytest.mark.parametrize("schema_path", CONTRACT_SCHEMA_FILES, ids=lambda p: p.name)
def test_json_schema_files_are_valid_metaschema(schema_path: Path) -> None:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)


def test_example_chat_request_validates() -> None:
    schema = _load_json(REPO_ROOT / "contracts/json-schema/chat-request.schema.json")
    instance = _load_json(REPO_ROOT / "contracts/examples/requests/chat.simple.json")
    Draft202012Validator(schema).validate(instance)


def test_example_chat_response_validates() -> None:
    schema = _load_json(REPO_ROOT / "contracts/json-schema/chat-response.schema.json")
    instance = _load_json(REPO_ROOT / "contracts/examples/responses/chat.simple.response.json")
    Draft202012Validator(schema).validate(instance)


def test_routing_default_policy_validates() -> None:
    schema = _load_json(REPO_ROOT / "contracts/json-schema/model-aliases-routing.schema.json")
    instance = _load_json(REPO_ROOT / "contracts/routing/default-policy.json")
    Draft202012Validator(schema).validate(instance)
