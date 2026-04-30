# Conexus — Test Gap Analysis

Last updated: 2026-04-30

## Current coverage impression

- **Backend**: has pytest + ruff, runs in CI. Core gateway + admin endpoints appear testable, and many components already isolate dependencies (e.g. provider factory override).
- **Frontend**: has Vitest configured and `npm test` script, but CI currently does not run frontend tests.
- **Integration**: docker-compose provides a realistic local stack, but there is no automated smoke/integration suite in CI.

## High-risk areas needing stronger tests

### Gateway streaming edge cases

- **Missing tests**
  - Stream interruption: provider stops mid-stream or raises; ensure request log becomes `failed` and reservation reconciles.
  - Stream timeout: per-chunk timeout yields correct error classification and cleanup.
  - Stream “usage not emitted”: ensure logging path behaves predictably (cost/tokens null vs 0).

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

- `backend/tests/test_gateway_stream_logging.py`
  - fake provider that yields a few chunks then raises; assert DB request row status and error code
- `backend/tests/test_internal_adapter_profile_register_race.py`
  - simulate IntegrityError path and ensure stable outcome

### Backend integration smoke (local-only)

- A lightweight script (or pytest marked integration) that:
  - boots docker-compose
  - runs `/health`, logs in admin, creates a project+key, does a real gateway request
  - verifies request row exists

### Frontend tests

- Ensure CI runs `npm test`.
- Keep UI tests focused on “API client does not send identities/roles” and correct rendering of ProblemDetails.

## Contract tests

- `POST /v1/chat/completions` response shape invariants (especially around streaming chunk structure and `X-Conexus-Request-Id` header).

## Load / resilience tests (deferred)

- Gateway saturation behavior under strict limits.
- Provider outage/failover behavior under load.

