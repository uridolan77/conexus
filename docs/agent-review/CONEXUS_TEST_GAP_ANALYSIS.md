# Conexus — Test Gap Analysis

Last updated: 2026-05-04 (M5/M6 cleanup pass)

## Current coverage impression

- **Backend**: has pytest + ruff, runs in CI. Core gateway + admin endpoints appear testable, and many components already isolate dependencies (e.g. provider factory override).
- **Frontend**: has Vitest configured; CI runs `npm test -- --run` and `npm run build`. ESLint is still not installed/configured, so lint is intentionally not in CI yet.
- **Integration**: docker-compose provides a realistic local stack, but there is no automated smoke/integration suite in CI.

## High-risk areas needing stronger tests

### Gateway streaming edge cases

- **Status after second pass**
  - Stream interruption (`RuntimeError`, `ProviderError`): ✓ already tested.
  - Stream timeout (per-chunk `asyncio.wait_for`): ✓ already tested.
  - Stream “usage not emitted”: ✓ **added in second pass** —
    `test_chat_completions_stream_no_usage_chunk_logs_completed_with_null_tokens`
    verifies `status=completed` with `prompt_tokens/completion_tokens/estimated_cost = None`.
- **Still missing**
  - Reservation reconcile path when stream fails with a hard-limit reservation active.

### Strict limit reservations correctness

- **Missing tests**
  - Concurrency scenarios: multiple concurrent reserves for the same project.
  - Stale reservation classification: each kind results in correct recommended action.
  - Repair apply vs dry-run: verify counter deltas are correct and idempotent.

### Adaptation proxy safety invariants

- **Missing/needs strengthening**
  - Identity stripping is case-insensitive and snake_case-aware for all known keys (`requestedByUserId`, `requested_by_user_id`, `roles`, etc.).
  - Idempotency header forwarding for the right operations.
  - Malformed JSON yields 400 and does not proxy upstream.
  - Permission checks block before any upstream call.

### Internal adapter registry race behavior

- **Missing tests**
  - `register` is idempotent under concurrent insert (IntegrityError race) and returns the existing gatewayProfileId.
  - Activation rules: one active/canary per domain; promote/rollback semantics.

## Suggested test additions (smallest practical)

### Backend unit tests

- ~~`backend/tests/test_gateway_stream_logging.py`~~ *(covered: stream interruption,
  timeout, and no-usage paths all tested in `test_gateway_endpoint.py` as of second pass)*
- `backend/tests/test_internal_adapter_profile_register_race.py`
  - simulate IntegrityError path and ensure stable outcome

### Internal key posture tests *(added in second pass)*

- `test_internal_api_key_not_configured_returns_503` — in `test_internal_adapter_profiles.py`.
- `test_adapter_profile_registry_disabled_returns_404` — in `test_internal_adapter_profiles.py`.

### Backend integration smoke (local-only)

- A lightweight script (or pytest marked integration) that:
  - boots docker-compose
  - runs `/health`, logs in admin, creates a project+key, does a real gateway request
  - verifies request row exists

### Frontend tests

- ~~Ensure CI runs `npm test`~~ *(done; CI runs frontend tests and build).*
- ESLint still needs to be installed before a lint CI step can be added (owner action).
- Keep UI tests focused on “API client does not send identities/roles” and correct rendering of ProblemDetails.

## Contract tests

- `POST /v1/chat/completions` response shape invariants (especially around streaming chunk structure and `X-Conexus-Request-Id` header).

## Load / resilience tests (deferred)

- Gateway saturation behavior under strict limits.
- Provider outage/failover behavior under load.

