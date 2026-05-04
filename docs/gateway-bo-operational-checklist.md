# Gateway to BO Operational Checklist

Use this checklist when validating that a real gateway call is visible in the
back office.

## Production Startup Expectations

- Run Alembic migrations before starting the backend.
- Set `ALLOW_CREATE_ALL=false` in production so startup does not mutate schema.
- Configure a valid Fernet `ENCRYPTION_KEY`; readiness fails when it is invalid.
- Replace default `AUTH_SECRET` and `ADMIN_PASSWORD`.
- Set explicit `CORS_ALLOWED_ORIGINS` for the BO origin; production must not use `*`.
- If adapter profile registry endpoints are enabled, set and protect
  `INTERNAL_ADAPTER_API_KEY` and keep `/internal/*` behind trusted-network access.

## Request Visibility Smoke

1. Start backend and frontend against the migrated database.
2. Confirm `/health` and `/health/ready` are healthy.
3. Log into the BO.
4. Add or verify an active provider credential.
5. Create a project and issue a project API key.
6. Call `POST /v1/chat/completions` with the project key.
7. Confirm the response includes `X-Conexus-Request-Id`.
8. Open the BO dashboard and check today request counts/latest errors.
9. Open Requests, filter by the request id, and confirm provider/model/status,
   latency, tokens, cost, fallback, and error fields are visible.

## Current Intentional Limits

- BO-managed provider configs are stored and testable, but runtime provider
  selection still uses the configured process provider/env credentials.
- Caller-supplied correlation ids are not persisted yet; Conexus always mints
  and returns its own request id.
- Strict limit serialization has process-local protection plus DB reservation
  rows, but no distributed lock.
- Metrics/tracing are deferred; request visibility is currently DB/log based.
