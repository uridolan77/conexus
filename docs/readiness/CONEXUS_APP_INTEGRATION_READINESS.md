# Conexus App Integration Readiness

**Assessment date:** 2026-05-11  
**Evidence:** repository inspection (`backend/app`, `frontend`, `contracts/`, tests) and reconciliation with `docs/_incoming/conexus-v1-contracts-work-package.zip` (extracted locally; path is gitignored).

## Executive Summary

**Status: PARTIALLY READY**

Conexus is a real FastAPI + Next.js back office with Postgres, admin auth, projects and project API keys, provider configuration, gateway request logging, and **`POST /v1/chat/completions`** with Anthropic/OpenAI routing behind a gateway provider. Docker Compose brings the stack up locally.

It is **not** yet a complete match for the idealized multi-endpoint contract in the original work package. In particular, there is **no** public `GET /v1/models`, **`POST /v1/route`**, **`POST /v1/embeddings`**, or **`GET /v1/usage/{trace_id}` / `GET /v1/traces/{trace_id}`**. Chat is **OpenAI-shaped** (with Conexus extensions such as `provider` and `fallback_used` on responses), not the work-package’s alternate JSON that embedded `caller`, `route`, and `trace_id` fields.

**Bottom line:** Agentor and Athanor can integrate for **non-streaming or streaming text chat** today if they accept OpenAI-compatible request/response shapes, project bearer auth, and correlation via **`X-Conexus-Request-Id`** rather than a public trace or usage retrieval API. Anything that **requires embeddings, route preview, or caller-scoped usage/trace HTTP APIs** remains blocked until those endpoints exist.

## Current Confirmed Capabilities

| Area | Evidence |
| --- | --- |
| **Health** | `GET /health` returns `status`, `service`, `version` — `backend/app/api/health.py`, `backend/tests/test_health.py` |
| **Readiness** | `GET /readyz` and alias `GET /health/ready` — same file and tests |
| **Backend startup** | FastAPI app in `backend/app/main.py`; requires valid `ENCRYPTION_KEY` per README |
| **Docker / local stack** | `docker-compose.yml` — Postgres, backend, frontend |
| **Admin auth** | Cookie/session admin under `/admin/auth/*` |
| **Project API keys** | Gateway dependency `require_project_api_key` — `backend/app/api/auth.py` |
| **Provider configuration** | Admin provider routes; gateway uses configured provider stack |
| **`POST /v1/chat/completions`** | `backend/app/api/gateway.py` + `app/services/gateway_service.py`; extensive tests `backend/tests/test_gateway_endpoint.py` |
| **Streaming** | SSE path when `stream: true`; usage may be absent if provider omits usage chunk (test documents behavior) |
| **Tool calls / logprobs / n>1** | Rejected with explicit 400 codes in `_validate_compat` |
| **Model aliases** | Static YAML `backend/static_config/model_aliases.yaml`; validated at startup |
| **Provider routing / failover** | `app/llm/gateway_router.py` — Anthropic primary with OpenAI failover for configured models |
| **Request logs** | Persisted and visible in BO (`admin_requests` stack) |
| **Usage / cost capture** | Token usage in chat response when available; `usage_events` when complete usage exists; estimated cost on gateway rows where pricing applies |
| **Provider error capture** | Normalized gateway errors (`GatewayClientError`, `GatewayLimitError`, `GatewayUpstreamError`) with `X-Conexus-Request-Id` |
| **BO visibility** | Next.js BO for projects, keys, providers, requests, usage dashboards |
| **Internal adapter profile API** | `POST /internal/adapter-profiles/register`, `activate-canary`, `promote`, `rollback`, `GET .../observability`, `GET /internal/domains/{domainKey}/active-profile` when registry enabled — `internal_adapter_profiles.py`, `internal_domains.py` |
| **OpenAPI in repo** | `contracts/openapi/conexus.v1.yaml` (this PR) describes implemented routes; FastAPI still serves interactive docs at `/docs` |
| **Tests** | Pytest suite including gateway, health, usage, admin routes |

## Required Integration Contract (minimal stable subset)

This is what other apps should target **today**.

| Concern | Contract |
| --- | --- |
| **Base URL** | Deployed Conexus API origin (e.g. `https://api.example.com` or `http://localhost:8000` locally). |
| **Auth** | `Authorization: Bearer <project_api_key>` for `POST /v1/chat/completions`. |
| **Optional headers** | `X-Conexus-Domain-Key`, `X-Conexus-Gateway-Profile-Id` (or legacy `X-Conexus-Adapter-Profile-Id`) for adapter-profile routing context. Optional **`X-Conexus-Request-Id`**: when sent and valid (`1–64` chars from `[A-Za-z0-9_-]`), Conexus uses it as the gateway `request_id` (must be unique per new request); when omitted, Conexus generates a UUID-like id. |
| **Chat request body** | OpenAI-compatible subset: `model`, `messages[]` with `role` in `system|user|assistant`, `content`, optional `max_tokens`, `temperature`, `stream`, plus ignored/extra fields per `ChatCompletionsRequest` schema. |
| **Chat response body (JSON)** | `id`, `object`=`chat.completion`, `created` (unix int), `model`, `provider`, `fallback_used`, **`request_id`** (same as `X-Conexus-Request-Id`), `choices[]`, `usage` with `prompt_tokens`, `completion_tokens`, `total_tokens`. |
| **Correlation** | Response header **`X-Conexus-Request-Id`**; JSON **`request_id`**; `id` uses `chatcmpl-{request_id}`. Callers may supply their own id via the request header when it is unique. |
| **Errors** | Often `{"detail": {"code", "message", "request_id", ...}}` for gateway domain errors; reused caller `X-Conexus-Request-Id` returns **409** `request_id_conflict`. `POST /v1/chat/completions` **422** responses include `X-Conexus-Request-Id` (generated) when body validation fails. |
| **Model alias behavior** | Request `model` may be a configured alias key (see `model_aliases.yaml`) or a concrete provider model id with known prefixes. |
| **Timeouts / retries** | Clients should use conservative HTTP timeouts and **retry only on idempotent reads** or application-level idempotency keys (not yet first-class on gateway). Streaming retries are inherently lossy. |

## Gap Analysis

| Area | Current status | Required for other apps | Gap | Priority |
| --- | --- | --- | --- | --- |
| OpenAPI contract | Checked-in `conexus.v1.yaml` aligned to implementation | Accurate contract in repo | ~~Missing file~~ **Done**; must be kept updated | P0 |
| .NET client | Minimal `src/dotnet/Conexus.Client` (health + chat) | Typed client without provider SDKs | No embeddings/route/usage/trace methods | P1 |
| Chat completion | Implemented + tested | Stable OpenAI subset | Tools/logprobs unsupported | P1 (feature) |
| Embeddings | **Not implemented** | Many Athanor flows | No `POST /v1/embeddings` | P0 for embedding consumers |
| Route preview | **Not implemented** | Pre-flight routing visibility | No `POST /v1/route` | P2 |
| Model aliases | YAML + router | Stable alias names | No `GET /v1/models` catalog | P1 |
| Trace IDs | `X-Conexus-Request-Id` + body `request_id` + BO logs | Portable trace document | No `trace_id` body field; no `GET /v1/traces/...` | P1 |
| Usage lookup | Admin + DB | Caller-facing `GET /v1/usage/...` | Not implemented for project keys | P1 |
| Request logs | BO + DB | Ops | No public API (by design today) | P2 |
| Cost estimation | Partial via gateway + pricing | Budgeting | Not exposed as standalone public API | P2 |
| Error normalization | Good for gateway domain errors; 422 on chat includes `X-Conexus-Request-Id` header | Uniform across all errors | `422` body remains FastAPI `detail` list shape | P2 |
| Auth / project keys | Implemented | Multi-tenant isolation | OK | — |
| Internal service key | Implemented for `/internal/...` | adaptation services | OK when enabled | — |
| BO visibility | Implemented | Operators | OK | — |
| Contract tests | YAML/JSON parse + schema validation | CI gate | Lightweight tests added | P1 |
| Smoke tests | Docker + curl in docs | CI | Optional hardening | P2 |
| Deployment readiness | Documented | prod checklist | Operators must run Alembic, secrets | P1 process |

## Agentor Readiness

| Capability | Today |
| --- | --- |
| Call chat completions | **Yes** with project API key and OpenAI-compatible payload. |
| Model aliases | **Yes** within configured YAML aliases and concrete ids. |
| Stable error shape | **Partially** — gateway errors are structured; validation errors differ. |
| Trace IDs | **Yes** — use `X-Conexus-Request-Id`, JSON `request_id`, and `id`; optional caller-owned ids when unique. Not the work-package `trace_id` JSON field. |
| Retrieve usage via HTTP | **No** public usage-by-id API. |
| Streaming | **Yes**, SSE; client must parse stream; usage may be missing on some streams. |
| Tool calls | **No** — rejected with `tool_calls_not_supported`. |
| Embeddings | **No**. |
| Retries | **Client responsibility** — no idempotency key in API. |

**Verdict:** **Usable with wrapper** for text chat agents that do not require tools or embeddings and that can tolerate correlation via `X-Conexus-Request-Id` instead of a trace document API.

## Athanor Readiness

| Capability | Today |
| --- | --- |
| Canonicalization via chat | **Possible** only as plain LLM text extraction; no structured pipeline contract in Conexus itself. |
| Entity/claim/provenance extraction | **Out of scope** for Conexus; must live in Athanor unless Conexus adds extraction APIs (it does not). |
| Embeddings | **Blocked** — no embeddings endpoint. |
| Deterministic traceability | **Partial** — strong DB logging and BO, weak public trace retrieval API. |
| Usage/cost lookup | **Admin-side**; not project-key HTTP retrieval. |
| Stable response schemas | **Good** for implemented chat JSON; streaming is OpenAI-like chunks. |

**Verdict:** **Blocked** for embedding-heavy or trace-API-dependent designs; **partial** for chat-only extraction prototypes.

## .NET Client Readiness

A minimal client was added at:

- `src/dotnet/Conexus.Client`

It targets **only** implemented routes (`GET /health`, optional `GET /readyz`, `POST /v1/chat/completions`) and uses **snake_case** JSON to match FastAPI/Pydantic responses.

**Stability:** adequate for internal pilots **not** for semver-stable public distribution until embeddings/tools/trace APIs stabilize and the client gains coverage.

## Readiness Score (0–10)

| Area | Score | Notes |
| --- | ---: | --- |
| Local runtime | 8 | Compose + migrations story documented |
| Public gateway API | 6 | Chat strong; several public endpoints missing |
| Provider routing | 7 | Real failover; config is file-driven |
| Auth / project isolation | 8 | Keys + admin separation |
| Observability / logging | 6 | BO strong; public trace API missing |
| Usage / cost accounting | 6 | DB + admin; caller HTTP API missing |
| OpenAPI / contract stability | 7 | New file; discipline required to avoid drift |
| .NET client readiness | 6 | Minimal surface, no provider SDKs |
| Agentor readiness | 6 | Chat-only agents OK with wrapper |
| Athanor readiness | 4 | Embeddings + trace APIs are gating |
| Deployment readiness | 7 | Real checklist; prod discipline on secrets |

**Total:** 73 / 110 → **~66%** — appropriate for **controlled integration**, not blind reliance as a finished multi-tenant analytics and embedding platform.

## Must-Fix Before Other Apps Depend on It

### P0

1. **Embeddings:** implement `POST /v1/embeddings` (or explicitly document that Athanor must not depend on Conexus for embeddings) before claiming Athanor readiness.
2. **Contract discipline:** treat `contracts/openapi/conexus.v1.yaml` as authoritative for cross-repo work; block merges that drift OpenAPI from code without an intentional version bump.
3. **Clarify correlation contract:** callers should prefer **`X-Conexus-Request-Id`** (optional) + response **`request_id`** for cross-system correlation; a separate `trace_id` JSON field is not implemented.

### P1

1. **`GET /v1/models` (or equivalent)** so .NET clients can discover aliases without reading repo YAML.
2. **Public usage retrieval** (or signed webhook export) if Agentor needs per-call accounting without BO access.
3. **Tool calls** if Agentor requires function-calling through Conexus.

## Recommended Next PRs

- **PR-A (contract adoption):** `contracts/**` + OpenAPI alignment + JSON schemas + `.gitignore` for extracted incoming folder.
- **PR-B (readiness report):** this file + architecture index + ADRs.
- **PR-C (route / trace / usage alignment):** implement or explicitly defer `POST /v1/route`, `GET /v1/traces/{id}`, `GET /v1/usage/{id}` with versioned OpenAPI; unify naming (`trace_id` vs `request_id`).
- **PR-D (.NET client):** expand `Conexus.Client` with any new public endpoints; add CI `dotnet build`.
- **PR-E (Agentor smoke test):** scripted chat call against docker-compose using a fixture project key.
- **PR-F (Athanor smoke test):** blocked on embeddings/trace until PR-C; stub chat-only smoke if useful.

---

## Implementation note (for reviewers)

**Already in repo before this work:** FastAPI app, gateway chat, health/ready, internal adapter routes, BO, Postgres models, usage service, gateway router, extensive pytest coverage, existing long-form `docs/specs/provider-abstraction.md` and `docs/architecture/architecture-principles.md`.

**Added or reconciled here:** `contracts/openapi/conexus.v1.yaml`; JSON schemas (implemented + forward-looking); `contracts/routing/default-policy.json`; examples; `docs/adr/*`; `docs/architecture/{README,runtime-boundary,routing-policy,observability-and-cost,provider-abstraction}.md`; readiness report; minimal `src/dotnet/Conexus.Client`; `backend/tests/test_contract_assets.py`; README pointer; gitignore for extracted zip folder.

**Intentionally not adopted:** work-package Python skeleton app, GitHub workflow from package, idealized chat DTOs (`caller`, `route` in body), and the original .NET DTOs that targeted non-existent HTTP shapes. Forward-looking JSON schemas are retained under `contracts/json-schema/` with `x-contract-status: not-implemented` where applicable.
