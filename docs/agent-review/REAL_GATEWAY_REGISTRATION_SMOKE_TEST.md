# Real Gateway Registration — Local Smoke-Test Guide

**Date:** 2026-04-30  
**Scope:** End-to-end verification that `conexus.adaptation` (HTTP mode) writes a real row to the `conexus` `gateway_adapter_profiles` table and stores the returned `gatewayProfileId` in the adaptation DB.

---

## What this verifies

- `HttpConexusGatewayRegistrationClient` calls `POST /internal/adapter-profiles/register`.
- Conexus creates a `gateway_adapter_profiles` row and returns `gatewayProfileId`.
- `conexus.adaptation` stores that ID in `adapter_profiles.gateway_profile_id`.
- Idempotency: a second publish call for the same `adapterProfileId` returns the same `gatewayProfileId` without a new row.

---

## Prerequisites

- Docker (for PostgreSQL) or a running PostgreSQL instance.
- Python 3.11+ with `conexus` deps installed (`pip install -r requirements.txt`).
- .NET 8 SDK with `conexus.adaptation` dependencies restored.
- `psql` or any PostgreSQL client (for DB verification).
- `curl` or HTTPie for API calls.

---

## Step 1 — Exact env vars

### `conexus` (FastAPI)

```env
# Required for all operations
DATABASE_URL=postgresql+asyncpg://conexus:conexus@localhost:5432/conexus
ENCRYPTION_KEY=<32-byte Fernet key, e.g. from: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
AUTH_SECRET=<random ≥32 chars>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=localdev

# Internal adapter profile registry — MUST be set and non-empty for registration to succeed
INTERNAL_ADAPTER_API_KEY=localdev-internal-key-change-before-prod

# Feature flags (defaults shown; no need to set unless overriding)
ADAPTER_PROFILE_REGISTRY_ENABLED=true
ADAPTER_PROFILE_CANARY_ROUTING_ENABLED=false
ADAPTER_PROFILE_OBSERVABILITY_ENABLED=true

# LLM provider (required to issue a project API key for adaptation)
# Use one of:
OPENAI_API_KEY=<your key>
# or
ANTHROPIC_API_KEY=<your key>
```

### `conexus.adaptation` (.NET)

```env
# Database
ConnectionStrings__Adaptation=Data Source=adaptation.db

# LLM calls
Conexus__BaseUrl=http://localhost:8000
Conexus__ApiKey=<project API key issued in Step 3>
Conexus__DefaultModelProfile=conexus-fast

# === Gateway registration in HTTP mode ===
GatewayRegistration__Mode=http
GatewayRegistration__BaseUrl=http://localhost:8000
GatewayRegistration__ApiKey=localdev-internal-key-change-before-prod
GatewayRegistration__Actor=conexus-adaptation-local
GatewayRegistration__TimeoutSeconds=30

# Corpus
Corpus__BasePath=<path to local corpus directory>
```

> **Key constraint:** `GatewayRegistration__ApiKey` must equal `INTERNAL_ADAPTER_API_KEY` exactly (byte-for-byte, HMAC-compared).

---

## Step 2 — Startup order

### 2a. Start PostgreSQL

```bash
docker run -d \
  --name conexus-pg \
  -e POSTGRES_USER=conexus \
  -e POSTGRES_PASSWORD=conexus \
  -e POSTGRES_DB=conexus \
  -p 5432:5432 \
  postgres:15
```

Wait ~5 seconds for PostgreSQL to be ready.

### 2b. Start `conexus`

From `conexus/` root:

```bash
# Export env vars (or use .env file with python-dotenv)
export DATABASE_URL="postgresql+asyncpg://conexus:conexus@localhost:5432/conexus"
export ENCRYPTION_KEY="<generated Fernet key>"
export AUTH_SECRET="localdev-auth-secret-32-chars-min"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="localdev"
export INTERNAL_ADAPTER_API_KEY="localdev-internal-key-change-before-prod"
export ADAPTER_PROFILE_REGISTRY_ENABLED="true"

# Run migrations then start server
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify ready:

```bash
curl http://localhost:8000/health/ready
# Expected: {"status":"ok"} or similar 200 response
```

### 2c. Start `conexus.adaptation`

From `conexus.adaptation/` root:

```bash
export GatewayRegistration__Mode="http"
export GatewayRegistration__BaseUrl="http://localhost:8000"
export GatewayRegistration__ApiKey="localdev-internal-key-change-before-prod"
export GatewayRegistration__Actor="conexus-adaptation-local"
export Conexus__BaseUrl="http://localhost:8000"
export Conexus__ApiKey="<see Step 3>"

dotnet run --project src/Conexus.Adaptation.Api
```

EF migrations apply on startup in dev mode.

---

## Step 3 — Issue a project API key in `conexus`

Before starting adaptation, you need a `cx_live_*` project key. Do this via the admin BO or directly:

```bash
# 1. Get an admin session token
curl -s -X POST http://localhost:8000/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"localdev"}' \
  | jq -r '.token'
# → <ADMIN_TOKEN>

# 2. Create a project
curl -s -X POST http://localhost:8000/admin/projects \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"local-adaptation-test","hard_limit_usd":10}' \
  | jq -r '.id'
# → <PROJECT_ID>

# 3. Issue an API key for the project
curl -s -X POST http://localhost:8000/admin/projects/<PROJECT_ID>/keys \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"label":"local-dev"}' \
  | jq -r '.key'
# → cx_live_<...>
```

Set `Conexus__ApiKey=cx_live_<...>` and (re)start `conexus.adaptation`.

---

## Step 4 — API call sequence

These calls exercise the full publish path. Use your `conexus.adaptation` API (default: `http://localhost:5000`).

> **Note:** Creating a plan, approving it, and running an evaluation are prerequisites for having a publishable adapter profile. The exact sequence below assumes you have already completed an evaluation run and have an approved adapter profile ID ready. Check the adaptation API docs or BO for the complete plan → run → evaluate → publish flow.

### 4a. Publish an adapter profile (triggers real registration)

```bash
PROFILE_ID=<adapter profile GUID from evaluation run>
IDEMPOTENCY_KEY=$(uuidgen)

curl -s -X POST http://localhost:5000/api/adapter-profiles/${PROFILE_ID}/publish \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -d '{"publishedByUserId":"local-admin","roles":["AdaptationPublisher"]}' \
  | jq .
```

**Expected response (first call):**

```json
{
  "profileId": "<PROFILE_ID>",
  "status": "Published",
  "gatewayProfileId": "gw-<32 hex chars>",
  "wasDuplicate": false
}
```

**Expected response (second call, same idempotency key):**

```json
{
  "profileId": "<PROFILE_ID>",
  "status": "Published",
  "gatewayProfileId": "gw-<same 32 hex chars>",
  "wasDuplicate": true
}
```

### 4b. Verify via direct gateway call (optional)

```bash
# Confirm the internal endpoint received the call
# (you can also check the conexus audit log table)
curl -s -X POST http://localhost:8000/internal/adapter-profiles/register \
  -H "X-Internal-Api-Key: localdev-internal-key-change-before-prod" \
  -H "Content-Type: application/json" \
  -d "{\"adapterProfileId\":\"${PROFILE_ID}\",\"domainKey\":\"<domain key>\"}" \
  | jq .
# Expected: {"gatewayProfileId":"gw-<...>","status":"Registered"}
# (Idempotent: returns the existing row if already registered)
```

---

## Step 5 — Verify the Conexus DB row

Connect to PostgreSQL and check:

```bash
psql "postgresql://conexus:conexus@localhost:5432/conexus"
```

```sql
-- Check the registered adapter profile row
SELECT
    id,
    gateway_profile_id,
    adapter_profile_id,
    domain_key,
    profile_version,
    status,
    source_run_id,
    source_plan_id,
    composite_score,
    evidence_hash,
    semantic_context_hash,
    slod_model_version,
    created_at
FROM gateway_adapter_profiles
ORDER BY created_at DESC
LIMIT 5;
```

**Expected row:**

| Column | Expected value |
|--------|----------------|
| `gateway_profile_id` | `gw-<32 hex chars>` (e.g., `gw-a1b2c3d4e5f6...`) |
| `adapter_profile_id` | UUID matching `PROFILE_ID` from Step 4 (hyphenated lowercase) |
| `domain_key` | The domain key of the adaptation plan |
| `profile_version` | `"v0.3j"` (the evidence projection schema version — see note below) |
| `status` | `"Registered"` |
| `composite_score` | A float between 0 and 1 |
| `evidence_hash` | A non-empty hash string |

```sql
-- Check the audit log entry
SELECT actor, action, resource_type, resource_id, metadata_json, created_at
FROM admin_audit_log
WHERE action = 'gateway.adapter_profile.registered'
ORDER BY created_at DESC
LIMIT 3;
```

**Expected:** A row with `action = 'gateway.adapter_profile.registered'` and `metadata_json` containing `adapter_profile_id` and `domain_key`.

---

## Step 6 — Verify the adaptation DB stores the real `GatewayProfileId`

Connect to the adaptation SQLite DB:

```bash
sqlite3 adaptation.db
```

```sql
SELECT
    id,
    domain_key,
    status,
    gateway_profile_id,
    published_at
FROM adapter_profiles
WHERE id = '<PROFILE_ID>'
LIMIT 1;
```

**Expected:**

| Column | Expected value |
|--------|----------------|
| `status` | `Published` |
| `gateway_profile_id` | `gw-<32 hex chars>` matching the `conexus` row from Step 5 |
| `published_at` | Non-null timestamp |

> **Cross-check:** `adapter_profiles.gateway_profile_id` must equal `gateway_adapter_profiles.gateway_profile_id` from Step 5. If they differ, the integration is not wiring up correctly.

---

## Known limitations at smoke-test time

| Limitation | Detail |
|------------|--------|
| Canary activation | Still stub — writes adaptation DB only; no HTTP call to `POST /internal/adapter-profiles/{id}/activate-canary` |
| Promote | Stub — adaptation DB only |
| Rollback | Stub — adaptation DB only |
| Observability | `DeterministicAdaptationObservabilityClient` — returns hardcoded metrics; no HTTP call to `GET /internal/adapter-profiles/{id}/observability` |
| Canary traffic routing | `ADAPTER_PROFILE_CANARY_ROUTING_ENABLED=false`; routing logic not yet implemented |
| `profileVersion` semantics | The registered `profile_version` is always `"v0.3j"` (the evidence projection schema version, not a business profile version) — see note in `CROSS_REPO_CONEXUS_INTEGRATION_REVIEW.md` |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `503` from `/internal/adapter-profiles/register` | `INTERNAL_ADAPTER_API_KEY` not set in conexus | Set env var and restart conexus |
| `401` from `/internal/adapter-profiles/register` | `GatewayRegistration__ApiKey` does not match `INTERNAL_ADAPTER_API_KEY` | Ensure exact byte-for-byte match |
| `404` from `/internal/adapter-profiles/register` | `ADAPTER_PROFILE_REGISTRY_ENABLED=false` | Set to `true` and restart |
| adaptation throws `InvalidOperationException` at startup | `GatewayRegistration__BaseUrl` or `GatewayRegistration__ApiKey` is empty while `Mode=http` | Set both config values |
| `ExternalServiceException: Gateway registration returned 400` | `adapterProfileId` or `domainKey` empty or whitespace-only | Check that the profile has a non-empty domain key set |
| `gateway_profile_id` in adaptation DB is `gw-<profile-guid-no-dashes>` | Still using `DeterministicGatewayRegistrationClient` | Confirm `GatewayRegistration__Mode=http` is set and restarted |
| Adaptation publish returns 200 but conexus DB row missing | `GatewayRegistration__Mode` not `"http"` (case-insensitive) | Check exact value; restart |
