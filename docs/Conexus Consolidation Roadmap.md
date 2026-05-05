Yes. Here is the consolidated comprehensive plan from both reviews.

Both assessments agree on the same big picture: **Conexus is architecturally strong, but it now needs a consolidation/hardening pass before more feature work.** The first review emphasizes production safety: single-process hard-limit locks, static admin fallback, pricing path/cache, and gateway duplication.  The second review adds sharper implementation targets: partial unique indexes for adapter-profile races, status enums, N+1 fixes, usage aggregation, error hierarchy cleanup, frontend filter duplication, and security-critical frontend helper verification. 

# Conexus Consolidation Roadmap

## Phase 0 — Freeze feature expansion and stabilize baseline

**Goal:** establish `main` as the working base and stop expanding Agentor until backend hardening is done.

Tasks:

```text
1. Work from latest main.
2. Run backend tests.
3. Run frontend tests/build.
4. Run agentor tests.
5. Add/confirm GitHub Actions for backend pytest, frontend tests/build, ruff, mypy.
6. Create docs/CONSOLIDATION_ROADMAP.md with this plan.
```

Acceptance:

```bash
cd backend && pytest
cd ../frontend && npm test && npm run build
cd ../agentor && pytest
```

Do not start broad refactors until this is green.

---

# Track A — Production safety first

## A1 — Adapter-profile Active/Canary race fix

**Priority:** highest
**Why:** fixes real TOCTOU race in canary activation/promotion.

Problem:

```text
internal_adapter_profiles.activate_canary and promote check for existing Active/Canary rows before insert/update.
Without DB uniqueness, two concurrent requests can create duplicate Active or Canary rows.
```

Implementation:

```text
1. Add Alembic migration with partial unique indexes:
   - unique Active activation per domain_key
   - unique Canary activation per domain_key

2. Update API/service logic:
   - catch IntegrityError
   - return clean 409 conflict
   - do not leak DB internals

3. Add tests:
   - cannot create two Active activations for same domain
   - cannot create two Canary activations for same domain
   - conflict returns 409, not 500
```

Code-agent prompt:

```text
Implement adapter-profile activation race hardening.

Scope:
- backend/app/api/internal_adapter_profiles.py
- backend/app/db/models.py if needed
- alembic migration
- backend/tests/*adapter_profile* tests

Tasks:
1. Add partial unique indexes enforcing one Active and one Canary activation per domain_key.
2. Convert IntegrityError into clean 409 conflict.
3. Add tests for duplicate Active/Canary prevention.
4. Do not refactor gateway_service.
5. Do not touch Agentor.
```

---

## A2 — Hard-limit reservation single-worker safety

**Priority:** critical production safety
**Why:** `_project_reserve_locks` is explicitly single-process only; multi-worker deployment silently weakens hard-limit guarantees.

Implementation:

```text
1. Add setting for worker/concurrency awareness if not present.
2. Detect WEB_CONCURRENCY or configured worker count.
3. If hard-limit reservations are enabled and worker count > 1:
   - fail startup, or
   - emit very loud startup error unless distributed lock enabled.
4. Document single-worker requirement in deployment docs.
5. Pin backend to one worker in docker-compose/Dockerfile until Redis/distributed lock exists.
```

Future version:

```text
Redis distributed lock per project_id
or serializable Postgres transaction strategy
```

Acceptance:

```text
WEB_CONCURRENCY=1 starts.
WEB_CONCURRENCY=2 with hard limits enabled fails or warns loudly according to chosen policy.
Tests cover both.
```

---

## A3 — Disable static admin fallback by default

**Priority:** critical security hardening
**Why:** static admin env credentials should not remain active after DB admin users exist.

Implementation:

```text
1. Add setting:
   enable_static_admin_fallback: bool = False

2. Login behavior:
   - DB admin auth is normal production path.
   - static admin login only works when explicitly enabled.
   - optionally allow static bootstrap only when no AdminUser rows exist.

3. Add tests:
   - static login disabled by default
   - static login works only when enabled
   - DB admin login still works
   - if DB users exist, static fallback does not silently bypass them
```

---

## A4 — Bound in-memory dictionaries

**Priority:** high
**Why:** small but real memory growth risks under churn/attack.

Targets:

```text
_project_reserve_locks: dict[str, asyncio.Lock]
AdminLoginRateLimiter._failures
```

Implementation options:

```text
1. LRU cap.
2. Periodic prune.
3. WeakValueDictionary for locks if safe.
4. Document accepted limit if intentionally kept.
```

Acceptance:

```text
Many unique project_ids/usernames do not grow memory unboundedly.
Tests simulate churn.
```

---

## A5 — Verify security-critical frontend/admin helpers

**Priority:** high
**Why:** second review explicitly could not inspect some security-critical frontend files.

Check these:

```text
frontend/lib/redaction.ts
frontend/lib/api.ts / adminSessionFetch
frontend/lib/admin/*
frontend/lib/types.ts
frontend/lib/adaptationApi.ts
frontend/lib/adaptationTypes.ts
```

Verify:

```text
1. adminSessionFetch includes credentials correctly.
2. 401 handling is safe and predictable.
3. redaction removes provider keys, bearer tokens, sk-* keys, internal keys, JWT-like values if possible.
4. redaction is tested.
5. no sensitive request/response body is displayed raw in BO drawers.
```

Acceptance:

```text
frontend tests cover redaction and admin fetch behavior.
```

---

# Track B — Correctness and data integrity

## B1 — Consolidate error hierarchy

**Priority:** high
**Problem:** there are gateway-local errors and `core.errors`; the review calls this a structural smell.

Decision required:

```text
Option A: Gateway errors inherit from ConexusDomainError.
Option B: Remove unused core.errors.
```

Recommended:

```text
Use ConexusDomainError everywhere.
```

Tasks:

```text
1. Make GatewayClientError / GatewayLimitError / GatewayUpstreamError inherit from ConexusDomainError.
2. Add global FastAPI exception handler.
3. Remove hand-built duplicate envelopes where possible.
4. Preserve request_id and limit metadata in error envelopes.
```

Acceptance:

```text
All gateway errors return consistent JSON shape.
Existing tests updated, not weakened.
```

---

## B2 — Pricing module hardening

**Priority:** high
Issues from reviews:

```text
pricing.yaml path uses __file__
module-level pricing globals are not ideal
unknown model fallback is silent
alias expansion path needs tests
```

Tasks:

```text
1. Load pricing.yaml via importlib.resources.
2. Add first-use warning for unknown model fallback.
3. Add tests for alias expansion in estimate_hard_monthly_reservation_cost_usd.
4. Consider PricingRegistry singleton later.
```

Acceptance:

```text
pricing works when package-installed.
unknown model logs warning once.
alias expansion test passes.
```

---

## B3 — Adapter profile registration retry cleanup

**Priority:** medium-high
Problem:

```text
register_adapter_profile has an IntegrityError retry/poll loop.
```

Tasks:

```text
1. Replace polling with INSERT ... ON CONFLICT DO NOTHING RETURNING where Postgres supports it.
2. Keep SQLite-compatible test path if necessary.
3. Return deterministic conflict/result.
```

---

## B4 — Status enums

**Priority:** medium-high
The second review calls this the highest-leverage maintainability change. I agree it is important, but after production-safety fixes.

Targets:

```text
GatewayRequest.status
GatewayAdapterProfile.status
GatewayAdapterProfileActivation.status
ProjectLimit.limit_mode
adaptation_mode
repair_kind
frontend StatusBadge values
```

Tasks:

```text
1. Define backend StrEnum values in one module.
2. Use enums in ORM/service/API code.
3. Ensure Pydantic serializes as strings.
4. Align frontend union types with backend values.
5. Fix PascalCase/snake_case mismatch, especially RolledBack / rolled_back.
```

Acceptance:

```text
No free-floating status strings in core paths.
Frontend badges match backend values.
```

---

# Track C — Scalability and performance

## C1 — Fix `admin_projects.list_projects` N+1

**Priority:** high
Problem:

```text
Per project:
- count active keys
- count requests

100 projects -> roughly 201 queries.
```

Tasks:

```text
1. Replace per-row counts with grouped aggregate query.
2. Or use two GROUP BY queries and join in Python.
3. Add test that query count does not scale linearly if query-count tooling exists.
```

---

## C2 — Dashboard summary indexes / rollups

**Priority:** high
Problem:

```text
dashboard scans gateway_requests for today's data.
```

Short-term:

```text
1. Add index on gateway_requests.created_at if missing.
2. Ensure dashboard query can use it.
```

Long-term:

```text
gateway_requests_daily_rollup table
periodic update job
dashboard reads rollup
```

---

## C3 — Usage timeseries SQL aggregation

**Priority:** high
Problem:

```text
admin_usage.get_usage_timeseries loads rows and bins in Python.
```

Tasks:

```text
1. Push binning into SQL.
2. Use date_trunc or dialect-compatible bucket expression.
3. Select only required columns.
4. Add tests for daily/hourly bucket correctness.
```

---

## C4 — Remove legacy hard-limit aggregate fallback

**Priority:** medium
Problem:

```text
reserve_gateway_request runs legacy daily/monthly aggregate queries on every hard-mode request.
```

Plan:

```text
1. Add feature flag: use_legacy_limit_fallbacks.
2. Verify ProjectUsageWindow is populated correctly.
3. Disable fallback in staging.
4. Remove after confidence period.
```

---

## C5 — DB pool settings

**Priority:** medium
Tasks:

```text
1. Add settings:
   db_pool_size
   db_max_overflow
   db_pool_timeout

2. Wire into create_async_engine.
3. Document relationship to workers and Postgres max_connections.
```

---

# Track D — Gateway maintainability

## D1 — Unify `run_chat_completion` and `run_chat_completion_stream` setup

**Priority:** high, but do after safety fixes
Problem confirmed in actual code: both functions duplicate reservation, request start, adapter profile association, client-error logging, and reservation reconciliation logic. The current `gateway_service.py` has both paths side by side with substantial duplication.

Refactor target:

```text
GatewayCallContext dataclass:
- request_id
- project_id
- api_key_id
- model
- domain_key
- explicit_gateway_profile_id
- limit_reservation_id
- started_at
- gateway_profile_id
- adapter_profile_id
- adaptation_mode
```

Helpers:

```text
_prepare_gateway_call()
_start_gateway_request()
_record_gateway_client_error()
_record_gateway_failure()
_finish_gateway_success()
```

Rules:

```text
Preserve session-per-phase pattern.
Preserve failure logging.
Preserve reservation reconciliation.
Do not change API behavior.
```

Acceptance:

```text
Existing gateway sync and streaming tests pass.
Diff reduces duplication without changing envelopes.
```

---

## D2 — Split `gateway_service.py`

After D1:

```text
gateway_service.py             public orchestration API
gateway_context.py             dataclasses/context
gateway_setup.py               reservation/start/profile association
gateway_finalize.py            finish success/failure/accounting
gateway_streaming.py           streaming drain/finalization helpers
gateway_errors.py              gateway error classes, or move to core.errors
```

Do this only after tests are strong.

---

## D3 — Streaming error events

**Priority:** medium
Problem:

```text
Once StreamingResponse starts, HTTP status is committed.
Typed gateway errors become generic SSE server_error.
```

Tasks:

```text
1. Emit structured SSE error events for known Gateway* errors.
2. Preserve request_id.
3. Add tests for stream provider failure after start.
```

---

# Track E — Admin adaptation proxy cleanup

## E1 — Add logging to generic proxy exceptions

**Priority:** high / easy
Task:

```text
In admin_adaptation.py, before generic 502 _problem() return:
logger.exception(...)
```

Acceptance:

```text
Unexpected proxy exceptions produce logs and sanitized API response.
```

---

## E2 — Extract proxy helpers

**Priority:** medium
Move pure helpers to a service module:

```text
_strip_browser_identity_and_roles_fields
_trim_optional_reason
_read_deployment_request_json
_idempotency_headers_from_request
_deployment_identity
```

Target:

```text
backend/app/services/adaptation_proxy_service.py
```

Add focused tests.

---

## E3 — Explicitly test identity stripping

**Priority:** high
Tests:

```text
browser-supplied roles stripped
browser-supplied identity stripped
case-insensitive snake/camel variants stripped
server-derived roles injected
idempotency key forwarded safely
```

---

# Track F — Frontend consolidation

## F1 — `useUrlFilters<T>` hook

**Priority:** medium
Problem:

```text
RequestsPage, AdaptationPlansPage, AdaptationProfilesPage, ActivityPage, AdaptationRunsPage repeat parse/build/apply/clear URL filter logic.
```

Task:

```text
Create shared useUrlFilters<T>().
Migrate one page first.
Then migrate the rest.
```

---

## F2 — Type consolidation

**Priority:** medium
Problem:

```text
lib/types.ts
lib/adaptationTypes.ts
lib/adaptationApi.ts
overlap shapes.
```

Task:

```text
Create frontend/lib/types/
- gateway.ts
- adaptation.ts
- problem.ts
```

---

## F3 — Redaction tests

**Priority:** high
Task:

```text
Add tests for redactSensitiveObject / redactSecretsDeep:
- Authorization headers
- OpenAI keys
- Anthropic keys
- internal adapter keys
- JWT-like tokens
- nested objects
- arrays
```

---

## F4 — Frontend error boundary

**Priority:** medium
Task:

```text
Add global AppShell/page error boundary.
Render recovery card.
Log error to console or telemetry hook.
```

---

## F5 — Split `globals.css`

**Priority:** low
Task:

```text
tokens.css
layout.css
components.css
```

---

# Track G — Agentor v0.1

Agentor should now be considered **stable enough for v0.1 foundation**. Do not expand it until backend hardening is underway.

Only do small polish:

```text
1. Update stale OntogonyCmsWorkflow docstrings.
2. Decide collection naming:
   external: essay
   internal path: essays
3. Validate whereNext objects:
   require kind + slug
   drop invalid entries
4. Add a tiny example with mock Conexus if useful.
```

Do **not** add yet:

```text
write-to-repo
open PR
MCP network server
LangGraph
A2A
agent memory
revision loops
```

---

# Recommended execution order

## Sprint 1 — Production safety

```text
1. Partial unique indexes for Active/Canary adapter activations
2. Single-worker hard-limit guard
3. Static admin fallback disable
4. Bound _project_reserve_locks and AdminLoginRateLimiter
5. Log generic admin_adaptation exceptions
```

## Sprint 2 — Security verification and correctness

```text
6. Verify/test frontend redaction and adminSessionFetch
7. Pricing importlib.resources + unknown model warning + alias tests
8. Consolidate gateway/core error hierarchy
9. Add status enums
```

## Sprint 3 — Performance

```text
10. Fix list_projects N+1
11. Add dashboard created_at index
12. Push usage timeseries aggregation into SQL
13. Plan legacy hard-limit fallback removal
```

## Sprint 4 — Maintainability

```text
14. Unify run_chat_completion / run_chat_completion_stream setup
15. Split gateway_service.py
16. Extract admin_adaptation helpers
17. Add frontend useUrlFilters
18. Split frontend types
```

## Sprint 5 — Agentor continuation

```text
19. Polish Agentor docs/schema naming
20. Add whereNext validation
21. Then consider v0.2 write/PR workflow
```

---

# Immediate next code-agent prompt

Use this first:

```text
You are working on Conexus main.

Use the consolidated Conexus hardening roadmap.

Implement Sprint 1, Task 1 only:
Adapter-profile activation race hardening.

Scope:
- backend/app/api/internal_adapter_profiles.py
- backend/app/db/models.py if needed
- alembic migration files
- backend/tests related to adapter profile activation

Tasks:
1. Add DB-level uniqueness so each domain_key can have at most:
   - one Active activation
   - one Canary activation

2. Use partial unique indexes where supported:
   - status = 'Active'
   - status = 'Canary'

3. Update API/service behavior:
   - concurrent or duplicate Active/Canary creation returns clean 409 conflict
   - no raw IntegrityError reaches client

4. Add tests:
   - duplicate Active for same domain is rejected
   - duplicate Canary for same domain is rejected
   - duplicate for different domain is allowed
   - conflict response is 409 and sanitized

5. Do not refactor gateway_service.
6. Do not touch Agentor.
7. Run backend tests and report exact result.
```

After that is green, continue to:

```text
Sprint 1 Task 2: hard-limit single-worker safety guard
```

This gives you a clean path: **safety first, then correctness, then performance, then maintainability, then Agentor v0.2.**
