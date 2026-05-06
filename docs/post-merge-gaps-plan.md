# Conexus remaining gaps plan (post-consolidation)

## Scope and repo target

This plan targets **`C:\dev\conexus`** (the repo that contains the referenced backend/frontend/agentor code and an existing CI workflow). The earlier report’s claim “CI missing” is **partially outdated**: there is already a GitHub Actions workflow at `[.github/workflows/ci.yml](.github/workflows/ci.yml)` running backend and frontend checks.

## Branching + artifact workflow (what you asked me to do next)

- Switch to `main` and update it.
- Create a new branch for the plan + follow-up work.
- Add a markdown plan file in `docs/` that enumerates each issue, where it lives, and the exact work to close it.

Recommended branch name:
- `plan/post-merge-gaps-2026-05-06`

Recommended plan doc path:
- `docs/post-merge-gaps-plan.md`

## Issues found (verified in code) and concrete fixes

### P0 — CI / quality gates (incomplete, not missing)

**Current state**
- Existing workflow: `[.github/workflows/ci.yml](.github/workflows/ci.yml)`
  - **Backend job**: installs `backend` with `pip install -e .[dev]`, runs `ruff check app tests`, runs `pytest -q`.
  - **Frontend job**: uses Node 20, runs `npm install` (not `npm ci`), runs `npm test -- --run`, runs `npm run build`.
- **No Agentor job** is present.
- **No mypy job** is present.

**Work to do**
- Update `[.github/workflows/ci.yml](.github/workflows/ci.yml)`:
  - **Frontend**: switch install step to `npm ci` (reproducible lockfile installs) and set cache dependency path to `frontend/package-lock.json` if present.
  - **Agentor**: add `agentor` job (Python 3.11):
    - `cd agentor`
    - `pip install -e .[dev]` (or equivalent per `agentor/pyproject.toml`)
    - `pytest -q`
  - **Mypy** (backend): add a job or a step.
    - If mypy currently passes: make it blocking.
    - If it does not: add it as a **non-blocking** job initially (allowed to fail) with a follow-up ticket to make it blocking.

**Acceptance criteria**
- PRs run backend+frontend+agentor checks on `pull_request`.
- Workflow uses deterministic installs (`npm ci`).
- If mypy is non-blocking, the workflow is explicit about the temporary state.

---

### P0 — Verify tests pass (local + CI)

**Current state**
- CI runs backend and frontend.
- Agentor tests are not run in CI.

**Work to do**
- After CI updates, ensure these are green in GitHub Actions (or locally when iterating):
  - backend: `pytest`, `ruff`, `mypy` (if enabled)
  - frontend: `npm test`, `npm run build`
  - agentor: `pytest`

**Acceptance criteria**
- A PR shows green checks for all three areas.

---

### P1 — `register_adapter_profile` retry loop cleanup (still present)

**Current state**
- In `[backend/app/api/internal_adapter_profiles.py](backend/app/api/internal_adapter_profiles.py)`, `register_adapter_profile` has an `IntegrityError` handler that:
  - rolls back
  - polls up to 100 times with `asyncio.sleep(0.01)` waiting for the winning transaction

Relevant snippet:

```148:173:backend/app/api/internal_adapter_profiles.py
    try:
        await session.flush()
    except BaseException as exc:
        if not isinstance(exc, IntegrityError):
            raise
        # Race: another request inserted the same adapter_profile_id concurrently.
        await session.rollback()
        existing = None
        # The winning transaction may not be committed yet; retry briefly.
        for _ in range(100):
            existing = await session.scalar(
                select(GatewayAdapterProfile).where(
                    GatewayAdapterProfile.adapter_profile_id == adapter_profile_id
                )
            )
            if existing is not None:
                break
            import asyncio

            await asyncio.sleep(0.01)
        if existing is None:
            raise
        return RegisterAdapterProfileResponse(
            gatewayProfileId=existing.gateway_profile_id,
            status=existing.status,
        )
```

**Work to do**
- Replace the polling loop with a deterministic “insert-or-read” strategy.
- Preferred for Postgres:
  - `INSERT ... ON CONFLICT (adapter_profile_id) DO NOTHING RETURNING gateway_profile_id, status`
  - If insert returns nothing, perform a single `SELECT`.
- Keep a SQLite-compatible fallback path for tests (SQLite supports `ON CONFLICT DO NOTHING` but RETURNING support depends on SQLite version; decide based on current test SQLite behavior).
- Add a focused concurrency test (or unit test of the new behavior) to ensure:
  - no polling
  - clean return of existing row

**Acceptance criteria**
- No loop/sleeps in the code path.
- Under concurrent calls, one insert wins and all callers receive a stable `gatewayProfileId`.

---

### P1 — DB pool settings are not configurable

**Current state**
- Engine creation in `[backend/app/db/session.py](backend/app/db/session.py)` uses `create_async_engine(settings.database_url, echo=False, pool_pre_ping=True, future=True)` with no pool sizing/timeouts.
- Settings class in `[backend/app/core/config.py](backend/app/core/config.py)` currently has no `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`.

**Work to do**
- Add settings to `[backend/app/core/config.py](backend/app/core/config.py)`:
  - `db_pool_size: int | None` (alias `DB_POOL_SIZE`)
  - `db_max_overflow: int | None` (alias `DB_MAX_OVERFLOW`)
  - `db_pool_timeout: int | None` (alias `DB_POOL_TIMEOUT`)
- Wire them into `[backend/app/db/session.py](backend/app/db/session.py)` `create_async_engine` call.
- Ensure SQLite paths don’t break (pool args may need conditional application depending on dialect).

**Acceptance criteria**
- In Postgres deployments, pool sizing is controlled by env vars.
- In SQLite tests, engine creation still works.

---

### P1 — `ALLOW_CREATE_ALL` in prod should fail-fast (currently warns)

**Current state**
- In `[backend/app/main.py](backend/app/main.py)` during lifespan startup, prod logs warnings if `settings.effective_allow_create_all` is true, but does not crash.

Relevant snippet:

```74:83:backend/app/main.py
    if settings.app_env.lower() == "prod":
        logger.warning("prod_startup use_alembic_migrations=true")
        if settings.effective_allow_create_all:
            logger.warning(
                "prod_startup_schema_notice create_all_enabled=true create_all_is_not_migrations=true"
            )
        else:
            logger.warning(
                "prod_startup_schema_notice create_all_enabled=false run_alembic_upgrade_head=true"
            )
```

**Work to do**
- Change behavior to **raise** in prod if `effective_allow_create_all` is true.
- Update docs (if needed) to reflect that prod will not start unless `ALLOW_CREATE_ALL=false`.

**Acceptance criteria**
- With `APP_ENV=prod` and `ALLOW_CREATE_ALL=true`, app startup fails immediately with a clear error.

---

### P2 — Gateway error envelope decision (detail vs canonical `{"error": ...}`)

**Current state**
- Gateway domain errors inherit from `ConexusDomainError` (e.g. `[backend/app/services/gateway_errors.py](backend/app/services/gateway_errors.py)`), but gateway exception handlers in `[backend/app/api/gateway.py](backend/app/api/gateway.py)` intentionally return `{"detail": ...}`.

Relevant snippet:

```92:126:backend/app/api/gateway.py
def register_gateway_exception_handlers(app: FastAPI) -> None:
    """Map gateway domain errors to the same JSON bodies as legacy HTTPException paths."""

    @app.exception_handler(GatewayClientError)
    async def _gateway_client_error(_request: Request, exc: GatewayClientError) -> Response:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": _error_detail(exc.code, exc.message, exc.request_id)},
            headers={REQUEST_ID_HEADER: exc.request_id},
        )
```

**Work to do (choose one)**
- Option A (compat): keep `detail` envelope but document it clearly as the gateway compatibility surface.
- Option B (canonical): migrate gateway errors to `{"error": {...}}` and update frontend/client expectations accordingly.

**Acceptance criteria**
- A single documented envelope policy for gateway errors.
- Tests cover the chosen shape.

---

### P2 — Streaming SSE error payloads are generic and omit `request_id`

**Current state**
- In `[backend/app/api/gateway.py](backend/app/api/gateway.py)`, `_event_stream()` catches all exceptions and yields:
  - `{"error": {"message": "Stream interrupted.", "type": "server_error"}}`
  - No `request_id` in payload.
  - No typed mapping for known gateway errors.

Relevant snippet:

```163:201:backend/app/api/gateway.py
        async def _event_stream():
            sent_role = False
            try:
                async for chunk in stream_result.stream:
                    # ...
                    yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            except Exception:
                logger.exception(
                    "gateway_stream_interrupted request_id=%s", request_id
                )
                err_payload = {
                    "error": {
                        "message": "Stream interrupted.",
                        "type": "server_error",
                    }
                }
                yield f"data: {json.dumps(err_payload)}\n\n".encode("utf-8")
            finally:
                yield b"data: [DONE]\n\n"
```

**Work to do**
- Implement typed SSE error events for known gateway errors (at minimum: `GatewayClientError`, `GatewayLimitError`, `GatewayUpstreamError`).
- Ensure SSE error payload includes `request_id`.
- Add tests to validate:
  - error payload shape
  - request id presence
  - behavior when error occurs after streaming has started

**Acceptance criteria**
- Streaming errors preserve structured error data for known error types.
- `request_id` is always present.

---

### P2 — Frontend: `useUrlFilters` migration is partial

**Current state**
- `useUrlFilters` exists at `[frontend/hooks/useUrlFilters.ts](frontend/hooks/useUrlFilters.ts)`.
- `ActivityPage` uses it at `[frontend/app/activity/page.tsx](frontend/app/activity/page.tsx)`.
- Other pages still do their own `URLSearchParams`/`replaceState` logic (examples):
  - `[frontend/app/requests/page.tsx](frontend/app/requests/page.tsx)`
  - `[frontend/app/adaptation/profiles/page.tsx](frontend/app/adaptation/profiles/page.tsx)`
  - `[frontend/app/adaptation/plans/page.tsx](frontend/app/adaptation/plans/page.tsx)`
  - `[frontend/app/adaptation/runs/page.tsx](frontend/app/adaptation/runs/page.tsx)`

**Work to do**
- Migrate the remaining filter-heavy pages to `useUrlFilters`.
- Normalize filter key naming and defaulting across pages.
- Ensure pagination offsets reset appropriately on filter apply.

**Acceptance criteria**
- All targeted pages share the same URL filter parsing/building behavior.
- No duplicated `URLSearchParams`/`history.replaceState` blocks for these pages.

---

### P2 — Frontend: global error boundary missing

**Current state**
- No evidence of an app-wide error boundary in the `frontend/app/` structure from code search.

**Work to do**
- Add a global error boundary using Next.js App Router conventions (e.g., `frontend/app/error.tsx` and possibly `frontend/app/global-error.tsx` depending on desired scope).
- Provide a recovery UI (retry, navigate back, link to dashboard).

**Acceptance criteria**
- Runtime render errors show a user-friendly recovery card rather than a blank page.

---

### P2 — CSRF policy/documentation is minimal

**Current state**
- Deployment docs note cookies default to `SameSite=Lax` and that many deployments are same-site across subdomains.
- No explicit CSRF token mechanism was found; no explicit “state-changing must not be GET” policy section was found in the frontend/backend code in this scan.

**Work to do (choose one)**
- Option A (documentation + conventions): explicitly document CSRF posture and add tests/guards that state-changing endpoints are not implemented as GET.
- Option B (token-based): implement double-submit CSRF tokens for cookie-authenticated admin endpoints.

**Acceptance criteria**
- Clear documented CSRF posture and enforcement aligned with the chosen option.

---

### P2+ — Distributed hard-limit locking (still a guard)

**Current state**
- There is a config flag `GATEWAY_HARD_LIMIT_DISTRIBUTED_LOCK_ENABLED` in `[backend/app/core/config.py](backend/app/core/config.py)` but no distributed lock implementation was addressed in this plan scan.
- Multi-worker safety is currently a guard (checked at startup), not a scaling solution.

**Work to do**
- Choose one approach:
  - Redis lock per `project_id`
  - or a Postgres-transaction approach (serializable / advisory locks)
- Implement with integration tests and clear operational docs.

**Acceptance criteria**
- Safe multi-replica operation is supported (or explicitly out of scope with guardrails).

---

### P2+ — Usage timeseries cross-DB verification

**Current state**
- `[backend/app/api/admin_usage.py](backend/app/api/admin_usage.py)` buckets timeseries via `func.extract("epoch", GatewayRequest.created_at)`.

**Work to do**
- Add tests that validate the bucketing query works on:
  - SQLite (unit tests)
  - Postgres (optional integration smoke later; document how to run)

**Acceptance criteria**
- Confidence that the SQL aggregation behaves consistently on target DBs.

---

### Deferred / medium: daily rollup table

**Current state**
- No daily rollup table / job was found in the scanned files.

**Work to do**
- If/when needed for scale, implement `gateway_requests_daily_rollup` + periodic update job + dashboard reads.

**Acceptance criteria**
- Dashboard performance is stable at high request volumes.

---

### Deferred / medium: pricing registry refactor

**Current state**
- (Not re-scanned in this pass.) Report indicates module-level globals for pricing cache/warn-once.

**Work to do**
- Replace module-level globals with an injected registry/service object.

**Acceptance criteria**
- Pricing loading is testable, thread-safe, and explicit.

---

### Agentor (keep mostly frozen; CI coverage only)

**Current state**
- Agentor exists in `agentor/` and has tests, but is not covered by CI.

**Work to do**
- Add the Agentor CI job (see CI section).
- Defer larger Agentor roadmap items until backend hardening/CI is stable.

## Proposed PR slicing (small, mergeable)

1) **PR: CI completion**
- Update `[.github/workflows/ci.yml](.github/workflows/ci.yml)` (agentor + mypy + npm ci)

2) **PR: production config hardening**
- Fail-fast on `ALLOW_CREATE_ALL` in prod (`[backend/app/main.py](backend/app/main.py)`)
- Add DB pool settings (`[backend/app/core/config.py](backend/app/core/config.py)`, `[backend/app/db/session.py](backend/app/db/session.py)`)

3) **PR: adapter profile registration race cleanup**
- Remove polling loop (`[backend/app/api/internal_adapter_profiles.py](backend/app/api/internal_adapter_profiles.py)`)

4) **PR: streaming SSE error payloads**
- Typed SSE errors + request_id + tests (`[backend/app/api/gateway.py](backend/app/api/gateway.py)`)

5) **PR: frontend admin polish**
- error boundary
- finish `useUrlFilters` migration
- CSRF documentation/policy selection

## Test plan (per PR)

- CI PR:
  - Validate workflow runs on PR and all jobs execute.
- Prod hardening PR:
  - Unit tests for settings + engine creation; startup behavior in `APP_ENV=prod`.
- Adapter registration PR:
  - Concurrency/race behavior test.
- Streaming errors PR:
  - SSE stream tests around mid-stream failure.
- Frontend polish PR:
  - `npm test` + `npm run build`; manual smoke of error boundary and filter URLs.

