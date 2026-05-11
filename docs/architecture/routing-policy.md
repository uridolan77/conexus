# Routing policy

## What exists today

Conexus resolves **model aliases** and default models from a YAML file checked into the backend:

- `backend/static_config/model_aliases.yaml`

Each alias maps to a pair of concrete models: one for Anthropic and one for OpenAI. The active gateway router (`app/llm/gateway_router.py`) chooses a route based on configured providers and the requested model string (alias vs concrete id prefixes).

The repository also carries a **JSON mirror** of that file for contract consumers who cannot read YAML in their tooling:

- `contracts/routing/default-policy.json`

JSON Schema for that shape:

- `contracts/json-schema/model-aliases-routing.schema.json`

## Forward-looking catalog (not loaded)

The work package described a richer multi-provider catalog with explicit capabilities and fallback chains. A schema for that aspirational shape is kept as:

- `contracts/json-schema/routing-policy.schema.json` (`x-contract-status: not-implemented`)

It is useful for planning and diffing against future gateway features, but **the backend does not consume this file today**.

## Determinism (target)

Given the same request, same static alias configuration, and the same provider availability, routing should be explainable and repeatable. Today, “explainability” is primarily via logs and BO request rows rather than a `POST /v1/route` preview endpoint.

## Adapter canary bucketing and `request_id`

When adapter canary routing is enabled, the gateway hashes `project_id`, `api_key_id`, and the **gateway `request_id`** (the same value as `X-Conexus-Request-Id` when the caller supplies one, otherwise the server-generated id) to pick a canary bucket.

**Integration note:** `X-Conexus-Request-Id` is a **correlation** handle for logs and BO, not an idempotency key (see OpenAPI and readiness docs). Callers should send a **fresh** value per new LLM attempt. Do not treat caller-chosen ids as a stable or intentional traffic-splitting control for canary semantics; if canary behavior must be independent of client-supplied correlation ids, that requires a deliberate product change to bucketing inputs.
