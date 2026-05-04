# 05 — Cursor Prompts

## Prompt 1 — Conexus M0/M1 skeleton and typed core

```text
We are building Conexus as a small deployed LLM gateway and back-office, using KGB as the source for reusable LLM gateway behavior.

Implement only M0 and M1.

Context:
- Source repo for behavior: uridolan77/KGB
- Extract behavior from:
  - backend/app/llm/pricing.py
  - backend/app/static_config/pricing.yaml
  - backend/app/llm/conexus_types.py
  - backend/app/api/errors.py
- Do not import KGB pipeline, corpus, ontology, chunks, DAG, Agentor, Celery, or semantic cache concepts.

Tasks:
1. Create FastAPI backend skeleton under backend/app.
2. Add /health and /health/ready.
3. Add config using pydantic-settings.
4. Add structured logging basics.
5. Add pytest, ruff, mypy setup.
6. Add Dockerfile and docker-compose with PostgreSQL.
7. Create backend/app/llm/types.py with Message, TokenUsage, ToolCall, ProviderRequest, ProviderResponse.
8. Create backend/app/llm/pricing.py and backend/app/static_config/pricing.yaml from KGB behavior.
9. Create backend/app/core/errors.py with ConexusDomainError, ValidationError, AuthenticationError, PermissionDeniedError, GatewayError, ServiceUnavailableError.
10. Add unit tests for pricing, unknown-model fallback, pricing override, and error envelope serialization.

Acceptance:
- backend starts
- GET /health returns ok
- pytest passes
- no KGB pipeline imports exist
- pricing tests pass
```

## Prompt 2 — Provider adapters

```text
Implement Conexus M2: provider adapters.

Source behavior from KGB:
- backend/app/llm/openai_router.py
- backend/app/llm/router.py
- backend/app/llm/conexus_types.py

Target modules:
- backend/app/llm/adapters/base.py
- backend/app/llm/adapters/openai.py
- backend/app/llm/adapters/anthropic.py
- backend/app/llm/provider_errors.py
- backend/app/llm/formatters/anthropic.py

Rules:
- Do not implement Redis cache, semantic cache, BudgetContext, stage routing, or KGB metrics.
- Provider adapters must accept injectable SDK clients for tests.
- Normalize every successful response into ProviderResponse.
- Normalize provider errors into ProviderError with retryable flag.
- Never log API keys or full request bodies by default.

Tests:
1. OpenAIAdapter mocked success maps content, model, tokens, provider.
2. AnthropicAdapter mocked success maps content, model, tokens, provider.
3. OpenAI retryable errors classified retryable.
4. Anthropic retryable errors classified retryable.
5. aclose closes underlying clients.

Acceptance:
- pytest passes
- mypy passes for llm adapters if possible
```

## Prompt 3 — Fallback gateway service

```text
Implement Conexus M3: GatewayService and fallback.

Target modules:
- backend/app/llm/gateway/service.py
- backend/app/llm/gateway/fallback.py
- backend/app/llm/provider_factory.py

Behavior:
- GatewayService receives ProviderRequest with project_id, request_id, model_alias, messages, temperature, max_tokens.
- Resolve a simple static RoutingProfile for now:
  conexus-fast -> primary openai gpt-4o-mini, fallback anthropic low model if configured
  conexus-smart -> primary anthropic high model, fallback openai gpt-4o
- If primary succeeds, return GatewayResult(fallback_used=false).
- If primary raises retryable ProviderError, attempt fallback.
- If both fail, raise GatewayError with sanitized details.
- Non-retryable validation/config errors should not fall back.

Tests:
1. primary success no fallback
2. primary retryable failure fallback success
3. both fail raises GatewayError
4. non-retryable provider error does not fallback
5. usage totals/cost are preserved

Acceptance:
- no DB required yet
- no BO required yet
- provider factory supports mocked adapters in tests
```

## Prompt 4 — OpenAI-compatible endpoint

```text
Implement Conexus M4: POST /v1/chat/completions.

Target modules:
- backend/app/api/chat_completions.py
- backend/app/schemas/openai_compat.py
- backend/app/services/gateway_service.py if needed

Requirements:
- Accept OpenAI-like request: model, messages, temperature, max_tokens, stream=false only.
- Return OpenAI-like response: id, object, created, model, choices, usage.
- For v1, reject stream=true with a clear 400/422 saying streaming not enabled yet.
- Use a temporary local API key setting until project API keys are implemented.
- Call GatewayService.
- Use global error handler for GatewayError.

Tests:
1. valid mocked request returns OpenAI-compatible shape
2. invalid messages returns 422
3. stream=true returns unsupported error
4. provider failure returns sanitized 502

Acceptance:
- curl example works locally
```

## Prompt 5 — Persistence and request logging

```text
Implement Conexus M5 persistence.

Use PostgreSQL with SQLAlchemy/Alembic.

Create models:
- organizations
- users
- projects
- project_api_keys
- llm_providers
- gateway_model_aliases
- gateway_requests
- usage_events
- audit_logs

Implement services:
- ProjectKeyService: generate, hash, verify, revoke.
- RequestLogService: start, complete, fail.
- UsageService: record usage event.
- ProviderService: read enabled provider configs.

Requirements:
- Project API keys use prefix + secret; only hash stored.
- Provider secrets are not implemented yet or are encrypted if implemented.
- Request logs must be written for both success and failure.
- Error messages must be sanitized.

Tests:
1. create key, verify key, revoked key fails
2. request log success path
3. request log failure path
4. usage event cost stored

Acceptance:
- /v1/chat/completions uses project API key auth
- DB contains gateway request row after call
```

## Prompt 6 — BO request visibility

```text
Implement Conexus M6 BO shell and request visibility.

Frontend: Next.js.

Pages:
- Dashboard
- Requests
- Request Detail
- Providers stub
- Projects stub

Backend admin endpoints:
- GET /admin/requests
- GET /admin/requests/{request_id}
- GET /admin/dashboard/summary

Dashboard cards:
- requests today
- success rate
- failed requests
- average latency
- estimated cost
- latest errors

Request table columns:
- time
- request_id
- project
- provider
- model
- status
- latency_ms
- tokens
- cost
- fallback_used

Acceptance:
- call gateway via curl
- open BO
- see the request
- click request detail and see provider/model/tokens/cost/error/fallback
```

## Prompt 7 — Minimal Agentor after Conexus M6

```text
Build minimal Agentor v0 only after Conexus M6 works.

Goal: one Ontogony CMS content workflow.

Do not use the old Agentor or Aigent framework wholesale.

Implement:
- AgentRun
- GraphState
- NodeExecutor
- ConexusClient
- ToolClient abstraction
- HumanApprovalCheckpoint
- RunLog

Workflow:
1. Planner node creates page outline.
2. Source node reads provided source docs/files through tool client stub.
3. Writer node calls Conexus.
4. Critic node calls Conexus.
5. Formatter node outputs Astro/Tina-compatible markdown/frontmatter.
6. Human approval required before writing or PR creation.

Acceptance:
- workflow runs with mocked tools and real/mock Conexus
- generated markdown is shown
- no write occurs without approval
```
