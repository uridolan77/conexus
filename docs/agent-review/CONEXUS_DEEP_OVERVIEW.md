# CONEXUS — Deep Engineering Overview

Last updated: 2026-05-04

## Executive summary

Conexus is a **deployed LLM gateway + operations back-office (BO)**. It exposes a small OpenAI-ish gateway endpoint (`POST /v1/chat/completions`) that:

- authenticates callers via **project API keys**
- routes the request to a configured **LLM provider** (OpenAI / Anthropic, with an optional failover “gateway” router)
- normalizes the response shape
- persists **request logs** (latency/tokens/cost/errors) for BO visibility
- optionally enforces **strict per-project hard limits** using a DB reservation+reconcile mechanism

Operationally, the BO provides admin login + management surfaces for projects, API keys, provider configs (encrypted at rest), request logs, usage summaries, routing policy visibility, and limit-reservation repair tooling. The backend also contains “internal/trusted caller” endpoints to support adapter profile registry/activation/observability used by external services (e.g. `conexus.adaptation`), plus an admin proxy for an adaptation service.

This repo is intentionally **small and deployable**: it uses stdlib logging (no tracing/metrics), a straightforward async SQLAlchemy persistence layer with Alembic migrations, and a minimal provider adapter interface.

## What the system appears to be

Conexus is best understood as three products in one repo:

- **Gateway API**: a stable, client-facing HTTP endpoint that proxies LLM calls while logging and enforcing limits.
- **BO (Back-office)**: a Next.js UI for operating Conexus (auth, configuration, monitoring, repair tools).
- **Internal integration surface**: endpoints intended for trusted services to register and activate “adapter profiles” and fetch observability metrics.

The “core promise” is: **a real request flows end-to-end**:

`POST /v1/chat/completions` → provider call → normalized response → request log in DB → visible in BO.

## Solution/project structure

Top-level shape:

- `backend/`: Python FastAPI service (gateway + admin + internal APIs)
- `frontend/`: Next.js 14 App Router BO UI (cookie-based admin session)
- `docker-compose.yml`: Postgres + backend + frontend local stack
- `.env.example`: expected env variables (includes required `ENCRYPTION_KEY`)
- `.github/workflows/ci.yml`: backend lint+tests; frontend tests+build
- `docs/`: milestone and architecture docs

Backend layout (major responsibility clusters):

- `backend/app/main.py`: FastAPI app creation, router mounting, CORS, lifespan startup/shutdown
- `backend/app/core/`: configuration (`config.py`), logging setup (`logging.py`)
- `backend/app/api/`: HTTP routers (gateway `/v1`, admin `/admin/*`, internal `/internal/*`)
- `backend/app/services/`: business logic (gateway orchestration, limits, auth, audit, provider configs)
- `backend/app/llm/`: provider interface, adapters, routing, model alias config, pricing
- `backend/app/db/`: SQLAlchemy models + session/engine + Alembic migrations

Frontend layout:

- `frontend/app/`: Next.js pages (dashboard, projects, providers, requests, limits, adaptation console, etc.)
- `frontend/components/`: BO UI components (shell/sidebar + ops panels)
- `frontend/lib/`: API clients and type normalization (e.g. `adaptationApi.ts`)
- `frontend/middleware.ts`: route protection based on the admin session cookie

## Main runtime entry points

- **Backend runtime entry**: `backend/app/main.py` exports `app = create_app()`
- **Backend container entry**: `backend/Dockerfile` runs `uvicorn app.main:app`
- **Frontend container entry**: `frontend/Dockerfile` builds Next standalone and runs `node server.js`
- **Local runtime**: `docker compose up --build`
- **Operational CLI**: `backend/app/cli.py` (init DB, create project/key/admin, list/repair stale reservations)

## API surface (backend)

### Public gateway

- `POST /v1/chat/completions` (`backend/app/api/gateway.py`)
  - Auth: `Authorization: Bearer <project_api_key>`
  - Response header: `X-Conexus-Request-Id` (server-minted correlation id)
  - Supports `stream=true` and returns **SSE** (`text/event-stream`) with OpenAI-like `chat.completion.chunk` payloads and `[DONE]`
  - Explicitly rejects tool-calls and some OpenAI options (compat guardrails)

### Health/readiness

- `GET /health`
- `GET /readyz` (+ alias `GET /health/ready`)

Readiness checks include DB connectivity, encryption key validity, model alias config validity, and (in prod + when adapter registry enabled) internal API key strength.

### Admin (BO)

Cookie-based session under `conexus_admin_session`. Major modules:

- Auth: `/admin/auth/*`
- Providers: `/admin/providers/*` (encrypted provider secrets; test provider connectivity)
- Projects + keys: `/admin/projects/*`
- Limits + reservations + stale repair tooling: `/admin/projects/*/limits*`, and `/admin/projects/limits/reservations/*`
- Requests: `/admin/requests/*` (request log explorer/detail)
- Usage: `/admin/usage/*` (summary/by-project/by-provider/timeseries)
- Routing visibility: `/admin/routing/*`
- Audit logs: `/admin/audit`
- Adaptation proxy: `/admin/adaptation/*` (proxies to `ADAPTATION_API_BASE_URL`)
- Adapter profiles runtime state view: `/admin/adapter-profiles/*`

### Internal (trusted caller)

Keyed by `X-Internal-Api-Key`:

- `/internal/adapter-profiles/*`: register, activate-canary, promote, rollback, observability
- `/internal/domains/*`: current active profile for a domain

## LLM/provider integration layer

### Abstractions and layering

- Provider interface: `LLMProvider` (`backend/app/llm/base.py`)
  - `chat(messages, model, max_tokens, temperature)`
  - `stream_chat(messages, model, max_tokens, temperature)`
  - `aclose()`

Provider implementations:

- `OpenAIProvider` (`backend/app/llm/openai_adapter.py`)
- `AnthropicProvider` (`backend/app/llm/anthropic_adapter.py`)
- `GatewayProvider` (`backend/app/llm/gateway_router.py`): Anthropic primary + OpenAI fallback (non-stream only)

Provider selection:

- `make_provider()` (`backend/app/llm/__init__.py`) via `LLM_PROVIDER`
- Provider object is cached per-process (`backend/app/llm/dependencies.py`) and closed on app shutdown (`shutdown_provider()` in lifespan teardown).

### Model alias routing

The request `model` may be:

- a **Conexus alias** resolved via YAML (`MODEL_ALIASES_PATH`) into `(anthropic_model, openai_model)` and routed through `GatewayProvider`
- a **concrete provider model** (prefix-based) that bypasses alias logic to force `"anthropic_only"` or `"openai_only"`
- otherwise it is rejected (`UnknownModelError`) so typos do not silently route to defaults.

### Retries and timeouts

- Provider adapters implement retry on raw SDK 429/connection/5xx via `tenacity` (per adapter).
- Gateway service enforces timeouts:
  - non-stream: `asyncio.timeout(LLM_REQUEST_TIMEOUT_SECONDS)`
  - stream: `asyncio.wait_for` per chunk (`LLM_STREAM_TIMEOUT_SECONDS`)

### Pricing/cost estimation

- Pricing table is loaded from YAML with optional env overrides:
  - default: `backend/app/static_config/pricing.yaml`
  - overrides: `PRICING_CONFIG_PATH`, `PRICING_OVERRIDES_JSON`
- Cost is derived from token counts via `get_cost(model, input_tokens, output_tokens)`.
- Hard monthly cost limits use an alias-aware “most conservative candidate” estimate:
  - If any expanded candidate lacks explicit pricing → admission fails with `pricing_unavailable_for_hard_cost_limit`.

## Gateway/request pipeline (end-to-end flow)

Two closely-related flows exist: non-streaming and streaming.

### Non-streaming request flow

High-level:

```text
HTTP POST /v1/chat/completions
  → require_project_api_key (DB lookup by prefix; constant-time hash compare)
  → validate OpenAI-compat guardrails (reject unsupported features)
  → GatewayService.run_chat_completion
      → request_id = uuid4 hex
      → (optional) reserve hard limits in DB (strict-limit reservations)
      → start_request log row (status=started) in its own short session+commit
      → provider.chat(...) under gateway timeout
      → compute cost from usage
      → finish_request_success (status=completed; tokens/cost/latency; fallback_used)
      → reconcile reservation (completed/failed) if any
  → respond OpenAI-ish JSON and header X-Conexus-Request-Id
```

Key modules:

- HTTP: `backend/app/api/gateway.py`
- Orchestration: `backend/app/services/gateway_service.py`
- Logging: `backend/app/services/request_log_service.py`
- Limits: `backend/app/services/project_limit_reservation_service.py`
- Provider: `backend/app/llm/*`
- Auth: `backend/app/api/auth.py` + `backend/app/services/project_key_service.py`

### Streaming request flow (SSE)

When `stream=true`, Conexus returns a `StreamingResponse` and yields SSE events:

- On each provider chunk, it emits `data: {json}\n\n`
- It always ends with `data: [DONE]\n\n`
- Best-effort in-stream error yields an error payload, then `[DONE]`

Important operational detail:

- Request log completion for streams depends on reaching the end of the provider stream and (ideally) receiving a final “usage” payload (OpenAI uses `include_usage`, Anthropic emits a final usage chunk via `get_final_message()` when available).

### Correlation IDs

- Conexus generates a request id per gateway call and returns it to callers as:
  - response header: `X-Conexus-Request-Id`
  - part of the error JSON for gateway/compat errors
- There is no inbound “adopt existing request id” middleware today.

## Configuration and secrets handling

### Settings model

Central settings are in `backend/app/core/config.py` (Pydantic Settings), reading from:

- `.env` at repo root or `backend/.env`
- environment variables

Notable settings:

- `ENCRYPTION_KEY`: **required**; must be a valid Fernet key
- `DATABASE_URL`
- `AUTH_SECRET` (admin session signing)
- `CORS_ALLOWED_ORIGINS` / `FRONTEND_ORIGINS`
- provider env keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- timeouts: `LLM_REQUEST_TIMEOUT_SECONDS`, `LLM_STREAM_TIMEOUT_SECONDS`
- strict-limits repair knobs: `LIMIT_RESERVATION_*`
- internal adapter api key + feature flags: `INTERNAL_ADAPTER_API_KEY`, `ADAPTER_PROFILE_*`

### Provider secrets at rest

Provider credentials entered in BO are stored in DB as:

- `ProviderConfig.api_key_encrypted` (Fernet-encrypted with `ENCRYPTION_KEY`)
- a masked view `ProviderConfig.key_mask` is stored for display/audit

### Production hardening checks

On startup in `APP_ENV=prod`, the backend refuses:

- default `AUTH_SECRET`
- default `ADMIN_PASSWORD`
- wildcard `*` in `CORS_ALLOWED_ORIGINS`

Readiness in prod can additionally fail if adapter registry is enabled and the internal API key is missing/weak.

## Caching, retry, resilience, timeout, rate-limit logic

### Retries

- Provider retries are adapter-local (tenacity around SDK calls/stream creation).
- Gateway-level retries are effectively “failover” in `GatewayProvider.chat()` for some classes of primary failures.

### Timeouts

- Gateway sets explicit timeouts around provider chat and per-stream-chunk waiting.
- Adaptation proxy sets a small default timeout (10s) with overrides for specific routes (e.g. `run` uses 30s).

### Rate limiting and limits

There are two distinct concepts:

- **Admin login brute-force limiting**: in-memory only today (process-local) with a prod warning.
- **Project hard limits**: DB-backed reservation+reconcile to enforce strict daily request admission and approximate token/monthly cost limits.

Strict limits rely on DB row locks in Postgres (and an additional per-process asyncio lock for reserve/start ordering).

## Observability (logging, tracing, metrics, correlation)

Current posture:

- **Logs**: stdlib logging, plain text formatter.
- **DB request log**: `gateway_requests` table records request metadata (no prompt/response bodies).
- **Audit logs**: `audit_logs` table; metadata is sanitized to avoid secrets/prompt content persistence.
- **Metrics/tracing**: not integrated (no OTel/Prometheus/Sentry in codebase today).

Internal “adapter profile observability” endpoint computes requestCount/errorRate/p95/cost-per-answer over a window by scanning matching `gateway_requests`.

## Background jobs/workers

No dedicated worker process exists. Operational “jobs” are:

- admin-triggered stale reservation repair endpoints
- CLI commands that list/repair stale reservations

## Persistence layer

### Storage

- Primary: Postgres (recommended for production locking semantics)
- Tests often use SQLite in-memory via `aiosqlite`

### Tables (current core)

From `backend/app/db/models.py`, core tables include:

- `projects`, `project_api_keys`
- `gateway_requests`
- strict limit tables: `project_limits`, `project_usage_windows`, `project_gateway_limit_reservations`
- admin tables: `admin_users`, `audit_logs`
- provider configs: `provider_configs` (encrypted api key)
- adapter profile registry: `gateway_adapter_profiles`, `gateway_adapter_profile_activations`

Alembic migrations live under `backend/app/db/migrations/versions/`.

## WebSocket/streaming behavior

- Backend supports streaming **SSE** for `POST /v1/chat/completions` when `stream=true`.
- Frontend currently does not appear to consume SSE/WS; BO operations are request/response + refresh/poll.

## MCP/tools/agent integration

The gateway request explicitly rejects tool calls today (`tools` / `tool_choice` are 400). No MCP integration was identified in the codebase.

## Error handling and exception boundaries

Key boundaries:

- `gateway.py` maps internal gateway exceptions to HTTP status codes:
  - `GatewayClientError` → 400
  - `GatewayLimitError` → 429
  - `GatewayUpstreamError` → 502
  - plus a specific “compat” validation path that yields 400 with `request_id`
- App-level exception handler exists for `ModelAliasConfigError` → 500
- Many other exceptions fall back to FastAPI defaults (500 with generic detail in prod unless configured otherwise).

Notable reliability tactic:

- request logging uses its **own short-lived session per write**, so failures are less likely to be lost due to transaction rollback in an error path.

## Dependency graph / layering analysis

The backend is mostly layered as:

```text
app/api/*  (FastAPI routers; request parsing; auth deps)
  → app/services/*  (business logic; orchestration; cross-cutting)
      → app/llm/*   (provider adapters; routing; pricing)
      → app/db/*    (models; sessions; migrations)
```

“Cross-cutting” services include `audit_service`, `secret_crypto`, admin permission mapping, and provider config management.

Frontend layering is:

```text
app/* pages → components/* UI → lib/* fetch clients and normalizers
```

## Runtime risks (prioritized)

### P0 (correctness / security that can break production)

- **Multi-replica safety gaps for process-local mechanisms**:
  - admin login rate limit backend is in-memory only
  - gateway per-project reserve lock is process-local and does not coordinate across workers/replicas
  - model alias config and provider instance are process-global caches
  - These are safe for single-replica and still largely correct under Postgres row locks, but operational assumptions must be explicit.
- **Internal endpoint key management**: `/internal/*` relies on a shared static header secret; if exposed publicly or misconfigured, it becomes a control-plane risk.
- **Streaming accounting edge cases**: stream completion logging depends on finishing the stream and (ideally) receiving usage; interruptions can lead to incomplete token/cost logs.

### P1 (serious reliability/maintainability)

- **CI gaps**: frontend tests/build run in CI; frontend lint is not wired because ESLint is not installed/configured.
- **Observability**: no standard metrics/tracing; diagnosing latency/error spikes is log/DB-only.
- **Provider configs not wired into runtime routing**: BO-managed provider keys are encrypted/stored/testable, but the runtime gateway provider selection currently relies on process config/env keys for actual provider calls.
- **Observability endpoint scaling**: internal observability scans request rows in Python and could get expensive for large windows/high traffic.

### P2 (cleanup/structure)

- Some docs show drift (e.g. `docs/03_ARCHITECTURE.md` lists tables like `organizations`, `llm_models` that do not exist in current schema).
- Minor duplication between streaming and non-stream gateway flows could be factored for clarity.
- Provider error sanitization is duplicated across services (audit vs provider test vs gateway logs); consistency can be improved without behavior change.

### P3 (polish/documentation)

- Expand the “operational checklist” for running migrations in production and validating readiness.
- Add explicit “what is stored” and “what is never stored” statements for privacy posture (prompts/responses not persisted).

## Security risks (selected)

- **Secrets in logs/audit**: the code already sanitizes audit metadata and masks provider keys, but any new audit fields must remain careful (especially around request bodies).
- **Cookie/session configuration**: relies on `SameSite` defaults; cross-subdomain deployments must validate cookie policy + CORS as documented.
- **CORS misconfiguration**: prod guardrails prohibit `*`, but operators still need to set the correct BO origin(s).

## Reliability risks (selected)

- **Timeout behavior**: gateway applies explicit timeouts, but long streams + aggressive thresholds can cause false failures.
- **DB write strategy**: multiple short sessions per request log are robust for persistence but increase DB connection churn under load (pooling configuration may matter as scale grows).

## Scalability bottlenecks (selected)

- `GET /internal/adapter-profiles/{id}/observability` computes stats by materializing rows; will degrade with high volumes.
- Some admin list endpoints can become slow without careful indexing (several indexes exist; confirm query plans as data grows).

## Maintainability issues / code health

- Clear separation of concerns exists, but there are a few “sharp edges”:
  - global caches/locks hidden inside modules
  - streaming completion and logging are subtle (usage may not arrive)
  - adaptation proxy correctness depends on carefully stripping browser-supplied identity fields

## Testing gaps (high-signal)

- Frontend tests are present (Vitest) and executed in CI; ESLint/lint CI is still deferred.
- Backend tests exist and run in CI; however, heavy SQLite usage can miss Postgres-specific behavior.
- Critical risk areas where tests matter most:
  - gateway streaming completion logging correctness on interruption/timeouts
  - strict limit reservations under concurrency
  - adaptation proxy identity stripping (case-insensitive, snake_case, idempotency header forwarding)
  - internal registry idempotency/race behavior around IntegrityError on register

## Documentation gaps

- Architecture docs should be kept consistent with current schema and operational reality (CI, provider runtime selection, and which features are “wired” vs “planned”).

## Prioritized improvement roadmap

Severity definitions:

- **P0**: correctness/security issue that can break production
- **P1**: serious reliability/maintainability
- **P2**: cleanup/structure improvement
- **P3**: polish/docs

Roadmap (smallest safe steps first):

- **P2**: Add ESLint configuration and then a frontend lint CI step.
- **P1**: Add lightweight request-scoped logging context for `request_id` and project id in gateway logs (safe; does not change API).
- **P1**: Optimize internal observability endpoint with aggregate queries (only if proven output-identical).
- **P2**: Factor tiny helpers in `gateway_service.py` to reduce stream vs non-stream duplication, preserving behavior.
- **P2**: Document and optionally guard more clearly against multi-replica assumptions (process-local locks/limiters).
- **P2/P3**: Update drifting docs (e.g. schema table list in `docs/03_ARCHITECTURE.md`) to match reality.

