# Cross-Repo Conexus Integration Review

**Scope:** `conexus` (FastAPI LLM gateway) ↔ `conexus.adaptation` (.NET adaptation orchestrator)  
**Date:** 2026-04-30  
**Reviewer:** Agent cross-repo review — v2 (corrected after implementation verification)  
**Status:** Draft — awaiting owner decisions on P1 items

---

## Correction Notice

The first draft of this review contained a material factual error: it incorrectly claimed that `/internal/*` endpoints do not exist in `conexus`. They are fully implemented. This version corrects that claim and rewrites all affected sections based on direct inspection of the implementation files.

---

## Executive Summary

**What works today (confirmed by code inspection):**
- `HttpConexusLlmClient` → `POST /v1/chat/completions` — real, tested HTTP integration with full error handling and response body redaction.
- All six `/internal/*` adapter profile endpoints are implemented and tested in `conexus`:
  - `POST /internal/adapter-profiles/register` — idempotent by `adapterProfileId`
  - `POST /internal/adapter-profiles/{gatewayProfileId}/activate-canary`
  - `POST /internal/adapter-profiles/{gatewayProfileId}/promote`
  - `POST /internal/adapter-profiles/{gatewayProfileId}/rollback`
  - `GET /internal/adapter-profiles/{gatewayProfileId}/observability`
  - `GET /internal/domains/{domainKey}/active-profile`
- All internal endpoints use `X-Internal-Api-Key` header auth backed by `INTERNAL_ADAPTER_API_KEY` env var.
- `conexus` DB has `GatewayAdapterProfile` and `GatewayAdapterProfileActivation` tables; `GatewayRequest` rows carry `gateway_profile_id` for per-profile observability queries.
- `conexus` admin BO — request logs, provider usage, project management, audit trail.

**What is still stub-only in `conexus.adaptation` (confirmed by code inspection):**
- `DeterministicGatewayRegistrationClient` is the only implementation of `IConexusGatewayRegistrationClient`. No `HttpConexusGatewayRegistrationClient` exists. Registration returns `gw-{profile.Id:N}` with no HTTP call.
- `DeterministicAdaptationObservabilityClient` is the only implementation of `IAdaptationObservabilityClient`. No HTTP client calls `GET /internal/adapter-profiles/{id}/observability`. Returns hardcoded metrics.
- Canary activation, promote, and rollback commands in `conexus.adaptation` do NOT call the corresponding `/internal/*` endpoints in `conexus`. They manage state in the adaptation DB only and never notify the gateway.

**The integration gap has shifted:** The problem is not that `conexus` is missing endpoints. The problem is that `conexus.adaptation` has no real HTTP clients for the profile lifecycle or observability endpoints, and the interface signatures have DTO mismatches with the real endpoint shapes.

**Are they conceptually aligned?**  
Yes. The architecture is coherent. The implementation gap is one-sided: `conexus` server side is ready; `conexus.adaptation` client side is not wired up.

---

## Current Actual Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                  conexus.adaptation (.NET)                    │
│                                                               │
│  Planning → Approval → Execution → Evaluation                 │
│       ↓                                                       │
│  AdapterProfile lifecycle (publish/canary/promote/rollback)   │
│  — state managed in adaptation DB only —                      │
│                                                               │
│  IConexusGatewayRegistrationClient                            │
│  └─ DeterministicGatewayRegistrationClient (STUB, no HTTP)    │
│                                                               │
│  IAdaptationObservabilityClient                               │
│  └─ DeterministicAdaptationObservabilityClient (STUB, no HTTP)│
│       returns hardcoded metrics                               │
│                                                               │
│  canary/promote/rollback commands → adaptation DB only        │
│  (DO NOT call /internal/* endpoints in conexus)               │
└──────────────┬────────────────────────────────────────────────┘
               │ POST /v1/chat/completions (HttpConexusLlmClient — REAL)
               │
               │ POST /internal/adapter-profiles/register       ← STUB on client side
               │ POST /internal/.../{id}/activate-canary        ← NOT called
               │ POST /internal/.../{id}/promote                ← NOT called
               │ POST /internal/.../{id}/rollback               ← NOT called
               │ GET  /internal/.../{id}/observability          ← STUB on client side
               │ GET  /internal/domains/{key}/active-profile    ← NOT called
               ↓
┌───────────────────────────────────────────────────────────────┐
│                     conexus (FastAPI)                         │
│                                                               │
│  POST /v1/chat/completions              ✅ implemented         │
│  POST /internal/adapter-profiles/register ✅ implemented      │
│  POST /internal/.../{id}/activate-canary  ✅ implemented      │
│  POST /internal/.../{id}/promote          ✅ implemented      │
│  POST /internal/.../{id}/rollback         ✅ implemented      │
│  GET  /internal/.../{id}/observability    ✅ implemented      │
│  GET  /internal/domains/{key}/active-profile ✅ implemented   │
│                                                               │
│  ADAPTER_PROFILE_CANARY_ROUTING_ENABLED=false (default)       │
│  — profiles registered and tracked, traffic not yet split —   │
└───────────────────────────────────────────────────────────────┘
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
- Internal adapter profile registry: `GatewayAdapterProfile` records, canary/active/rollback activation state, per-profile observability windows over `gateway_requests`.
- **(pending flag enable)** Canary traffic routing: `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED` exists in config but defaults to `false`; no routing logic reads this flag yet.

### What belongs in `conexus.adaptation`

- Adaptation plan creation, approval, and execution.
- Evaluation pipeline: corpus loading, indexing, QA pair generation, scoring, metric gates.
- Adapter profile assembly, versioning, and state machine (draft → published → canary → promoted → rolled-back) in adaptation DB.
- Deployment authorization (role-based publish/promote/rollback gates).
- Drift detection and reevaluation triggers.
- Evaluation evidence projection (BO-safe truncated views).
- Outbox-based event relay.
- Calling `conexus` `/internal/*` endpoints to synchronize profile lifecycle state into the gateway (currently stub).

### What must NOT leak across the boundary

| Direction | What must not cross |
|-----------|---------------------|
| adaptation → gateway | Raw evaluation evidence, prompt content, retrieved context chunks, training data, security evaluation details, evaluation question/answer pairs |
| gateway → adaptation | Plaintext project API keys, provider API key fragments, raw upstream provider response bodies, user PII from request logs |
| Both directions | Exception stack traces, DB query plans, internal service URLs |

### Boundary confusion / duplicated responsibility

| Issue | Severity | Notes |
|-------|----------|-------|
| Two parallel lifecycle state machines: adaptation DB tracks `AdapterProfileStatus`; `conexus` DB tracks `GatewayAdapterProfileActivation.status`. They are not synchronized because canary/promote/rollback commands do not call the gateway | P1 | When stub is replaced, both must stay consistent. A failure at the gateway call after adaptation DB commit leaves state split across both systems. |
| `GatewayRegistration:ApiKey` in `conexus.adaptation` maps to `INTERNAL_ADAPTER_API_KEY` in `conexus`, but the key issuance and rotation process is undocumented | P1 | No guidance on how this key is minted, rotated, or revoked. |
| `conexus.adaptation` has its own deployment authorization (roles in request body); `conexus` `/internal/*` endpoints use `X-Internal-Api-Key` only — no role awareness | P2 | Roles in request body is an internal/dev mechanism only. `conexus` trusts any caller with the internal key regardless of role. |
| No shared DTO library; request/response DTOs defined independently in both repos | P2 | Casing conventions differ (Python `camelCase` JSON from `conexus`; C# `PascalCase` DTOs in adaptation); risk of silent field mismatch on any new integration. |

---

## Adapter Profile Lifecycle Sequence

```
conexus.adaptation                              conexus (gateway)
─────────────────                               ─────────────────

1. Plan created (draft)
2. Plan approved
3. Run triggered
4. Corpus loaded, indexed
5. QA pairs generated
6. LLM evaluation via HttpConexusLlmClient ───→ POST /v1/chat/completions   ✅ REAL
7. Metrics scored, gates checked
8. AdapterProfile assembled
9. PublishAdapterProfileCommandHandler
   → IConexusGatewayRegistrationClient
     .RegisterAsync(profile, evidence)      ──→ [STUB: returns gw-{profile.Id:N}]
                                                 real target: POST /internal/adapter-profiles/register  ✅ ready
10. ActivateCanaryAdapterProfileCommandHandler
    → IAdapterProfileActivationRepository   ← adaptation DB only
    (no HTTP call to conexus)                    real target: POST /internal/.../{id}/activate-canary  ✅ ready
11. PromoteAdapterProfileCommandHandler
    → IAdapterProfileActivationRepository   ← adaptation DB only
    (no HTTP call to conexus)                    real target: POST /internal/.../{id}/promote          ✅ ready
12. RollbackAdapterProfileCommandHandler
    → IAdapterProfileActivationRepository   ← adaptation DB only
    (no HTTP call to conexus)                    real target: POST /internal/.../{id}/rollback         ✅ ready
13. DriftAssessmentService
    → IAdaptationObservabilityClient
      .GetSnapshotAsync(profileId)          ──→ [STUB: hardcoded metrics]
                                                 real target: GET /internal/.../{id}/observability    ✅ ready
14. Drift triggers reevaluation
    → repeat from step 3
```

Note: Live canary traffic routing in `conexus` requires `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED=true`. This flag exists in config but no routing logic currently reads it. Setting it to `true` today would have no effect on request dispatch.

---

## Drift / Observability Feedback Sequence

```
conexus.adaptation                              conexus (gateway)
─────────────────                               ─────────────────

1. Profile registered via stub (not in        ← gateway_adapter_profiles table NOT populated
   real conexus DB)                              (until HttpConexusGatewayRegistrationClient is built)
2. Real user requests routed through           ← gateway_requests rows include gateway_profile_id
   active profile                                (field exists; populated when profile ID is known)
3. DriftAssessmentService triggered
   → IAdaptationObservabilityClient
     .GetSnapshotAsync(profile.Id)            ──→ [STUB: hardcoded metrics, no HTTP]
                                                   real target: GET /internal/.../{gatewayProfileId}/observability
                                                   NOTE: interface takes Guid (adaptation profile ID);
                                                   endpoint takes string gatewayProfileId → TYPE MISMATCH
4. Drift score computed against baseline
5. If score > threshold:
   → automatic rollback triggered in
     adaptation DB only
   (no notification to conexus gateway)
```

---

## Endpoint / Client Contract Table

### Real integration (working today)

| Client (adaptation) | Server endpoint (conexus) | Auth | Status |
|---------------------|--------------------------|------|--------|
| `HttpConexusLlmClient` → `POST /v1/chat/completions` | ✅ Implemented | `Authorization: Bearer <project_key>` | ✅ Works |

### Endpoints implemented in `conexus`; clients stubbed in `conexus.adaptation`

| Intended client call | Server endpoint (conexus) | Server status | Client status |
|---------------------|--------------------------|---------------|---------------|
| `IConexusGatewayRegistrationClient.RegisterAsync()` | `POST /internal/adapter-profiles/register` | ✅ Implemented, tested | ❌ Stub only (`DeterministicGatewayRegistrationClient`) |
| (not called) canary activation notify | `POST /internal/adapter-profiles/{gatewayProfileId}/activate-canary` | ✅ Implemented, tested | ❌ No client; adaptation uses own DB |
| (not called) promote notify | `POST /internal/adapter-profiles/{gatewayProfileId}/promote` | ✅ Implemented, tested | ❌ No client; adaptation uses own DB |
| (not called) rollback notify | `POST /internal/adapter-profiles/{gatewayProfileId}/rollback` | ✅ Implemented, tested | ❌ No client; adaptation uses own DB |
| `IAdaptationObservabilityClient.GetSnapshotAsync()` | `GET /internal/adapter-profiles/{gatewayProfileId}/observability` | ✅ Implemented, tested | ❌ Stub only (`DeterministicAdaptationObservabilityClient`) |
| (not called) | `GET /internal/domains/{domainKey}/active-profile` | ✅ Implemented, tested | ❌ No client |

---

## DTO Compatibility Notes

### Chat completions (real, working)

| Field | adaptation sends | conexus expects | Match |
|-------|-----------------|-----------------|-------|
| `model` | `<ModelProfile>` string | Any known alias or concrete model name | ⚠ No validation that `ModelProfile` maps to a valid `conexus` alias; mismatch returns 400 |
| `messages[].role` | `"system"` / `"user"` | `"system"` / `"user"` / `"assistant"` | ✅ |
| `messages[].content` | String | String | ✅ |
| `temperature` | `0` (hardcoded) | Float optional | ✅ |
| `stream` | Not sent | Bool optional (default false) | ✅ |

Response parsing:

| Field | conexus returns | adaptation reads | Match |
|-------|-----------------|-----------------|-------|
| `choices[0].message.content` | String | Primary parse path | ✅ |
| `choices[0].text` | Not returned | Fallback parse path | ⚠ Dead code — `conexus` never emits `text` field |
| `usage.prompt_tokens` | Integer | `usage.prompt_tokens` | ✅ |
| `usage.completion_tokens` | Integer | `usage.completion_tokens` | ✅ |
| `cost` | **Not returned** | Optional decimal or string | ⚠ `EstimatedCost` will always be null/zero for HTTP-mode evaluations |
| `provider` | String | Not read | ✅ (ignored) |
| `fallback_used` | Bool | Not read | ✅ (ignored) |

### Gateway registration — current stub vs. real endpoint (DTO mismatch)

`DeterministicGatewayRegistrationClient` signature:
```csharp
RegisterAsync(AdapterProfile profile, EvaluationEvidenceProjection evidence, CancellationToken ct)
// → returns GatewayAdapterProfileRegistrationResult { Succeeded, GatewayProfileId }
```

`conexus` `POST /internal/adapter-profiles/register` expects:
```json
{
  "adapterProfileId": "...",   // required — maps from profile.Id.ToString()
  "domainKey": "...",           // required — maps from profile.DomainKey
  "runId": "...",               // optional — maps from profile.RunId
  "planId": "...",              // optional — maps from profile.PlanId / profile.PlanKey
  "compositeScore": 0.87,       // optional — maps from evidence.CompositeScore or similar
  "evidenceHash": "...",        // optional — maps from evidence hash
  "semanticContextHash": "...", // optional
  "slodModelVersion": "...",    // optional
  "profileVersion": "...",      // optional — maps from profile.Version
  "metadata": {}                // optional
}
```

`conexus` returns:
```json
{
  "gatewayProfileId": "gw-...",  // maps to GatewayAdapterProfileRegistrationResult.GatewayProfileId
  "status": "Registered"
}
```

The mapping from `AdapterProfile` + `EvaluationEvidenceProjection` to `RegisterAdapterProfileBody` is plausible but requires explicit field mapping work. The real `HttpConexusGatewayRegistrationClient` will need to decide which evidence fields to include and how to compute `compositeScore` and `evidenceHash`.

**Important:** The stub returns `gw-{profile.Id:N}` — a deterministic `gw-` prefix followed by the adaptation profile GUID. The real endpoint also returns a `gw-` prefixed ID, but generates it via `uuid4().hex`. The two IDs will differ for the same profile. Tests that compare stub vs. real `GatewayProfileId` values will fail.

### Observability client — interface vs. real endpoint (type and field mismatch)

`IAdaptationObservabilityClient`:
```csharp
Task<ProfileObservabilitySnapshot> GetSnapshotAsync(Guid profileId, CancellationToken ct)
// profileId is the adaptation profile GUID (e.g. 3fa85f64-...)
```

`conexus` `GET /internal/adapter-profiles/{gatewayProfileId}/observability`:
```
gatewayProfileId = "gw-3fa85f645717..."  ← string, not a Guid; different value from profile.Id
Query params: since (ISO datetime), until (ISO datetime)
```

`conexus` returns `ObservabilityResponse`:
```json
{
  "gatewayProfileId": "gw-...",
  "windowStart": "...",
  "windowEnd": "...",
  "requestCount": 42,
  "errorRate": 0.02,
  "latencyP95Ms": 340,
  "costPerAnswer": 0.0012,
  "citationFailureRate": null,
  "refusalRate": null,
  "userNegativeFeedbackRate": null
}
```

`DeterministicAdaptationObservabilityClient` returns `ProfileObservabilitySnapshot`:
```csharp
{
  ProfileId: profileId,          // Guid
  ObservedAt: DateTimeOffset,
  Metrics: {
    "citation_accuracy": 1.0,    // ← different concept from citationFailureRate
    "latency_ms_p95": 500,       // ← snake_case; real = latencyP95Ms (camelCase, int)
    "cost_per_answer": 0.001     // ← snake_case; real = costPerAnswer (camelCase, float)
  }
}
```

**Mismatches requiring resolution before a real HTTP client can be written:**

| Issue | Severity |
|-------|----------|
| `GetSnapshotAsync(Guid profileId)` passes the adaptation ID; `conexus` endpoint expects the `gatewayProfileId` string. A real HTTP client must translate between them (look up the profile's stored `GatewayProfileId` before calling). | P1 |
| No time window parameter in the interface (`since` / `until` absent); the real endpoint supports windowed queries. | P1 |
| `citation_accuracy` (deterministic stub) vs. `citationFailureRate` (real endpoint) — inverse semantics. A drift rule calibrated against the stub's `citation_accuracy=1.0` will fire incorrectly against `citationFailureRate` data. | P1 |
| Metric key naming: stub uses `snake_case`; `ObservabilityResponse` uses camelCase field names. | P2 |
| `ProfileObservabilitySnapshot.Metrics` is a `Dictionary<string, double>`; the real response is a typed DTO. The real HTTP client will need to project the typed DTO onto the dict, or the interface will need to be redesigned. | P2 |

### Lifecycle status value alignment

| `conexus.adaptation` `AdapterProfileStatus` | `conexus` activation `status` | Match |
|---------------------------------------------|-------------------------------|-------|
| `Draft` | (no row) | n/a |
| `Approved` | (no row) | n/a |
| `Published` | `"Registered"` | ⚠ Different names for same concept |
| `Canary` | `"Canary"` | ✅ |
| `Promoted` | `"Active"` / `"Promoted"` | ⚠ Promoted in conexus is a transient activation row; Active is the current live row. Not a simple mapping. |
| `RolledBack` | `"RolledBack"` | ✅ |
| — | `"Retired"` | Only in conexus; no adaptation equivalent |

---

## Security Risks

| Risk | Severity | Description |
|------|----------|-------------|
| `INTERNAL_ADAPTER_API_KEY` has no documented issuance or rotation process | P1 | The key exists as an env var on the `conexus` side and `GatewayRegistration:ApiKey` on the adaptation side. No guidance on how to mint it, rotate it, or revoke it. If it leaks, all lifecycle endpoints are compromised. |
| `conexus` returns 503 (not 401) when `INTERNAL_ADAPTER_API_KEY` is not configured | P1 | Safe behavior but could cause confusing failure modes during initial deploy if the env var is forgotten. Test `test_internal_api_key_not_configured_returns_503` covers this. |
| `ADAPTER_PROFILE_REGISTRY_ENABLED=false` returns 404 for all internal endpoints | P2 | Intended as an emergency kill switch. The 404 (not 403) is intentional to avoid revealing the endpoint surface. Callers must handle 404 as a registration failure, not as "wrong URL." |
| Deployment authorization uses roles in HTTP request body in `conexus.adaptation` | P2 | `{ publishedByUserId, roles: ["AdaptationPublisher"] }` — caller supplies their own roles. `conexus` internal endpoints have no awareness of this; they accept any call with a valid internal key. Appropriate only behind a hard network boundary. |
| `conexus` internal endpoints share the same port/process as public endpoints | P2 | No network isolation. Any path misconfiguration that removes the `require_internal_adapter_api_key` dependency would expose lifecycle operations publicly. |
| Adapter profile `metadata` field in `RegisterAdapterProfileBody` is a free-form `dict` | P2 | A real client must ensure this field does not contain prompt content, retrieved context, or evaluation evidence. The `EvaluationEvidenceProjection` passed to `RegisterAsync` must not be forwarded as-is. |
| `conexus` logs `error_message` from provider responses in `gateway_requests` | P3 | If an upstream provider includes user content in error messages, it lands in the DB. Not a current gap in `conexus.adaptation`. |

**Future hardening options (do not implement now):**
- mTLS between `conexus.adaptation` and `conexus` internal surface.
- Signed service tokens (short-lived JWTs).
- Private subnet isolation for `/internal/*` endpoints.
- `X-Internal-Actor` header for audit attribution (already supported in `conexus`; adaptation clients should send it).

---

## Reliability Risks

| Risk | Severity | Description |
|------|----------|-------------|
| Dual state: canary/promote/rollback update adaptation DB but do NOT call `conexus` gateway | P1 | Profile status in adaptation and gateway diverge from the moment canary is activated. If the gateway is later called for routing, it will not know about canary state. This is by far the most significant reliability gap. |
| No retry or transactional compensation for gateway registration failure | P1 | `PublishAdapterProfileCommandHandler` calls `RegisterAsync()`, catches failure, and throws `ExternalServiceException`. The adaptation profile stays in `Approved` state. No automatic retry. If the real HTTP client times out, the operator must retry manually. |
| `conexus` rollback requires `previous_gateway_profile_id` | P1 | Rollback returns 409 if there is no previous active profile. The adaptation rollback command does not check this precondition. A real HTTP client must handle a 409 from rollback differently from a network failure. |
| `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED=false` by default | P1 | Even if a profile is in `Canary` state in the `conexus` DB, no traffic is split today. Setting this flag to `true` in the future without implementing the routing logic first would have no effect, but it sets a false expectation. |
| Outbox worker O(N) claim sorting (TD-002) | P1 | Under load, outbox degrades. Affects event relay but not direct gateway calls. |
| `conexus` down during publish | P1 | `ExternalServiceException` thrown; profile stays in `Approved`. No retry. Operator must re-trigger publish. |
| `conexus.adaptation` down | P2 | `conexus` continues serving LLM requests normally. Active profiles in gateway remain active. No degraded mode for `conexus`. |
| Missing internal key at deploy time | P1 | All registration, canary, promote, rollback calls fail with 401 (or 503 if unconfigured). Profile lifecycle blocked. |
| Single-replica assumption for `conexus.adaptation` (SQLite) | P2 | SQLite serializes writes. Multi-replica not safe until migrated to PostgreSQL. |

---

## Scalability Risks

| Risk | Severity | Description |
|------|----------|-------------|
| `conexus.adaptation` uses SQLite | P2 | Multi-replica production deployment requires PostgreSQL migration. |
| Outbox worker polling is fixed, not adaptive | P2 | No backpressure under event bursts. |
| `conexus` `gateway_requests` table has no partitioning or TTL | P3 | Relevant at production scale; not a demo concern. |

---

## Contract Mismatches

| Mismatch | Severity | Impact |
|----------|----------|--------|
| `IAdaptationObservabilityClient.GetSnapshotAsync(Guid profileId)` passes adaptation ID; real endpoint needs `gatewayProfileId` string | P1 | Cannot build real HTTP client without redesigning the interface or adding a lookup step |
| No time window parameters in `GetSnapshotAsync`; real endpoint has `since`/`until` | P1 | Drift assessment cannot use windowed observability data without interface change |
| `citation_accuracy` (stub) vs `citationFailureRate` (real) — inverse semantics | P1 | Drift thresholds calibrated against stub will fire incorrectly on real data |
| `AdapterProfileStatus.Published` vs `conexus` `status="Registered"` | P2 | "Published" in adaptation is "Registered" in the gateway; documentation must clarify |
| `AdapterProfileStatus.Promoted` vs `conexus` `status="Active"` | P2 | "Promoted" leaves a `Promoted` activation row; a new `Active` row is created. Not a simple rename. |
| Stub `GatewayProfileId` format is `gw-{profile.Id:N}` (deterministic); real endpoint generates `gw-{uuid4().hex}` (random) | P2 | Any test comparing stub IDs to real IDs will fail; idempotency tests must be aware |
| `cost` / `estimated_cost` not returned by `conexus` in `/v1/chat/completions` | P2 | `EstimatedCost` always null in `ConexusAnswerResult` for HTTP-mode evaluations |
| Metric key casing: stub uses `snake_case`; real observability response uses camelCase fields | P2 | Must be mapped explicitly in any real HTTP observability client |
| `choices[0].text` fallback in `HttpConexusLlmClient` is dead code | P3 | `conexus` never emits `text` field |

---

## Missing Tests

### Tests that should exist now (adaptation side)

| Test | Priority |
|------|----------|
| `HttpConexusGatewayRegistrationClient` (once built): success, 401, 503, 404, timeout, non-2xx — response body not in exception | P0 |
| `HttpConexusGatewayRegistrationClient`: duplicate call (same `adapterProfileId`) → second call returns same `gatewayProfileId` without creating a new row | P1 |
| Real HTTP canary notify: `POST /internal/.../{id}/activate-canary` success → adaptation status matches | P1 |
| Real HTTP promote notify: success → gateway status `Active` | P1 |
| Real HTTP rollback notify: 409 (no previous) handled gracefully | P1 |
| `HttpAdaptationObservabilityClient` (once built): success, 404, timeout | P1 |
| Drift threshold calibrated against real `ObservabilityResponse` fields (not stub dict keys) | P1 |
| `HttpConexusLlmClient`: `conexus` does NOT return `cost` field → null `EstimatedCost`, no exception | P2 |
| `HttpConexusLlmClient`: valid unknown model alias → 400 surfaced correctly | P1 |

### Tests that should exist now (conexus side)

| Test | Priority |
|------|----------|
| `POST /internal/adapter-profiles/register` → idempotent on second call with same `adapterProfileId` | ✅ Already exists (`test_register_adapter_profile_is_idempotent_by_adapterProfileId`) |
| `POST /internal/adapter-profiles/register` → 401 without key | ✅ Already exists |
| `POST /internal/adapter-profiles/register` → 503 when key not configured | ✅ Already exists |
| `POST /internal/adapter-profiles/register` → 404 when registry disabled | ✅ Already exists |
| Full canary → promote → rollback sequence | Verify coverage in `test_internal_adapter_profile_activations.py` |
| Rollback with no previous → 409 | Verify coverage |
| Observability: empty window → `requestCount=0`, no null dereference | Verify coverage in `test_internal_adapter_profile_observability.py` |
| Observability: `since > until` → 400 | Verify coverage |
| `GET /internal/domains/{domainKey}/active-profile` → 404 when no active profile | Verify coverage |

### Cross-repo contract tests (not yet possible; require real HTTP clients)

| Test | Priority |
|------|----------|
| Round-trip: adaptation publishes → `conexus` DB has `GatewayAdapterProfile` row → adaptation stores `GatewayProfileId` | P0 |
| Round-trip: adaptation activates canary → `conexus` DB has `Canary` activation row | P1 |
| Round-trip: adaptation promotes → `conexus` DB has `Active` activation row | P1 |
| Round-trip: adaptation triggers drift check → receives real `ObservabilityResponse` | P1 |
| Failure mode: `conexus` returns 502 during publish → adaptation profile stays in `Approved`, no partial state | P1 |

---

## Demo Readiness Checklist

### Must resolve before demo

- [ ] **State clearly** in the demo script: the gateway integration is stub-only. Profiles are stored in the adaptation DB. `conexus` gateway DB does not have these profiles. "Registered in Conexus" is not a true claim until `HttpConexusGatewayRegistrationClient` is built.
- [ ] **Verify model profile name alignment:** Confirm `Conexus:DefaultModelProfile` values match valid aliases in `conexus` (`conexus-fast`, `conexus-default`, etc.). A mismatch returns 400.
- [ ] **`INTERNAL_ADAPTER_API_KEY`:** Ensure the demo environment has this set in `conexus` and `GatewayRegistration:ApiKey` set in `conexus.adaptation`. Without both, any future real registration call fails immediately.

### Should document before demo

- [ ] Document that `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED=false` — registering a canary profile does not split traffic yet.
- [ ] Document required env vars for a working local-dev demo (see Operational Model section).
- [ ] Document the dual-state gap: adaptation DB and gateway DB are not synchronized for canary/promote/rollback.

### Can safely wait

- [ ] `HttpConexusGatewayRegistrationClient` implementation.
- [ ] Canary/promote/rollback HTTP notify clients in adaptation.
- [ ] `HttpAdaptationObservabilityClient` implementation.
- [ ] `IAdaptationObservabilityClient` interface redesign (add `gatewayProfileId`, `since`/`until`).
- [ ] `estimated_cost` field in `/v1/chat/completions` response.
- [ ] `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED` routing logic.
- [ ] mTLS or signed service tokens for internal auth.
- [ ] `INTERNAL_ADAPTER_API_KEY` rotation runbook.

### Could embarrass us in a demo if ignored

- Claiming profiles are "live in the gateway" when `DeterministicGatewayRegistrationClient` is active.
- `EstimatedCost` always null in evaluation results.
- Running without `Conexus:BaseUrl` / `Conexus:ApiKey` — all LLM steps silently fall back to the fake client.
- Any test or UI metric showing `citation_accuracy=1.0` (hardcoded stub value) without a disclaimer.

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
| `INTERNAL_ADAPTER_API_KEY` | Yes (for internal endpoints) | Shared secret for `X-Internal-Api-Key` auth; must be non-empty, not `"change-me"`, ≥ 16 chars in prod |
| `ADAPTER_PROFILE_REGISTRY_ENABLED` | No | Default: `true`. Set `false` to disable all `/internal/*` endpoints (returns 404). |
| `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED` | No | Default: `false`. No routing logic reads this flag yet. |
| `ADAPTER_PROFILE_OBSERVABILITY_ENABLED` | No | Default: `true`. Set `false` to disable observability endpoint (returns 404). |

### Required env vars — `conexus.adaptation` (.NET)

| Variable | Required | Description |
|----------|----------|-------------|
| `ConnectionStrings:Adaptation` | Yes | SQLite (dev) or PostgreSQL (prod) |
| `Conexus:BaseUrl` | Yes (HTTP mode) | e.g., `http://localhost:8000` |
| `Conexus:ApiKey` | Yes (HTTP mode) | Project API key issued by `conexus` (`cx_live_*`) |
| `Conexus:TimeoutSeconds` | No | Default: 30; clamped 1–300 |
| `Conexus:DefaultModelProfile` | No | Default model alias (must be a valid `conexus` alias) |
| `GatewayRegistration:BaseUrl` | Yes (when real) | Not needed while `DeterministicGatewayRegistrationClient` is active |
| `GatewayRegistration:ApiKey` | Yes (when real) | Must match `INTERNAL_ADAPTER_API_KEY` in `conexus` |
| `GatewayRegistration:Enabled` | No | Default: true |
| `Corpus:BasePath` | Yes | Local corpus directory |

### Deployment order

1. Start PostgreSQL (or confirm connection).
2. Start `conexus` backend. Wait for `GET /health/ready` → 200.
3. Create a project and issue an API key in the `conexus` BO (or via admin API).
4. Set `Conexus:ApiKey` in `conexus.adaptation` config.
5. Set `GatewayRegistration:ApiKey` = value of `INTERNAL_ADAPTER_API_KEY` in `conexus.adaptation` config (for future real registration).
6. Start `conexus.adaptation`. EF migrations run on startup (dev default).

### Failure modes

| Failure | Impact on `conexus` | Impact on `conexus.adaptation` |
|---------|---------------------|-------------------------------|
| `conexus` is down | — | LLM evaluation steps fail with `CONEXUS_HTTP_ERROR` or `CONEXUS_TIMEOUT`. Runs cannot complete. Workers retry with jitter. No data loss. |
| `conexus.adaptation` is down | `conexus` serves LLM requests normally. No dependency. | — |
| `INTERNAL_ADAPTER_API_KEY` missing/wrong | All `/internal/*` return 503 (unconfigured) or 401 (wrong key) | Gateway registration, when real, will fail immediately. Profile stays in `Approved`. |
| `ADAPTER_PROFILE_REGISTRY_ENABLED=false` | All `/internal/*` return 404 | Real registration client will receive 404; must treat as registration failure, not wrong URL. |
| SQLite locked (adaptation) | — | Concurrent worker writes serialized. Multi-replica unsupported. |

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
| Observability | `DeterministicAdaptationObservabilityClient` (stub, hardcoded) | Real `HttpAdaptationObservabilityClient` (not yet built) |
| Canary routing | Not active (`ADAPTER_PROFILE_CANARY_ROUTING_ENABLED=false`) | Requires routing logic + flag enable |
| Admin auth | Env-based (`ADMIN_USERNAME`/`ADMIN_PASSWORD`) | DB-backed admin users recommended |
| CORS | Wildcard allowed | Strict `CORS_ALLOWED_ORIGINS` required |

---

## Contract Tests — Proposed

### Group 1: `conexus` — LLM endpoint contracts (testable today)

1. `POST /v1/chat/completions` with valid Bearer key and known alias → 200, `choices[0].message.content` present, `usage.prompt_tokens` and `usage.completion_tokens` non-zero.
2. `POST /v1/chat/completions` with unknown model → 400.
3. `POST /v1/chat/completions` with revoked API key → 401.
4. `POST /v1/chat/completions` with project over hard cost limit → 429, body includes `limit_type`, `reset_at`.
5. Response does NOT include `cost` field → confirm `conexus.adaptation` parses correctly (null `EstimatedCost`, no exception).

### Group 2: `conexus` — internal endpoint contracts (testable today, mostly covered)

6. `POST /internal/adapter-profiles/register` → 401 without `X-Internal-Api-Key`.
7. `POST /internal/adapter-profiles/register` → 503 when `INTERNAL_ADAPTER_API_KEY` not set.
8. `POST /internal/adapter-profiles/register` → 404 when `ADAPTER_PROFILE_REGISTRY_ENABLED=false`.
9. `POST /internal/adapter-profiles/register` idempotent by `adapterProfileId` → same `gatewayProfileId` on repeat.
10. Full sequence: register → activate-canary → promote → `GET /internal/domains/{key}/active-profile` → correct `gatewayProfileId`.
11. Register → activate-canary → rollback → 409 (no previous profile to restore).
12. `GET /internal/adapter-profiles/{id}/observability` with `since > until` → 400.
13. `GET /internal/adapter-profiles/{id}/observability` when `ADAPTER_PROFILE_OBSERVABILITY_ENABLED=false` → 404.

### Group 3: `conexus.adaptation` — LLM client contracts (testable today)

14. `HttpConexusLlmClient` with valid config → `Answer` non-empty, `PromptTokens` > 0.
15. `HttpConexusLlmClient` with non-2xx (mock 429) → error code `CONEXUS_NON_2XX`, response body absent from exception message.
16. `HttpConexusLlmClient` with send timeout → `CONEXUS_TIMEOUT`.
17. `HttpConexusLlmClient` with malformed JSON → `CONEXUS_MALFORMED_RESPONSE`.

### Group 4: Adapter profile lifecycle in adaptation (testable today, self-contained)

18. Publish → `WasDuplicate: false` on first call, `WasDuplicate: true` on idempotent repeat.
19. Publish → ActivateCanary → `Status == Canary`, `CanaryPercent` in [1, 50].
20. Publish → ActivateCanary → Promote → `Status == Promoted`.
21. Publish → ActivateCanary → Rollback → `Status == RolledBack`, `RolledBackAt` set.
22. ActivateCanary with `canaryPercent > 50` → 422.
23. Promote without prior ActivateCanary → 409 (state conflict).
24. 403 if caller roles insufficient.

### Group 5: Cross-repo contract tests (require real HTTP clients — not yet possible)

25. Round-trip: adaptation publish → `conexus` `gateway_adapter_profiles` row exists → adaptation stores returned `gatewayProfileId`.
26. Round-trip: adaptation canary activate → `conexus` `gateway_adapter_profile_activations` has `Canary` row.
27. Round-trip: adaptation promote → `conexus` activation `status == "Active"`.
28. Round-trip: observability pull → real `requestCount`, `errorRate`, `latencyP95Ms` returned.
29. Failure: `conexus` returns 502 during publish → adaptation profile stays in `Approved`; no partial gateway state.
30. Failure: rollback when no previous profile → `conexus` 409 → adaptation handles gracefully.

### Cross-repo fixture JSON examples

**Profile registration request (actual `conexus` endpoint shape):**
```json
{
  "adapterProfileId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "domainKey": "gaming-crm",
  "runId": "run-abc123",
  "planId": "plan-xyz",
  "compositeScore": 0.87,
  "evidenceHash": "sha256:evh...",
  "semanticContextHash": "sha256:sch...",
  "slodModelVersion": "v1",
  "profileVersion": "1.0.0"
}
```

**Profile registration response (actual `conexus` endpoint shape):**
```json
{
  "gatewayProfileId": "gw-a1b2c3d4e5f6...",
  "status": "Registered"
}
```

**Observability response (actual `conexus` endpoint shape):**
```json
{
  "gatewayProfileId": "gw-a1b2c3d4e5f6...",
  "windowStart": "2026-04-29T12:00:00+00:00",
  "windowEnd": "2026-04-30T12:00:00+00:00",
  "requestCount": 142,
  "errorRate": 0.014,
  "latencyP95Ms": 380,
  "costPerAnswer": 0.0009,
  "citationFailureRate": null,
  "refusalRate": null,
  "userNegativeFeedbackRate": null
}
```

---

## Owner Decisions Required

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Build `HttpConexusGatewayRegistrationClient` now or keep stub for demo? | A) Stub for demo; real in v0.4. B) Build minimal real client now. | **A** — stub is safe for demo; infrastructure is ready on `conexus` side |
| 2 | Redesign `IAdaptationObservabilityClient` interface before or after building the HTTP client? | A) Add `gatewayProfileId` + window params to the interface now, then build client. B) Build client with an adapter that takes `AdapterProfile` and extracts `GatewayProfileId`. | **A** — interface change is small; avoids a two-level wrapper |
| 3 | `INTERNAL_ADAPTER_API_KEY` rotation process | Document who issues the key, where it is stored, and what the rotation runbook is. | Required before any production deploy |
| 4 | Should `conexus` return `estimated_cost` in `/v1/chat/completions` response? | A) Yes, add to response DTO. B) No, adaptation maintains its own cost table. | **A** — avoids null `EstimatedCost` in evaluations |
| 5 | DB for `conexus.adaptation` in production | A) Stay on SQLite. B) Migrate to PostgreSQL. | **B** — required before multi-replica deployment |
| 6 | `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED`: when to implement the actual routing logic? | Deferred to v0.5; flag exists but is inert. | Do not enable flag until routing logic is written. |

---

## 30 / 60 / 90 Minute Cleanup Plan

### 30 minutes (demo-blocking)

1. Verify that `Conexus:DefaultModelProfile` values are valid `conexus` model aliases — check `gateway_router.py` alias table against `conexus.adaptation` config.
2. Add one sentence to `conexus.adaptation/README.md`: "Gateway registration uses `DeterministicGatewayRegistrationClient` (stub). Profiles are stored in the adaptation DB only; the `conexus` gateway DB is not populated until `HttpConexusGatewayRegistrationClient` is built."
3. Add one sentence to `conexus/docs/04_GATEWAY.md` or `README.md`: "`ADAPTER_PROFILE_CANARY_ROUTING_ENABLED` defaults to `false`; canary routing logic is not yet implemented."

### 60 minutes (should do before demo)

4. Verify test coverage for Group 2 items 10–13 in `test_internal_adapter_profile_activations.py` and `test_internal_adapter_profile_observability.py`.
5. Add Group 1 items 1–4 as explicit contract tests in the `conexus` test suite if not already present.
6. Document `INTERNAL_ADAPTER_API_KEY` issuance in `conexus/docs/07_DATABASE_AUTH.md`.

### 90 minutes (quality of life)

7. Redesign `IAdaptationObservabilityClient` to accept `string gatewayProfileId` and optional window params (Owner Decision 2).
8. Add `estimated_cost` to `conexus` `/v1/chat/completions` response DTO.
9. Document Owner Decisions 1–3 as an ADR in `conexus/docs/ADRs/`.

---

## Longer-Term Production Hardening Roadmap

| Phase | Work | Dependency |
|-------|------|------------|
| v0.4 | Build `HttpConexusGatewayRegistrationClient` in `conexus.adaptation` | Owner Decision 1 |
| v0.4 | Build canary/promote/rollback HTTP notify clients in `conexus.adaptation` | Registration client stable |
| v0.4 | Redesign `IAdaptationObservabilityClient` interface; build `HttpAdaptationObservabilityClient` | Owner Decision 2 |
| v0.4 | Add `estimated_cost` to `/v1/chat/completions` response | Owner Decision 4 |
| v0.4 | Document `INTERNAL_ADAPTER_API_KEY` rotation runbook | Owner Decision 3 |
| v0.5 | Implement canary routing logic in `conexus` and enable `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED` | Owner Decision 6; registration + notify clients stable |
| v0.5 | Migrate `conexus.adaptation` to PostgreSQL | Owner Decision 5 |
| v0.6 | Cross-repo contract test suite in CI | Real HTTP clients stable |
| v0.6 | mTLS or signed service tokens for internal auth | Infrastructure ready |
| v1.0 | Network isolation: `/internal/*` on separate port or private subnet | Infrastructure ready |
