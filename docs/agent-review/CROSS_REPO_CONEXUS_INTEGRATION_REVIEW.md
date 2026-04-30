# Cross-Repo Conexus Integration Review

**Scope:** `conexus` (FastAPI LLM gateway) ↔ `conexus.adaptation` (.NET adaptation orchestrator)  
**Date:** 2026-04-30  
**Reviewer:** Agent cross-repo review  
**Status:** Draft — awaiting owner decisions on P0/P1 items

---

## Executive Summary

Two findings dominate this review:

1. **The `/internal/*` adapter profile endpoint surface described in the integration design does not exist in `conexus`.** There are no internal endpoints for profile registration, canary activation, promotion, rollback, active profile lookup, or observability. `conexus` is currently a clean, functional LLM gateway and operations back-office with no awareness of adapter profiles.

2. **The gateway registration client in `conexus.adaptation` is a complete stub.** `DeterministicGatewayRegistrationClient` returns `gw-{profileId:N}` with no HTTP calls. No real `HttpConexusGatewayRegistrationClient` exists.

**What works today:**
- `HttpConexusLlmClient` → `POST /v1/chat/completions` — real, tested HTTP integration with full error handling and response body redaction.
- Adapter profile lifecycle (publish → canary → promote → rollback) — self-contained state machine within `conexus.adaptation`.
- `conexus` admin BO — request logs, provider usage, project management, audit trail.

**What does not work today:**
- Adapter profile registration in the `conexus` gateway.
- Canary traffic routing in `conexus` based on adaptation profiles.
- Drift feedback loop from `conexus` to `conexus.adaptation`.
- Any observability integration between the two services.

**Are they conceptually aligned?**  
Yes. The architecture is coherent: `conexus.adaptation` builds and manages the lifecycle of adapter profiles; `conexus` routes live traffic through active profiles and emits observability signals. The gap is implementation, not design.

---

## Current Inferred Architecture

```
┌─────────────────────────────────────────────────────┐
│               conexus.adaptation (.NET)             │
│                                                     │
│  Planning → Approval → Execution → Evaluation       │
│       ↓                                             │
│  AdapterProfile (publish/canary/promote/rollback)   │
│       ↓                                             │
│  IConexusGatewayRegistrationClient                  │
│  └─ DeterministicGatewayRegistrationClient (STUB)   │
│       returns gw-{profileId:N}  (NO HTTP)           │
└───────────────────┬─────────────────────────────────┘
                    │ ← STUB — contract does not exist yet
                    ↓
┌─────────────────────────────────────────────────────┐
│                  conexus (FastAPI)                  │
│                                                     │
│  POST /v1/chat/completions  ← only real integration │
│  GET/POST /admin/*          ← BO only               │
│  GET /health, /health/ready                         │
│                                                     │
│  [/internal/* endpoints: NOT IMPLEMENTED]           │
└─────────────────────────────────────────────────────┘
```

LLM call flow (real, working today):
```
conexus.adaptation evaluation
  → HttpConexusLlmClient
  → POST /v1/chat/completions (Bearer cx_live_...)
  → GatewayProvider (Anthropic primary → OpenAI fallback)
  → ConexusAnswerResult (answer, tokens, cost, latency)
```

---

## Boundary Map

### What belongs in `conexus`

- LLM provider routing, failover, and model aliasing.
- Request logging, token accounting, cost estimation.
- Project API key issuance and enforcement.
- Per-project rate/cost limits.
- Provider secret management.
- Admin BO UI and API.
- Audit trail of admin actions.
- **(future)** Internal adapter profile registry: active profile per domain, canary routing percentages.
- **(future)** Internal observability endpoint for drift signal emission to registered clients.

### What belongs in `conexus.adaptation`

- Adaptation plan creation, approval, and execution.
- Evaluation pipeline: corpus loading, indexing, QA pair generation, scoring, metric gates.
- Adapter profile assembly, versioning, and state machine (draft → published → canary → promoted → rolled-back).
- Deployment authorization (role-based publish/promote/rollback gates).
- Drift detection and reevaluation triggers.
- Evaluation evidence projection (BO-safe truncated views).
- Outbox-based event relay.

### What must NOT leak across the boundary

| Direction | What must not cross |
|-----------|---------------------|
| adaptation → gateway | Raw evaluation evidence, prompt content, retrieved context chunks, training data, security evaluation details, evaluation question/answer pairs |
| gateway → adaptation | Plaintext project API keys, provider API key fragments, raw upstream provider response bodies, user PII from request logs |
| Both directions | Exception stack traces, DB query plans, internal service URLs |

### Boundary confusion / duplicated responsibility

| Issue | Severity | Notes |
|-------|----------|-------|
| Adapter profile lifecycle state machine lives entirely in `conexus.adaptation`, but `conexus` will need a shadow of "active profile per domain" for routing | P1 | State synchronization protocol not defined |
| `GatewayRegistration:ApiKey` in `conexus.adaptation` duplicates the concept of project API keys in `conexus`, but the key format and issuing mechanism are not shared | P1 | No guidance on whether to reuse `cx_live_*` keys or issue a service-identity key |
| `conexus.adaptation` has its own deployment authorization (roles in request body); `conexus` has no concept of deployment authorization | P2 | Roles in request body is an internal/dev mechanism only — not suitable for a real security boundary |
| No shared DTO library exists; DTOs are defined independently in both repos | P2 | Casing conventions differ (Python snake_case vs C# PascalCase); risk of silent field mismatch on any new integrated DTOs |

---

## Adapter Profile Lifecycle Sequence

```
conexus.adaptation                          conexus (gateway)
─────────────────                           ─────────────────

1. Plan created (draft)
2. Plan approved
3. Run triggered
4. Corpus loaded, indexed
5. QA pairs generated
6. LLM evaluation via HttpConexusLlmClient ─→ POST /v1/chat/completions
7. Metrics scored, gates checked
8. AdapterProfile assembled                     ↑ only real integration today
9. PublishAdapterProfile command
   → IConexusGatewayRegistrationClient
     .RegisterAsync()                        ─→ [STUB: DeterministicGatewayRegistrationClient]
                                             ─→ [MISSING: POST /internal/adapter-profiles]
10. ActivateCanary command
    → [STUB/no HTTP]                         ─→ [MISSING: PUT /internal/adapter-profiles/{id}/canary]
11. Live traffic through canary              ─→ [MISSING: canary routing logic in gateway]
12. Promote command
    → [STUB/no HTTP]                         ─→ [MISSING: PUT /internal/adapter-profiles/{id}/promote]
13. Rollback command
    → [STUB/no HTTP]                         ─→ [MISSING: DELETE/PUT /internal/adapter-profiles/{id}/rollback]
14. Drift detection
    → DriftDetectionService                  ─→ [MISSING: GET /internal/adapter-profiles/{id}/metrics]
15. Reevaluation trigger
    → repeat from step 3
```

---

## Drift / Observability Feedback Sequence

```
conexus.adaptation                          conexus (gateway)
─────────────────                           ─────────────────

1. Adaptation profile is active in gateway  ─→ [MISSING: active profile routing]
2. Real user requests route through profile ─→ request logged in gateway_requests
3. DriftDetectionService triggered
   (periodic or event-driven)
4. Fetch observability window               ─→ [MISSING: GET /internal/adapter-profiles/{id}/observability
                                                 or direct DB query on gateway_requests]
5. Compute drift score against baseline
6. If score > threshold:
   → Trigger automatic rollback             ─→ [MISSING: PUT /internal/adapter-profiles/{id}/rollback]
   → Queue reevaluation run
```

Currently, steps 1–4 have no implementation in `conexus`. `conexus.adaptation` has the drift detection logic and `DriftOptions`/`RollbackOptions` config, but the observability data feed from `conexus` does not exist.

---

## Endpoint / Client Contract Table

### Implemented today (real integration)

| Client (adaptation) | Server endpoint (conexus) | Status |
|---------------------|--------------------------|--------|
| `HttpConexusLlmClient` → `POST /v1/chat/completions` | ✅ Implemented | Works |

### Designed but not implemented

| Intended client call | Intended server endpoint | Status |
|---------------------|--------------------------|--------|
| `IConexusGatewayRegistrationClient.RegisterAsync()` | `POST /internal/adapter-profiles` | ❌ Stub client, missing endpoint |
| Canary activation notification | `PUT /internal/adapter-profiles/{id}/canary` | ❌ Neither side implemented |
| Canary promotion notification | `PUT /internal/adapter-profiles/{id}/promote` | ❌ Neither side implemented |
| Rollback notification | `PUT /internal/adapter-profiles/{id}/rollback` | ❌ Neither side implemented |
| Active profile lookup | `GET /internal/domains/{domainKey}/active-profile` | ❌ Neither side implemented |
| Observability data pull | `GET /internal/adapter-profiles/{id}/metrics?window=24h` | ❌ Neither side implemented |

---

## DTO Compatibility Notes

### Chat completions (real, working)

| Field | adaptation sends | conexus expects | Match |
|-------|-----------------|-----------------|-------|
| `model` | `<ModelProfile>` string | Any known alias or concrete model name | ⚠ No validation that `ModelProfile` maps to a valid `conexus` alias |
| `messages[].role` | `"system"` / `"user"` | `"system"` / `"user"` / `"assistant"` | ✅ |
| `messages[].content` | String | String | ✅ |
| `temperature` | `0` (hardcoded) | Float optional | ✅ |
| `stream` | Not sent | Bool optional (default false) | ✅ |

Response parsing:

| Field | conexus returns | adaptation reads | Match |
|-------|-----------------|-----------------|-------|
| `choices[0].message.content` | String | Primary parse path | ✅ |
| `choices[0].text` | Not returned | Fallback parse path | ⚠ Fallback is dead code — `conexus` never emits `text` field |
| `usage.prompt_tokens` | Integer | `usage.prompt_tokens` | ✅ |
| `usage.completion_tokens` | Integer | `usage.completion_tokens` | ✅ |
| `cost` | **Not returned** | Optional decimal or string | ⚠ `EstimatedCost` will always be null/zero for HTTP-mode evaluations |
| `provider` | String | Not read | ✅ (ignored) |
| `fallback_used` | Bool | Not read | ✅ (ignored) |

**P2 issue:** `cost` / `estimated_cost` is not returned by `conexus` in `/v1/chat/completions` responses. `conexus.adaptation` optionally parses it; `EstimatedCost` will be null in all real evaluations until `conexus` adds this field.

**P3 issue:** `choices[0].text` fallback in `HttpConexusLlmClient` is dead code. `conexus` never returns a `text` field.

### Gateway registration (stub — no real contract yet)

There is no agreed DTO for adapter profile registration. `DeterministicGatewayRegistrationClient` returns `gw-{profileId:N}` with no request payload sent. A real HTTP client would need to define:

- **Registration request DTO:** profile metadata, domain key, model profile, prompt profile, index metadata, evaluation summary (not raw evidence — see security section).
- **Registration response DTO:** gateway-assigned profile ID, status, registered timestamp.

This contract is entirely undefined and must be designed before any real HTTP implementation begins.

---

## Security Risks

| Risk | Severity | Description |
|------|----------|-------------|
| Internal endpoints do not exist yet, so they cannot be accidentally exposed today — but the auth mechanism is also undefined | P0 | When `/internal/*` endpoints are implemented, `X-Internal-Api-Key` or equivalent must be designed and validated before the first deploy. Key issuance, rotation, and network-layer protection must all be specified. |
| `GatewayRegistration:ApiKey` in `conexus.adaptation` has no corresponding issuance or validation mechanism in `conexus` | P0 | If a real HTTP registration client is added without a matching auth check in `conexus`, the endpoint will be unauthenticated or reject all requests on day one |
| Deployment authorization uses roles in HTTP request body | P1 | `{ publishedByUserId, roles: ["AdaptationPublisher"] }` — the caller supplies their own roles. Appropriate only for internal calls behind a hard network boundary; not suitable for any externally reachable endpoint |
| Adapter profile metadata could include prompt content, retrieved context, or PII if not truncated before registration | P1 | `EvaluationEvidenceProjection` applies truncation limits for the BO view, but the registration DTO is undefined — no guarantee that evidence is excluded |
| `conexus` logs `error_message` from provider responses in the `gateway_requests` table | P2 | If an upstream provider includes user content in error messages, it lands in the DB. Not currently a gap in `conexus.adaptation`, but relevant to the shared request log |
| No network isolation between internal and public endpoints | P2 | Both would share the same FastAPI process and port. Mitigation requires a separate service, auth middleware, or network policy |
| `ENCRYPTION_KEY` validated at `conexus` startup; `conexus.adaptation` has no equivalent at-rest encryption for adapter profile data | P3 | Low risk today given SQLite single-host deployment; relevant when moving to shared PostgreSQL |

**Future hardening options (do not implement now):**
- mTLS between `conexus.adaptation` and `conexus` internal surface.
- Signed service tokens (short-lived JWTs issued by an identity service).
- Private network only (VPC/subnet isolation for `/internal/*`).
- Gateway allowlist: `conexus` accepts internal calls only from known source IPs.

---

## Reliability Risks

| Risk | Severity | Description |
|------|----------|-------------|
| Gateway registration is on the critical path — publish fails → profile never activates | P1 | When real, a timeout or 502 from `conexus` blocks the profile lifecycle. Retry and idempotency semantics for `/internal/adapter-profiles` must be defined before implementation |
| `conexus.adaptation` outbox worker has O(N) claim sorting (TD-002) | P1 | Under load, if deployment events queue up, the outbox degrades. Not a gateway integration issue but affects event relay |
| `conexus` has no circuit breaker — if `conexus.adaptation` sends many concurrent registration/canary/rollback calls, all hit the FastAPI process directly | P1 | Mitigation: idempotent endpoints + retry backoff in adaptation client (backoff already exists for LLM calls via tenacity/WorkerBackoff) |
| `conexus` down during profile registration | P1 | `PublishAdapterProfileCommandHandler` would catch a 502/timeout, return error, profile stays in draft. No retry is implemented today |
| `conexus.adaptation` down | P1 | `conexus` continues serving LLM requests normally — no dependency in that direction. Active profiles (when implemented) remain in last-known state until TTL or manual action. No degraded mode is defined |
| Internal key missing or wrong | P1 | Registration, canary, promote, rollback all fail with 401/403. Profile lifecycle is blocked. No fallback |
| Streaming: no mid-stream fallback in `conexus` | P2 | If Anthropic fails mid-stream, the stream terminates. `conexus.adaptation` does not use streaming, so this is not a current integration concern |
| Single-replica assumption for `conexus.adaptation` | P2 | Workers use distributed DB locking (`LockTimeoutSeconds`), suggesting multi-replica awareness, but SQLite serializes writes — multi-replica is not safe in practice |

---

## Scalability Risks

| Risk | Severity | Description |
|------|----------|-------------|
| `conexus.adaptation` uses SQLite for persistence | P2 | SQLite does not support concurrent writes. Multi-replica production deployment requires migration to PostgreSQL |
| Outbox worker polling interval is fixed, not adaptive | P2 | Fixed `Outbox:PollingIntervalMs` — no backpressure under event bursts |
| `conexus` `gateway_requests` table has no partitioning or TTL strategy | P3 | Long-lived append-only table. Not a demo concern; relevant at production scale |

---

## Contract Mismatches

| Mismatch | Severity | Impact |
|----------|----------|--------|
| `cost` / `estimated_cost` field not returned by `conexus` in `/v1/chat/completions` | P2 | `EstimatedCost` is always null in `ConexusAnswerResult` for HTTP-mode evaluations |
| `choices[0].text` fallback in `HttpConexusLlmClient` is unreachable | P3 | `conexus` never emits the `text` field; dead code path |
| `GatewayRegistration:ApiKey` has no corresponding validation or issuance in `conexus` | P0 | Real registration will fail auth on the first call |
| No agreed registration request/response DTO | P0 | No shared contract exists for the profile registration call |
| No agreed canary/promote/rollback notification DTO | P0 | Entire deployment notification surface is undefined on both sides |
| Casing: `conexus` uses `snake_case` JSON; `conexus.adaptation` uses `PascalCase` C# DTOs with `[JsonPropertyName]` attributes | P2 | Must be verified field-by-field on any new DTOs; `HttpConexusLlmClient` handles this correctly today, but new integrated DTOs will need the same care |
| No shared lifecycle status enum | P2 | `conexus.adaptation` has `AdapterProfileStatus` (Draft, Published, Canary, Promoted, RolledBack). `conexus` has no equivalent. Shadow state values must match exactly when added to `conexus` |

---

## Missing Tests

| Test | Priority | Repo |
|------|----------|------|
| Contract test: `POST /v1/chat/completions` with a `model` value that is not a valid alias → 400 | P1 | Both — verify adaptation never sends unknown model names |
| Contract test: `HttpConexusLlmClient` when `conexus` returns a `cost` field → parsed correctly | P2 | adaptation |
| Contract test: `HttpConexusLlmClient` when `conexus` does NOT return `cost` → null, no exception | P2 | adaptation |
| `DeterministicGatewayRegistrationClient` vs real client behavior divergence test | P1 | adaptation |
| Internal registration endpoint contract test (when implemented) | P0 | conexus |
| Idempotency: duplicate publish call returns `WasDuplicate: true` | P1 | adaptation (API test) |
| Canary → promote → rollback sequence test | P1 | adaptation (integration test) |
| Failure mode: registration 502 → profile stays in draft, response body not in exception | P1 | adaptation |
| Failure mode: registration timeout → profile stays in draft, `CONEXUS_TIMEOUT` error code | P1 | adaptation |
| Failure mode: internal key missing → registration returns 401 | P1 | conexus (when implemented) |
| Observability window query returns correct metrics for a given profile ID | P1 | conexus (when implemented) |
| Drift score > threshold triggers rollback command | P1 | adaptation |
| Drift score with empty observation window → neutral, no rollback | P1 | adaptation |

---

## Demo Readiness Checklist

### Must resolve before demo (P0)

- [ ] **Decide and document:** Will the demo use `DeterministicGatewayRegistrationClient` (stub), or will real `/internal/*` endpoints be implemented? If stub, the demo script must not claim that profiles are "registered in Conexus."
- [ ] **Verify model profile name alignment:** Confirm that `Conexus:DefaultModelProfile` values used in `conexus.adaptation` match valid model aliases in `conexus` (`conexus-fast`, `conexus-default`, `gpt-4o`, `claude-haiku-4-5-20251001`, etc.). A mismatch returns 400 with no user-visible diagnostic.
- [ ] **Document `GatewayRegistration:ApiKey` setup:** Without a defined issuance path, any move to real registration fails immediately on auth.

### Should document before demo (P1)

- [ ] State clearly in the demo script whether gateway integration is stub or live.
- [ ] Document the one-way data flow: adaptation calls `conexus` for LLM evaluation; `conexus` does not call adaptation.
- [ ] Document what "published" means today (profile stored in adaptation DB, stub `gw-*` ID returned) versus what it will mean in production (profile registered in `conexus` routing table).
- [ ] Document required env vars for a local-dev demo (see Operational Model section).

### Can safely wait (P2/P3)

- [ ] Real `/internal/*` endpoint implementation.
- [ ] Real `HttpConexusGatewayRegistrationClient`.
- [ ] Drift feedback loop.
- [ ] Canary traffic routing in `conexus`.
- [ ] `estimated_cost` field added to `/v1/chat/completions` response.
- [ ] mTLS or signed service tokens for internal auth.
- [ ] Shared DTO schema library.

### Could embarrass us in a demo if ignored

- Claiming profile is "live in the gateway" when `DeterministicGatewayRegistrationClient` is active — the profile exists only in the adaptation DB.
- Sending an unknown model profile name to `conexus` — returns 400 with no helpful message surfaced in the BO.
- `EstimatedCost` always showing null in evaluation results because `conexus` does not return it.
- Running the demo without `Conexus:BaseUrl` / `Conexus:ApiKey` configured — all LLM evaluation steps silently fall back to the fake client with no warning shown in the UI.

---

## Operational Model

### Required env vars — `conexus` (FastAPI)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `ENCRYPTION_KEY` | Yes | Fernet key for provider secret encryption |
| `AUTH_SECRET` | Yes | HMAC secret for admin session tokens |
| `ADMIN_USERNAME` | Yes (prod) | Default admin username |
| `ADMIN_PASSWORD` | Yes (prod) | Default admin password |
| `CORS_ALLOWED_ORIGINS` | Yes (prod) | Comma-separated origins; no wildcard in prod |
| `OPENAI_API_KEY` | Conditional | Required if routing to OpenAI |
| `ANTHROPIC_API_KEY` | Conditional | Required if routing to Anthropic |
| `LLM_PROVIDER` | No | Default: `gateway` |

### Required env vars — `conexus.adaptation` (.NET)

| Variable | Required | Description |
|----------|----------|-------------|
| `ConnectionStrings:Adaptation` | Yes | SQLite (dev) or PostgreSQL (prod) |
| `Conexus:BaseUrl` | Yes (HTTP mode) | e.g., `http://localhost:8000` |
| `Conexus:ApiKey` | Yes (HTTP mode) | Project API key issued by `conexus` (`cx_live_*`) |
| `Conexus:TimeoutSeconds` | No | Default: 30; clamped 1–300 |
| `Conexus:DefaultModelProfile` | No | Default model alias (must be a valid `conexus` alias) |
| `GatewayRegistration:BaseUrl` | Yes (when real) | Not needed while stub is active |
| `GatewayRegistration:ApiKey` | Yes (when real) | Not issued or validated yet |
| `GatewayRegistration:Enabled` | No | Default: true |
| `Corpus:BasePath` | Yes | Local corpus directory |

### Deployment order

1. Start PostgreSQL (or confirm connection).
2. Start `conexus` backend. Wait for `GET /health/ready` → 200.
3. Create a project and issue an API key in the `conexus` BO (or via admin API).
4. Set `Conexus:ApiKey` in `conexus.adaptation` config.
5. Start `conexus.adaptation`. EF migrations run on startup (dev default).

### Failure modes

| Failure | Impact on `conexus` | Impact on `conexus.adaptation` |
|---------|---------------------|-------------------------------|
| `conexus` is down | — | LLM evaluation steps fail with `CONEXUS_HTTP_ERROR` or `CONEXUS_TIMEOUT`. Runs cannot complete. Workers retry with jitter. No data loss. |
| `conexus.adaptation` is down | `conexus` serves LLM requests normally. No dependency. | — |
| Internal key missing/wrong | — | Registration, canary, promote, rollback (when real) all fail with 401/403. Profile lifecycle blocked. Worker retries with backoff. |
| SQLite locked (adaptation) | — | Concurrent worker writes serialized. Multi-replica unsupported with SQLite. |

### Single-replica vs multi-replica

| Service | Multi-replica safe? | Notes |
|---------|---------------------|-------|
| `conexus` | Yes | Stateless process; shared PostgreSQL |
| `conexus.adaptation` | No (with SQLite) | SQLite serializes writes; distributed DB row locking exists but concurrent writers will conflict |

### Local-dev vs production

| Aspect | Local dev | Production |
|--------|-----------|-----------|
| `conexus` DB | SQLite via `ALLOW_CREATE_ALL=true` or PostgreSQL | PostgreSQL + Alembic migrations |
| `conexus.adaptation` DB | SQLite | PostgreSQL recommended |
| LLM client | `FakeConexusLlmClient` (no `Conexus:BaseUrl` set) | `HttpConexusLlmClient` |
| Gateway registration | `DeterministicGatewayRegistrationClient` (stub) | Real `HttpConexusGatewayRegistrationClient` (not yet built) |
| Admin auth | Env-based (`ADMIN_USERNAME`/`ADMIN_PASSWORD`) | DB-backed admin users recommended |
| CORS | Wildcard allowed | Strict `CORS_ALLOWED_ORIGINS` required |

---

## Contract Tests — Proposed

### Group 1: `conexus` — LLM endpoint contracts (testable today)

1. `POST /v1/chat/completions` with valid Bearer key and known alias → 200, `choices[0].message.content` present, `usage.prompt_tokens` and `usage.completion_tokens` non-zero.
2. `POST /v1/chat/completions` with unknown model → 400.
3. `POST /v1/chat/completions` with revoked API key → 401.
4. `POST /v1/chat/completions` with project over hard cost limit → 429, body includes `limit_type`, `reset_at`.
5. `POST /v1/chat/completions` response does NOT include `cost` field → confirm `conexus.adaptation` parses correctly (null `EstimatedCost`, no exception).

### Group 2: `conexus.adaptation` — gateway client contracts (testable today against stub; real when endpoints exist)

6. `DeterministicGatewayRegistrationClient.RegisterAsync()` returns `gw-{profileId:N}` — verifies stub contract shape.
7. `HttpConexusLlmClient` with valid config → `ConexusAnswerResult.Answer` non-empty.
8. `HttpConexusLlmClient` with non-2xx (mock 429) → error code `CONEXUS_NON_2XX`, response body absent from exception message.
9. `HttpConexusLlmClient` with send timeout → error code `CONEXUS_TIMEOUT`.
10. `HttpConexusLlmClient` with malformed JSON → error code `CONEXUS_MALFORMED_RESPONSE`.

### Group 3: Adapter profile lifecycle (adaptation self-contained, testable today)

11. Publish → `WasDuplicate: false` on first call, `WasDuplicate: true` on idempotent repeat.
12. Publish → ActivateCanary → verify `Status == Canary`, `CanaryPercent` in [1, 50].
13. Publish → ActivateCanary → Promote → verify `Status == Promoted`.
14. Publish → ActivateCanary → Rollback → verify `Status == RolledBack`, `RolledBackAt` set.
15. ActivateCanary with `canaryPercent > 50` → 422.
16. Promote without prior ActivateCanary → 409 (state conflict).
17. Rollback without prior Publish → 409 (state conflict).
18. 403 if caller roles do not match `RequiredRolesForPublish`.

### Group 4: Failure mode and cross-repo (requires real endpoints when built)

19. `RegisterAsync()` with `conexus` returning 502 → profile remains in draft, error message does not include response body.
20. `RegisterAsync()` timeout → profile remains in draft, error code `CONEXUS_TIMEOUT`.
21. `RegisterAsync()` with wrong internal key → 401 from `conexus` → profile blocked.
22. Drift score > threshold → rollback command triggered, profile transitions to `RolledBack`.
23. Observability window query returns empty (no requests in window) → drift score neutral, no rollback.

### Cross-repo fixture JSON examples

**Profile registration request (to be defined — not yet implemented):**
```json
{
  "profileId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "domainKey": "gaming-crm",
  "modelProfile": "conexus-fast",
  "promptProfile": "rag-cite-v1",
  "indexMetadata": {
    "chunkCount": 42,
    "corpusHash": "sha256:abc123"
  },
  "evaluationSummary": {
    "precision": 0.87,
    "recall": 0.82,
    "gatesPassed": true
  }
}
```

**Profile registration response (to be defined):**
```json
{
  "gatewayProfileId": "gw-3fa85f645717...",
  "status": "registered",
  "registeredAt": "2026-04-30T12:00:00Z"
}
```

---

## Owner Decisions Required

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Demo uses stub or real `/internal/*` endpoints? | A) Stub for demo, real later. B) Build minimal registration endpoint now. | **A** — stub is safe for demo; document clearly that profiles are not live in the gateway |
| 2 | Auth mechanism for `/internal/*` endpoints | A) `X-Internal-Api-Key` header. B) Reuse project API keys with a special service project. C) mTLS. | **A for now** — simplest; document the key rotation process |
| 3 | Should `conexus` return `estimated_cost` in `/v1/chat/completions` response? | A) Yes, add to response DTO. B) No, adaptation maintains its own cost table. | **A** — single cost source of truth; adaptation reads it passively |
| 4 | DB for `conexus.adaptation` in production | A) Stay on SQLite. B) Migrate to PostgreSQL. | **B** — required before multi-replica deployment |
| 5 | Registration DTO design | Owner must define before any real HTTP client is built. | Block on this before implementing Group 4 tests |

---

## 30 / 60 / 90 Minute Cleanup Plan

### 30 minutes (demo-blocking)

1. Verify that `Conexus:DefaultModelProfile` values are valid `conexus` model aliases — check `gateway_router.py` alias table against `conexus.adaptation` config.
2. Add one sentence to `conexus/README.md`: "Adapter profile `/internal/*` endpoints are not yet implemented."
3. Add one sentence to `conexus.adaptation/README.md`: "Gateway registration currently uses `DeterministicGatewayRegistrationClient` (stub). Profiles are stored in the adaptation DB only; they are not registered in the live `conexus` routing table."

### 60 minutes (should do before demo)

4. Extract the Operational Model section above into `docs/LOCAL_DEV_SETUP.md` in each repo as a quick-start card.
5. Add contract test Group 1 items 1–4 to the `conexus` test suite.
6. Verify Group 2 items 7–10 are covered in `conexus.adaptation` — the test gap analysis indicates most are already present.

### 90 minutes (quality of life)

7. Add `estimated_cost` field to `conexus` `/v1/chat/completions` response DTO and confirm `HttpConexusLlmClient` parses it without exception when present.
8. Document Owner Decisions 1–3 as a short ADR in `conexus/docs/ADRs/`.
9. Cross-link this review from `conexus.adaptation/docs/agent-review/CONEXUS_ADAPTATION_AGENT_CHANGELOG.md`.

---

## Longer-Term Production Hardening Roadmap

| Phase | Work | Dependency |
|-------|------|------------|
| v0.4 | Implement `POST /internal/adapter-profiles` in `conexus` with `X-Internal-Api-Key` auth | Owner Decision 2 |
| v0.4 | Implement `HttpConexusGatewayRegistrationClient` in `conexus.adaptation` | Endpoint + DTO design (Decision 5) |
| v0.4 | Add `estimated_cost` to `/v1/chat/completions` response | Owner Decision 3 |
| v0.5 | Canary routing in `conexus` (`X-Conexus-Profile-Id` header or domain routing table) | Registration endpoint stable |
| v0.5 | Drift observability endpoint in `conexus` | Canary routing in place |
| v0.5 | Migrate `conexus.adaptation` to PostgreSQL | Owner Decision 4 |
| v0.6 | mTLS or signed service tokens for internal endpoint auth | v0.4 endpoints stable |
| v0.6 | Shared DTO schema (OpenAPI fragment or AsyncAPI) | Both teams aligned |
| v0.7 | Cross-repo contract test suite in CI | Shared DTO schema |
| v1.0 | Network isolation: `/internal/*` on separate port or private subnet | Infrastructure ready |
