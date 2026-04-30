# Frontend Pages Expansion Review (BO)

This document summarizes the BO frontend pages added/updated during the BO pages expansion work described in `docs/frontend/FRONTEND_MISSING_BO_PAGES.md`.

## Pages added/changed

### Added

- `/playground` (`frontend/app/playground/page.tsx`)
- `/activity` (`frontend/app/activity/page.tsx`)
- `/health` (`frontend/app/health/page.tsx`)
- `/settings` (`frontend/app/settings/page.tsx`)
- `/adapter-profiles` (`frontend/app/adapter-profiles/page.tsx`)
- `/limits` (`frontend/app/limits/page.tsx`)

### Aliases / redirects

- `/smoke-tests` → redirects to `/playground` (`frontend/app/smoke-tests/page.tsx`)
- `/audit` → redirects to `/activity` (`frontend/app/audit/page.tsx`)

### Updated / hardened

- `/requests` (`frontend/app/requests/page.tsx`): uses domain module + `buildQuery`, detail moved to `DetailDrawer`
- `/routing` (`frontend/app/routing/page.tsx`): uses domain module helpers and shows wiring warning banner
- `/usage` (`frontend/app/usage/page.tsx`): uses domain module helpers, summary via `MetricCard`

## Endpoints used (frontend)

### Gateway endpoints (project key auth)

- `POST /v1/chat/completions` (Playground)

### Non-admin public endpoints (no cookies)

- `GET /health` (Health page)
- `GET /readyz` (Health page)

### Admin endpoints (cookie session)

- `GET /admin/projects`
- `GET /admin/providers`
- `GET /admin/requests`
- `GET /admin/requests/{request_id}`
- `GET /admin/audit`
- `GET /admin/usage/summary`
- `GET /admin/usage/by-project`
- `GET /admin/usage/by-provider`
- `GET /admin/usage/timeseries`
- `GET /admin/routing/policy`
- `GET /admin/routing/provider-candidates`
- `GET /admin/adapter-profiles` (registry list)
- `GET /admin/adapter-profiles/{gateway_profile_id}` (registry detail)
- `GET /admin/adapter-profiles/{gateway_profile_id}/activations` (activation history)

## Backend endpoints added (if any)

Added a minimal, **read-only** adapter profiles registry API for the BO:

- `backend/app/api/admin_adapter_profiles_registry.py` (new)
- wired in `backend/app/main.py`

Security properties:

- requires admin session
- requires adaptation view permission (`ADAPTATION_VIEW`)
- read-only (no mutations)
- does not call adaptation service
- adapter profile metadata is redacted server-side (`_redact_metadata`) before the response is returned

## Security notes

- Playground **never persists** project API keys (no local/session storage).
- Playground redacts the pasted API key from:
  - error text rendering
  - raw JSON debug output (deep redaction)
- Admin API helpers reject:
  - absolute URLs
  - non-leading-slash paths (prevents accidental relative paths like `admin/projects`)
- BO pages avoid rendering:
  - provider secrets
  - full project API keys (prefix only is shown)
  - raw prompt/response bodies in Requests
- Activity and Adapter Profiles pages apply frontend redaction (`frontend/lib/redaction.ts`) before rendering metadata JSON.
- Redaction is defense-in-depth — it is not a license to render secrets carelessly.

## Follow-up hardening

- `frontend/lib/redaction.ts`: client-side metadata redaction utility applied by Activity and Adapter Profiles pages before rendering.
- `backend/_redact_metadata`: server-side redaction applied before adapter profile metadata is returned by the registry API.
- Requests page: project-loading logic cleaned up to avoid unnecessary project list fetches on mount.
- Playground: parser and test utilities extracted from the page component for testability.

## Validation results

- Frontend tests: 213 passed, 0 failed.
- Frontend build: clean, 23 routes.
- Backend tests: 296 passed, 0 failed.
- Linter (`ruff`): clean.

## Placeholders / gaps

- Backend safe config endpoint for `/settings` is not implemented yet (frontend shows a notice).
- Some domain wrapper modules suggested by the expansion doc (e.g. `frontend/lib/admin/health.ts`, `frontend/lib/admin/settings.ts`) were not created because the current pages do not need them yet.

## Manual sanity checklist

- [ ] Login works.
- [ ] Create project.
- [ ] Issue project API key.
- [ ] Open Playground.
- [ ] Paste API key.
- [ ] Send request.
- [ ] Request succeeds or fails safely.
- [ ] Requests page shows the row.
- [ ] Usage page loads and handles null/empty values.
- [ ] Activity page shows login/project/key events.
- [ ] Health page shows /health and /readyz.
- [ ] Routing page loads.
- [ ] Adapter Profiles page shows manual internal registration row if present.
- [ ] No full secrets are displayed.
- [ ] UX tightening reviewed for tables, drawers, empty states, route clarity, and responsive behavior.

