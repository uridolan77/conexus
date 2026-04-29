Goal: implement the next substantial Conexus hardening slice after commit `2cab627`:
- middleware now protects `/adaptation`
- `adminSessionFetch` exists
- OpenAI stream creation retry exists
- login limiter rejects mismatched config
- composite index on `gateway_requests(project_id, created_at)` exists

This next slice should focus on:
1. hard-limit correctness under concurrency
2. production-mode warnings for process-local protections
3. backend health/readiness and Docker health checks
4. safer admin session/token handling
5. small provider/gateway reliability improvements
6. frontend auth UX consistency

Do not touch:
- `conexus.adaptation`
- adaptation service internals
- profile publishing/canary/rollback
- KGB/SLOD
- Redis implementation unless explicitly scoped as optional design-only
- major gateway rewrite
- public `/v1/chat/completions` response shape

Do not introduce:
- new queue/background worker
- new auth system
- paid external service dependency
- large frontend redesign

============================================================
PHASE 1 — Hard-limit concurrency semantics
============================================================

Current issue:
Project hard limits are currently checked by reading existing `gateway_requests` aggregates before starting the request. Under concurrent traffic, many requests can pass the preflight check simultaneously before their log rows affect the aggregate. This means “hard” limits can be exceeded under burst concurrency.

Goal:
Make the semantics explicit and improve correctness without overbuilding.

Step 1 — Document current semantics

In backend docs or code comments near `check_hard_limits`:
- Document whether the current limit mode is:
  - strict hard limit, or
  - best-effort hard limit under concurrency

For now, prefer:
- “best-effort hard limit under concurrent bursts”
unless this patch implements locking.

Step 2 — Add a concurrency regression test

Add a test showing current or improved expected behavior.

Suggested test:
- configure project hard daily_request_limit = 1
- fire multiple concurrent requests for the same project/API key
- assert expected behavior

If strict locking is not implemented in this slice:
- mark the test as documenting current best-effort behavior
- or add an xfail/skip with a clear TODO

If strict locking is implemented:
- assert that at most one request proceeds.

Step 3 — Implement minimal DB-backed reservation if practical

Preferred minimal approach:
- Add a small `project_limit_reservations` or `project_usage_counters` table is probably too much for this slice.
- Instead, if PostgreSQL is the production target, use row-level locking on `project_limits`:
  - in the same transaction:
    - `SELECT project_limits ... FOR UPDATE`
    - compute usage
    - insert/mark a started request row
  - commit before provider call if needed
- SQLite does not support the same semantics; tests may need to document SQLite behavior separately.

Do not force a large cross-database abstraction if it becomes messy.

Acceptable outcome for this slice:
- code/documentation explicitly states current behavior is best-effort
- a design note describes strict enforcement options:
  - DB row lock on `project_limits`
  - Redis atomic counters
  - monthly/daily counter table

Add doc:
`docs/hard-limit-concurrency.md`

Cover:
- current behavior
- risk under bursts
- recommended production implementation
- why Redis/row locking is deferred or implemented

============================================================
PHASE 2 — Production warning for process-local login limiter
============================================================

Current state:
`AdminLoginRateLimiter` is process-local and in-memory. That is fine for local/dev/single-process deployments, but not enough for multi-worker/multi-replica production.

Task:
Add a startup warning when:
- `APP_ENV=prod` or equivalent production mode
- login limiter backend is still in-memory/process-local

Do not add Redis yet.

Implementation:
- Find the existing startup/lifespan hardening checks.
- Add log warning:
  `admin_login_rate_limiter_in_memory_prod_warning`
- Message should say:
  - process-local limiter is not shared across workers/replicas
  - use a distributed limiter before multi-replica production

Optional setting:
- `ADMIN_LOGIN_RATE_LIMIT_BACKEND=in_memory`
- default: `in_memory`
- docs mention future `redis`

Tests:
- settings/startup test if existing pattern supports it
- otherwise add unit test for helper function that decides whether to warn

============================================================
PHASE 3 — Health and readiness endpoints
============================================================

Goal:
Make Docker/orchestrated startup safer.

Add backend endpoints:

1. `GET /health`
- unauthenticated
- returns 200 if process is alive
- JSON:
```json
{
  "status": "ok",
  "service": "conexus",
  "version": "..."
}
````

2. `GET /readyz`

* unauthenticated
* checks:

  * DB connectivity with a cheap `SELECT 1`
  * encryption readiness if that is not already guaranteed at startup
  * model alias config is loaded/valid if available
* returns 200 if ready
* returns 503 if not ready
* do not expose secrets or full exception strings in production response

Add tests:

* `/health` returns 200
* `/readyz` returns 200 with working test DB
* `/readyz` returns 503 if DB check fails, if practical with monkeypatch/mock

Update `docker-compose.yml`:

* backend healthcheck calls `/health` or `/readyz`
* frontend depends on backend `condition: service_healthy` if compose format supports it
* add `restart: unless-stopped` for backend/frontend if appropriate

Do not break local dev.

============================================================
PHASE 4 — Admin session/token safety
====================================

Current review concern:
Session token payload uses a pipe-delimited format:
`username|admin_user_id|exp`
If a username contains `|`, token parsing becomes ambiguous.

Task:
Prevent future ambiguous admin usernames.

Do not rewrite the token format in this slice unless very small.

Implement:

* validation that admin usernames cannot contain `|`
* apply to:

  * CLI/admin user creation path
  * API admin user creation path, if present
  * any service-layer validation for admin usernames
* add test:

  * creating/admin-validating username with `|` fails clearly
  * normal username still works

Optional:

* add code comment near token issue/parse:

  * `|` is forbidden in usernames because session token payload is pipe-delimited.

Do not invalidate existing normal sessions.

============================================================
PHASE 5 — Provider streaming retry parity
=========================================

OpenAI stream creation retry was implemented in commit `2cab627`.

Now inspect Anthropic.

Task:

* If Anthropic non-streaming uses retry but stream creation does not, add retry for stream creation only.
* Do not retry after chunks are emitted.
* Preserve provider error mapping:

  * rate limit → ProviderRateLimitError
  * connection/5xx/unavailable → ProviderUnavailableError
  * other SDK/provider error → ProviderError

Tests:

* transient Anthropic stream creation rate limit/unavailable is retried, if fake SDK setup exists
* persistent stream creation error maps to normalized provider error

If Anthropic SDK stream API is hard to fake:

* add a minimal unit around the retry helper
* document limitation

============================================================
PHASE 6 — Frontend auth UX consistency
======================================

Current state:
`adminSessionFetch` exists and many pages use it. Ensure all cookie-authenticated admin pages use it consistently.

Task:
Search frontend for raw:

```text
fetch(`${BACKEND_BASE}/admin
fetch(BACKEND_BASE + "/admin
credentials: "include"
window.location.href = "/login"
```

For admin API calls:

* replace with `adminSessionFetch`
* keep unauthenticated routes untouched:

  * login
  * health
  * gateway `/v1/...` testing if intentionally API-key based

Ensure adaptation pages still work.

Add tests:

* `adminSessionFetch` redirects on 401 in browser env
* `adminSessionFetch` does not throw in node/server test env
* one representative page uses it, if current frontend test style supports that

============================================================
PHASE 7 — Gateway model-prefix diagnostics
==========================================

Current behavior:
Unknown model names raise `UnknownModelError`. Good. But operator diagnostics can improve.

Task:
Update unknown-model error message to include:

* known aliases
* accepted provider prefixes:

  * Anthropic prefixes
  * OpenAI prefixes

Do not allow silent fallback.

Tests:

* unknown model still errors
* error message includes at least one alias and one provider prefix
* existing gateway behavior unchanged

============================================================
PHASE 8 — Small cleanup items
=============================

Do these only if quick:

1. `anthropic_adapter.py`

* `_safe_message` currently appears to be a no-op.
* Either:

  * implement real sanitization, or
  * remove the misleading helper and keep a direct safe message.
* Do not leak upstream headers/secrets.

2. `admin_login_rate_limiter.py`

* already removed redundant second prune in `record_failure`; confirm.

3. `structlog`

* if `structlog` is listed in dependencies but unused, either:

  * remove dependency, or
  * leave with TODO if planned.
* Prefer not to start a logging migration now.

4. `pricing.py`

* if using `_pricing_loaded` + cache dict, consider replacing with a single nullable cache sentinel.
* Only do if tests are nearby and simple.

============================================================
PHASE 9 — Tests and checks
==========================

Backend checks:

```bash
cd backend
pytest -q
ruff check .
```

Frontend checks, if frontend changed:

```bash
cd frontend
npm test -- --run
npm run build
```

If Docker compose changed:

* no need to fully run compose unless easy
* at least validate YAML formatting if tooling exists

Report:

* files changed
* backend endpoints added
* migrations added
* tests added/updated
* backend test result
* frontend test/build result
* any skipped/deferred items
* whether hard limits are now strict or explicitly documented as best-effort

============================================================
Expected final state
====================

After this slice:

* BO routes, including `/adaptation`, remain protected.
* Expired/tampered admin sessions redirect more consistently.
* OpenAI and Anthropic streaming creation retry behavior is symmetric where practical.
* Usage/limits queries have the composite DB index.
* Hard-limit concurrency semantics are either improved or clearly documented.
* Health/readiness endpoints exist.
* Docker startup is safer.
* Process-local login limiter limitation is visible in production.
* Admin usernames cannot break pipe-delimited session tokens.
* Unknown model errors are more operator-friendly.
* No adaptation-service changes were made.
* No publishing/canary/rollback was added.

```

I would treat this as **Conexus hardening v0.6**, not as a feature sprint. The only “big” unresolved item is strict hard-limit enforcement; the prompt gives Cursor permission to document it if a clean DB-lock implementation becomes too large.
```
