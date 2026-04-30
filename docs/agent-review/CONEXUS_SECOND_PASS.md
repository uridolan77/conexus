# Conexus — Second Hardening Pass

Agent pass date: 2026-04-30

## Scope

This was a narrow, low-risk hardening pass. Architecture rewrites, public API changes,
database schema changes, provider-runtime rewiring, internal-auth redesign, and
multi-replica coordination redesign were all explicitly out of scope.

---

## 1. CI / Frontend Lint Gap

### What was reviewed

- `frontend/package.json` — has `"lint": "next lint"`.
- `.github/workflows/ci.yml` — already runs `npm test -- --run` and `npm run build`.
- Running `npm run lint` manually: `next lint` opens an interactive ESLint setup
  prompt (`? How would you like to configure ESLint?`) because `eslint` is not in
  `devDependencies` and there is no `.eslintrc.*` file at the project root.

### What was changed

Nothing. Adding `npm run lint` to CI would fail immediately (interactive prompt hangs
in non-TTY, no auto-exit).

### Deferred — why

Pre-existing configuration gap: ESLint is not installed and the project has no
`.eslintrc.*`. Forcing a broad cleanup of the ESLint setup is out of scope for a
hardening pass.

### Smallest future fix

1. `npm install --save-dev eslint eslint-config-next` in `frontend/`.
2. Create a minimal `.eslintrc.json`:
   ```json
   { "extends": "next/core-web-vitals" }
   ```
3. Add `- name: Lint` / `run: npm run lint` between Test and Build in the CI frontend job.

---

## 2. Internal `/internal/*` Static Key Posture

### What was reviewed

`backend/app/api/internal_adapter_profiles.py` — `require_internal_adapter_api_key` dependency:

- Uses `hmac.compare_digest` for timing-safe comparison. ✓
- Returns 503 (not 401) when `INTERNAL_ADAPTER_API_KEY` is absent/empty — safe-fail
  posture is correct. ✓
- Returns 401 when key is present but wrong. ✓
- **The key is never logged or echoed in any response body or error message.** ✓

`backend/app/main.py` — `_ensure_prod_secret_hardening()`:

- Checks `AUTH_SECRET` and `ADMIN_PASSWORD` for weak defaults at startup.
- Does **not** check that `INTERNAL_ADAPTER_API_KEY` is set in prod.
- In prod with registry enabled but no key: every `/internal/*` call returns 503 at
  request time. This is safe-fail but silent at startup.

### What was changed

Added two new tests to `backend/tests/test_internal_adapter_profiles.py`:

- **`test_internal_api_key_not_configured_returns_503`** — verifies the existing
  safe-fail 503 behavior when `INTERNAL_ADAPTER_API_KEY` is None.
- **`test_adapter_profile_registry_disabled_returns_404`** — verifies the 404
  behavior when `ADAPTER_PROFILE_REGISTRY_ENABLED=False`.

### Deferred — startup check in prod

Adding a startup check to `_ensure_prod_secret_hardening()` for a missing
`INTERNAL_ADAPTER_API_KEY` would be a small, safe change, but this is a new
production-gate behavior (not an existing behavior), so an owner should decide
whether to enforce it.

**Recommended future change (one line in `main.py`):**
```python
if settings.adapter_profile_registry_enabled and not (settings.internal_adapter_api_key or "").strip():
    problems.append("INTERNAL_ADAPTER_API_KEY is not set while adapter profile registry is enabled")
```

---

## 3. Streaming Accounting Risk

### What was reviewed

`backend/app/services/gateway_service.py` — `_wrapped()` async generator inside
`run_chat_completion_stream`:

- **Mid-stream provider error** (`ProviderError`, `AllProvidersFailedError`, etc.):
  `_record_failure` is called → DB row set to `status=failed`. ✓
- **Stream timeout** (`asyncio.wait_for` / `TimeoutError`): same `_record_failure`
  path. ✓
- **Generic exception**: caught by `except Exception` → `_record_failure` → DB row
  `status=failed`. ✓
- **Normal stream completion, no usage chunk**: `final_usage is None` →
  `cost=None`, `total_tokens=0`, `finish_request_success` called with
  `prompt_tokens=None, completion_tokens=None, estimated_cost=None` →
  DB row `status=completed` with null token/cost fields.

The existing test suite already covered mid-stream `RuntimeError`, `ProviderError`,
and stream timeout. The one untested path was **stream completes cleanly but provider
emits no usage chunk**.

### What was changed

Added one new test to `backend/tests/test_gateway_endpoint.py`:

- **`test_chat_completions_stream_no_usage_chunk_logs_completed_with_null_tokens`** —
  verifies that when a stream completes without a usage chunk the DB row has
  `status=completed`, `prompt_tokens=None`, `completion_tokens=None`,
  `total_tokens=None`, `estimated_cost=None`.

### Risk note (not changed)

This null-usage path is correct behavior (best-effort accounting) but means the
observability endpoint and BO usage reports will show 0-token, 0-cost records for
providers that don't emit usage in streaming mode. There is no simple fix without
provider-specific post-stream usage fetching (out of scope).

---

## 4. Request Correlation

### What was reviewed

`backend/app/api/gateway.py`:

- Mints a server-side `request_id` (UUID hex via `new_request_id()`).
- Sets `X-Conexus-Request-Id` header on all responses (streaming and non-streaming).
- Does not read or store any inbound `X-Request-Id` / `X-Correlation-Id`.

### What was changed

Nothing.

### Deferred — why

Storing a caller-supplied correlation ID requires a new `correlation_id` column in
the `GatewayRequest` DB table, which is a schema migration. Running a migration in
a hardening pass (without a matching Alembic revision) is out of scope.

### Smallest future fix

1. Add `correlation_id TEXT` column to `GatewayRequest` model + Alembic migration.
2. In `gateway.py` `chat_completions`, read:
   ```python
   correlation_id = request.headers.get("X-Request-Id") or request.headers.get("X-Correlation-Id")
   ```
3. Pass `correlation_id` (not `request_id`) through to `start_request` as
   a metadata field only — never use it for auth or routing decisions.
4. Log it alongside `request_id` in the `gateway_request_ok` log line.

Security note: the inbound value must **only** be stored as metadata and must never
influence routing, auth, rate-limiting, or any security decision.

---

## 5. Observability Endpoint Scaling

### What was reviewed

`backend/app/api/internal_adapter_profiles.py` — `get_observability`:

- Fetches `(status, latency_ms, estimated_cost)` for all rows in the window into
  a Python list.
- Computes error_rate (Python sum), latency_p95 (Python sort + index), and
  cost_per_answer (Python sum/count) in-process.
- For large windows or high-traffic adapters, this could load thousands of rows.

### What was changed

Nothing.

### Deferred — why

The aggregate SQL equivalent for error_rate and cost_per_answer is straightforward
(`SUM(CASE ...) / COUNT(*)`, `AVG(estimated_cost) FILTER (WHERE status='completed')`),
but **p95 latency is not portable**: PostgreSQL has `percentile_cont(0.95) WITHIN
GROUP (ORDER BY latency_ms)`, SQLite does not. Since tests use SQLite, any SQL
rewrite would need a compatibility shim or two code paths, which risks introducing
bugs and breaking existing tests.

### Future query plan (PostgreSQL-native)

```sql
SELECT
  COUNT(*)                                                    AS request_count,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)::float
    / NULLIF(COUNT(*), 0)                                     AS error_rate,
  percentile_cont(0.95) WITHIN GROUP (
    ORDER BY latency_ms
  ) FILTER (WHERE status = 'completed')                       AS latency_p95_ms,
  AVG(estimated_cost) FILTER (
    WHERE status = 'completed' AND estimated_cost IS NOT NULL
  )                                                           AS cost_per_answer
FROM gateway_requests
WHERE gateway_profile_id = :gateway_profile_id
  AND created_at >= :window_start
  AND created_at <= :window_end
```

Add index: `CREATE INDEX idx_gateway_requests_profile_window ON gateway_requests (gateway_profile_id, created_at)`.

Owner decision: whether to maintain a SQLite compat shim for tests or gate the
SQL path on the DB dialect.

---

## 6. Process-Local Mechanisms

### What was reviewed

**`backend/app/services/admin_login_rate_limiter.py`**:

- Docstring on `get_admin_login_rate_limiter` already says: "In-memory state is
  **single-process only** (not shared across workers or hosts)."
- `main.py` lifespan emits `admin_login_rate_limiter_in_memory_prod_warning` at
  startup when `app_env=prod` and backend is `in_memory`. ✓

**`backend/app/services/gateway_service.py`** — `_project_reserve_locks`:

- Original comment mentioned SQLite/Postgres transaction behavior only.
- No multi-replica warning.

### What was changed

Added an expanded module-level comment to `_project_reserve_locks` in
`backend/app/services/gateway_service.py`:

```
# SINGLE-PROCESS ONLY: asyncio.Lock is not shared across OS processes, workers,
# or replicas. Under multi-replica deployment the serialization guarantee is lost
# and concurrent reservations from different processes may both pass the hard-limit
# check for the same project window. The DB reservation table provides a last-line
# of defense (rows are committed individually), but strict admission is not
# guaranteed without a distributed lock or a serializable DB transaction.
# Production-safe future options: serializable Postgres transactions on the
# reservation INSERT, or a Redis-based distributed lock per project_id.
```

---

## Validation

### Commands run

```bash
# Backend
cd backend
python -m pytest -q
python -m ruff check app tests

# Frontend
cd frontend
npm test -- --run          # PASS
npm run build              # PASS (NEXT_TELEMETRY_DISABLED=1)
npm run lint               # BLOCKED — see below

# Repo
docker compose config
```

### Results

| Check | Result | Notes |
|---|---|---|
| `pytest -q` | **272 passed** | Up from 269; 3 new tests added |
| `ruff check app tests` | **All checks passed!** | |
| `npm test -- --run` | **30 passed** | |
| `npm run build` | **PASS** | Build completed successfully |
| `npm run lint` | **BLOCKED** | Interactive ESLint setup prompt — ESLint not installed |
| `docker compose config` | **PASS** | Exit 0, no errors |

---

## Summary

| Item | Action | Reason |
|---|---|---|
| CI lint step | Deferred | ESLint not installed; would require devDependency addition and `.eslintrc` |
| Internal key safe-fail test | **Added** | 2 new tests covering 503 (key absent) and 404 (registry disabled) |
| Internal key startup check | Deferred | New production-gate behavior; owner decision needed |
| Stream no-usage test | **Added** | 1 new test documenting null-token accounting posture |
| Request correlation | Deferred | Requires DB schema migration |
| Observability SQL refactor | Deferred | p95 percentile SQL is not SQLite-compatible |
| `_project_reserve_locks` single-process doc | **Added** | Comment expansion only; no behavior change |

---

## Remaining Owner Decisions

1. **ESLint**: Install eslint + `eslint-config-next`, add `.eslintrc.json`, add lint step to CI.
2. **Internal key startup hardening**: Add `INTERNAL_ADAPTER_API_KEY` check to `_ensure_prod_secret_hardening()` for prod deployments with registry enabled.
3. **Request correlation**: Decide column name, migration strategy, logging format, and privacy constraints before adding `correlation_id` storage.
4. **Observability SQL**: Decide whether to maintain a SQLite compat shim, gate on dialect, or accept the Python row materialization path until volumes warrant the change.
5. **Multi-replica production**: Decide whether Conexus will run multi-replica soon and prioritize either a serializable Postgres reservation INSERT or Redis-based per-project locking for strict hard-limit admission.
