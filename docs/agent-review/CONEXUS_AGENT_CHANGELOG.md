# Conexus — Agent Changelog

This file is intentionally operational and chronological. It records what changed, why it was safe, and what validations were run.

Last updated: 2026-04-30 (second pass appended)

## Files changed (by this agent)

### Docs added

- `docs/agent-review/CONEXUS_DEEP_OVERVIEW.md`
  - **Why safe**: documentation only.
  - **Behavior impact**: none.
- `docs/agent-review/CONEXUS_TECH_DEBT_REGISTER.md`
  - **Why safe**: documentation only.
  - **Behavior impact**: none.
- `docs/agent-review/CONEXUS_REFACTOR_PLAN.md`
  - **Why safe**: documentation only.
  - **Behavior impact**: none.
- `docs/agent-review/CONEXUS_TEST_GAP_ANALYSIS.md`
  - **Why safe**: documentation only.
  - **Behavior impact**: none.
- `docs/agent-review/CONEXUS_AGENT_CHANGELOG.md`
  - **Why safe**: documentation only.
  - **Behavior impact**: none.

## Code changes (pending)

- `.github/workflows/ci.yml`
  - **Change**: run `npm test -- --run` in the frontend CI job.
  - **Why safe**: CI-only change; does not affect runtime behavior or deployment artifacts.
  - **Behavior impact**: none (product/runtime).

## Commands run (pending)

- Backend:
  - `cd backend`
  - `python -m pytest -q`
  - `python -m ruff check app tests`
- Frontend:
  - `cd frontend`
  - `npm test -- --run`
  - `npm run build`
- Repo:
  - `docker compose config`

## Results (first pass)

- Backend: **PASS**
  - `269 passed`
  - `ruff`: `All checks passed!`
- Frontend: **PASS**
  - `30 passed`
  - `next build`: success
- `docker compose config`: **PASS`

---

## Second pass — 2026-04-30

### Code changes

- `backend/app/services/gateway_service.py`
  - **Change**: expanded `_project_reserve_locks` comment to include an explicit
    SINGLE-PROCESS ONLY warning and production-safe future options.
  - **Why safe**: comment only; no behavior change.
  - **Behavior impact**: none.

- `backend/tests/test_internal_adapter_profiles.py`
  - **Change**: added `test_internal_api_key_not_configured_returns_503` and
    `test_adapter_profile_registry_disabled_returns_404`.
  - **Why safe**: new tests only; no production code changed.
  - **Behavior impact**: none (test-only).

- `backend/tests/test_gateway_endpoint.py`
  - **Change**: added `test_chat_completions_stream_no_usage_chunk_logs_completed_with_null_tokens`.
  - **Why safe**: new test documenting existing behavior; no production code changed.
  - **Behavior impact**: none (test-only).

### Docs added / updated

- `docs/agent-review/CONEXUS_SECOND_PASS.md` — new; full second-pass record.
- `docs/agent-review/CONEXUS_TECH_DEBT_REGISTER.md` — status updates for TD-003, TD-005, TD-007.
- `docs/agent-review/CONEXUS_REFACTOR_PLAN.md` — updated CI lint status; added observability future query plan reference; noted process-local doc completion.
- `docs/agent-review/CONEXUS_TEST_GAP_ANALYSIS.md` — marked covered stream gaps; noted new internal-key tests.
- `docs/agent-review/CONEXUS_AGENT_CHANGELOG.md` — this entry.

### Commands run (second pass)

- `cd backend && python -m pytest -q`
- `cd backend && python -m ruff check app tests`
- `cd frontend && npm test -- --run`
- `cd frontend && npm run build` (NEXT_TELEMETRY_DISABLED=1)
- `cd frontend && npm run lint` (probed only — blocked by missing ESLint install)
- `docker compose config`

### Results (second pass)

- Backend: **PASS** — `272 passed` (+3), `ruff`: `All checks passed!`
- Frontend tests: **PASS** — `30 passed`
- Frontend build: **PASS**
- Frontend lint: **BLOCKED** — `next lint` prompts for interactive ESLint install;
  `eslint` not in devDependencies, no `.eslintrc.*` at project root.
- `docker compose config`: **PASS**

