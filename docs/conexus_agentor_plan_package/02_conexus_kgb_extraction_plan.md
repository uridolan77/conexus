# 02 — Conexus KGB Extraction Plan

## Goal

Turn KGB's LLM-router code into a clean standalone Conexus gateway.

Current KGB shape:

```text
pipeline stage → stage_name router → provider → KG pipeline telemetry/cache/budget
```

Target Conexus shape:

```text
client/project → model_alias/routing_profile → provider adapter → request log/usage/cost
```

## Extraction map

| KGB source | Extract into Conexus | Keep | Remove / rewrite |
|---|---|---|---|
| `backend/app/llm/base.py` | `backend/app/llm/adapters/base.py` | async interface, `aclose`, context manager | `stage_name`, KGB budget references |
| `backend/app/llm/openai_router.py` | `backend/app/llm/adapters/openai.py` | async call, retry, usage extraction, streaming pattern | Redis cache, semantic cache, KGB metrics, stage routing |
| `backend/app/llm/router.py` | `backend/app/llm/adapters/anthropic.py` | Anthropic call, retry, stream setup, `ModelConfig`, `LLMCallResult` | cache, shadow rollout, BudgetGuard, KG stage table |
| `backend/app/llm/conexus_router.py` | `backend/app/llm/gateway/fallback.py` + `gateway_service.py` | failover logic, normalized usage, provider error handling, agent-call idea | graph_node_count, KGB complexity tiers, KGB stage interface |
| `backend/app/llm/pricing.py` | `backend/app/llm/pricing.py` | YAML pricing, overrides, conservative fallback | KGB path assumptions |
| `backend/app/static_config/pricing.yaml` | `backend/app/static_config/pricing.yaml` | model cost data | update model IDs/prices as needed |
| `backend/app/llm/conexus_types.py` | `backend/app/llm/types.py` or `schemas/llm.py` | `Message`, `TokenUsage`, `ToolCall`, `AgentResponse` | KGB-specific naming only if needed |
| `backend/app/llm/conexus_format.py` | `backend/app/llm/formatters/anthropic.py` | OpenAI→Anthropic message/tool conversion | none; simplify for v1 |
| `backend/app/llm/conexus_constants.py` | `backend/app/llm/provider_errors.py` | failover error classes | stage complexity map |
| `backend/app/api/errors.py` | `backend/app/core/errors.py` | stable error envelope and `GatewayError` | KG-specific errors |
| `backend/app/llm/__init__.py` | `backend/app/llm/provider_factory.py` | factory pattern | global KGB settings only; evolve to DB config |
| `backend/tests/unit/test_conexus_router_semantic.py` | `backend/tests/unit/test_gateway_*.py` | fallback, usage, stream, close, cost behavior | semantic-routing tests until later |

## Target module layout

```text
backend/app/
  main.py
  api/
    health.py
    chat_completions.py
    admin_providers.py
    admin_projects.py
    admin_requests.py
    auth.py
  core/
    config.py
    errors.py
    logging.py
    security.py
  db/
    models.py
    session.py
    migrations/
  llm/
    types.py
    pricing.py
    provider_factory.py
    provider_errors.py
    normalizer.py
    adapters/
      base.py
      openai.py
      anthropic.py
    formatters/
      anthropic.py
      openai.py
    gateway/
      fallback.py
      routing.py
      service.py
  services/
    api_key_service.py
    provider_service.py
    request_log_service.py
    usage_service.py
```

## New concepts replacing KGB concepts

| KGB concept | Conexus concept |
|---|---|
| `stage_name` | `model_alias` or `routing_profile` |
| `BudgetContext` | later `ProjectBudgetPolicy` |
| `KG pipeline telemetry` | `gateway_request` + `usage_event` |
| `stage token estimate` | per-model/per-profile estimate |
| `ConexusRouter` class | `GatewayService` + `FallbackPolicy` + provider adapters |
| `settings.llm.provider` | DB/config-backed `ProviderConfig` |
| `LLMCallResult` | `ProviderResponse` / `ChatCompletionResponse` |

## Extraction phases

### Phase A — Skeleton

Create FastAPI backend, health endpoints, config, logging, and test setup.

Acceptance:

```text
GET /health returns ok
pytest runs
ruff/mypy baseline configured
```

### Phase B — Pricing + types

Extract pricing and typed contracts.

Acceptance:

```text
get_cost("gpt-4o-mini", 1000, 500) works
pricing overrides work in tests
Message/TokenUsage schemas pass type checking
```

### Phase C — Provider adapters

Implement `OpenAIAdapter` and `AnthropicAdapter` with mocked tests.

Acceptance:

```text
mock OpenAI success → normalized response
mock Anthropic success → normalized response
provider usage normalized to input/output/total/provider/model
```

### Phase D — Fallback gateway

Implement fallback from primary to secondary for retryable provider errors.

Acceptance:

```text
Anthropic 429 → OpenAI fallback
OpenAI 500 as primary → Anthropic fallback if configured
both fail → GatewayError with sanitized details
fallback_used recorded
```

### Phase E — OpenAI-compatible endpoint

Implement `/v1/chat/completions`.

Acceptance:

```text
client changes only base_url and api_key
request validates messages/model
response is OpenAI-compatible enough for standard clients
```

### Phase F — Persistence

Add projects, API keys, providers, request logs, usage events.

Acceptance:

```text
API key auth works
request_log row exists for success and failure
usage/cost fields populated
```

### Phase G — BO shell

Add Next.js dashboard and basic request visibility.

Acceptance:

```text
Dashboard loads
Requests table loads
Request detail shows provider/model/tokens/cost/error/fallback
```

## Extraction rules for Cursor

1. Copy behavior, not paths.
2. Do not import `app.pipeline`, `app.corpus`, `app.ontology`, or `app.agentor` into Conexus.
3. Every provider adapter must be testable with mocked SDK clients.
4. Every outbound provider error must normalize to a stable Conexus error code.
5. Provider API keys must never be logged.
6. The first endpoint should be non-streaming. Streaming comes after request logging works.
