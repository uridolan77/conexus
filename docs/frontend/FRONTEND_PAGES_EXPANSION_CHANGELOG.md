# Frontend Pages Expansion Changelog (BO)

Changelog for the BO frontend pages expansion work described in `docs/frontend/FRONTEND_MISSING_BO_PAGES.md`.

## Added pages

- `/playground`: non-streaming chat completion request UI (project API key auth)
- `/activity`: audit log explorer with filters + detail drawer
- `/health`: `/health` + `/readyz` diagnostics, refresh + copy JSON
- `/settings`: operational summary (frontend-known values + assumptions)
- `/adapter-profiles`: adapter profile registry explorer (read-only)
- `/limits`: limits landing page with navigation links

## Updated pages

- `/requests`: request explorer now uses domain module helpers and a detail drawer; safer display (no full secrets)
- `/usage`: uses `MetricCard` and consistent formatters; handles null/empty values
- `/routing`: uses domain helpers; shows doc warning banner when candidates are missing or fallbacks are active

## Aliases

- `/smoke-tests` redirects to `/playground`
- `/audit` redirects to `/activity`

## Frontend modules added/updated

- `frontend/lib/useAdminResource.ts` (hook)
- `frontend/lib/admin/playground.ts`
- `frontend/lib/admin/requests.ts` (expanded filters)
- `frontend/lib/admin/audit.ts` (expanded filters)
- `frontend/lib/admin/usage.ts` (usage endpoints)
- `frontend/lib/admin/routing.ts` (policy + candidates)
- `frontend/lib/admin/adapterProfiles.ts` (registry endpoints)
- `frontend/lib/api.ts` (path guard hardening; `requestAdminJson` extraction)
- `frontend/lib/navigation.ts` (nav entries added after routes existed)
- `frontend/lib/types.ts` (adapter registry types)

## Backend changes (supporting BO)

- Added read-only adapter profiles registry endpoints:
  - `GET /admin/adapter-profiles`
  - `GET /admin/adapter-profiles/{gateway_profile_id}`
  - `GET /admin/adapter-profiles/{gateway_profile_id}/activations`
  - Adapter profile metadata is redacted server-side (`_redact_metadata`) before the response is returned.

## Follow-up hardening

- `frontend/lib/redaction.ts`: client-side metadata redaction applied by Activity and Adapter Profiles pages before rendering metadata JSON. Redaction is defense-in-depth — not a license to render secrets carelessly.
- `backend/_redact_metadata`: server-side metadata redaction applied before adapter profile data is returned by the registry API.
- Requests page: project-loading logic cleaned up to avoid unnecessary fetches on mount.
- Playground: parser and test utilities extracted from the page component for testability.

## Tests added/updated

- Added page tests for:
  - Playground, Activity, Health, Routing, Adapter Profiles, Limits
- Added unit tests for:
  - admin API path safety
  - query building for admin requests/audit
  - playground payload builder
  - `useAdminResource`
- Updated existing tests for:
  - Requests, Usage, CopyButton

## Validation results

- Frontend tests: 213 passed, 0 failed.
- Frontend build: clean, 23 routes.
- Backend tests: 296 passed, 0 failed.
- Linter (`ruff`): clean.

## Manual sanity checklist

- [ ] UX tightening reviewed for tables, drawers, empty states, route clarity, and responsive behavior.

