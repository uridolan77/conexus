# Conexus BO Pages Expansion — Controlled Implementation Plan

You are working in the `conexus` repository.

Goal: add the missing operational BO pages using the now-hardened frontend foundation.

This frontend is intended to become a reusable BO/admin foundation for Conexus and future back offices. Keep the implementation clean, typed, testable, and consistent with the documented BO conventions.

---

## Current frontend foundation

The frontend already has:

- Next.js App Router
- TypeScript strict mode
- Vanilla CSS design tokens
- grouped sidebar navigation via `frontend/lib/navigation.ts`
- typed admin API helpers in `frontend/lib/api.ts`
- `buildQuery`
- `AdminResult<T>`
- `parseApiError`
- `useAdminResource`
- formatter utilities in `frontend/lib/format.ts`
- domain modules under `frontend/lib/admin/`
- shared UI primitives in `frontend/components/ui/index.tsx`
- decomposed Projects components under `frontend/components/projects/`
- BO conventions in `docs/frontend/BO_FRONTEND_CONVENTIONS.md`

Use those foundations. Do not bypass them.

---

## Hard constraints

Do not violate these:

1. Do not redesign the app.
2. Do not introduce Tailwind, shadcn/ui, MUI, Radix, React Query, SWR, or any large dependency.
3. Do not expose secrets.
4. Do not store project API keys in `localStorage`, `sessionStorage`, cookies, query strings, logs, or persistent component state beyond the current in-memory form state.
5. Do not show raw provider keys.
6. Do not show internal API keys.
7. Do not call `/internal/*` endpoints directly from the browser.
8. Do not show prompts/responses unless the backend explicitly returns them and it is safe.
9. Do not weaken TypeScript strictness.
10. Do not run or enforce `npm run lint`; ESLint is not configured yet.
11. Preserve all existing pages and behaviors.
12. Keep each phase small and reviewable.

---

## Required validation

From `frontend/` after each phase:

```bash
npm test -- --run
npm run build
````

If backend endpoints are added:

```bash
cd backend
python -m pytest
python -m ruff check app tests
```

Do not run `npm run lint`.

---

# Implementation strategy

Do not implement all pages in one uncontrolled pass.

Use this order:

1. Phase 0 — tiny API safety fix
2. Phase 1 — Playground + Smoke Test alias
3. Phase 2 — Requests Explorer hardening
4. Phase 3 — Activity / Audit
5. Phase 4 — Usage
6. Phase 5 — Health + Settings
7. Phase 6 — Routing
8. Phase 7 — Adapter Profiles registry
9. Phase 8 — Limits landing page
10. Phase 9 — docs + final sanity checklist

If this prompt is run in Cursor as one agent task, complete **Phase 0 and Phase 1 only**, then stop and report. Continue later phase-by-phase after review.

---

# Phase 0 — Tiny API safety correction

Before adding pages, tighten the admin API helper.

## Files

* `frontend/lib/api.ts`
* relevant tests under `frontend/test/lib/`

## Required changes

### 0.1 Reject paths without leading slash

Current API helpers reject absolute `http(s)://` URLs. Also reject relative paths that do not start with `/`.

Invalid:

```ts
getAdminJson("admin/projects")
```

Valid:

```ts
getAdminJson("/admin/projects")
```

Expected behavior:

* returns `{ ok: false }`
* does not call `fetch`
* error message is clear
* error message does not contain secrets

Suggested behavior:

```ts
if (!path.startsWith("/")) {
  return {
    ok: false,
    error: {
      message: "Invalid path: admin API paths must start with '/'.",
      status: 0,
    },
  };
}
```

Keep the existing absolute URL rejection.

### 0.2 Optional: expose public `requestAdminJson`

If low-risk, add:

```ts
requestAdminJson<T>({
  method,
  path,
  body,
  signal,
})
```

Use it internally for `getAdminJson`, `postAdminJson`, `putAdminJson`, and `deleteAdminJson`.

This helps future pages that need `PATCH` or non-standard methods.

Do not break existing helper signatures.

## Tests

Add/update tests for:

* `/admin/projects` accepted
* `admin/projects` rejected
* `http://example.com/admin/projects` rejected
* rejected paths do not call `fetch`
* `buildQuery` behavior remains unchanged
* empty 204/empty body handling remains valid

---

# Shared page conventions

Every new BO page must follow this shape:

```tsx
<PageHeader
  eyebrow="..."
  title="..."
  description="..."
  actions={<RefreshButton onClick={reload} loading={loading} />}
/>

{pageError && <ErrorState message={pageError} />}

<Card>
  <SectionHeader title="..." description="..." />
  <PageState
    loading={loading}
    error={sectionError}
    empty={rows.length === 0}
    emptyTitle="..."
    emptyBody="..."
  >
    ...
  </PageState>
</Card>
```

Use:

* `useAdminResource` for new read-heavy pages
* `AdminResult<T>` for all admin API calls
* domain modules under `frontend/lib/admin/*`
* `buildQuery` for query strings
* `formatDateTime`
* `formatCost`
* `formatPercentRatio`
* `formatPercentValue`
* `formatTokens`
* `formatLatency`
* `formatNullable`
* `formatDurationSeconds`
* `PageState`
* `Toolbar`
* `FilterBar`
* `RefreshButton`
* `DetailDrawer`
* `JsonBlock`
* `InlineCode`
* `CodeChip`
* `CopyableCode`
* `DataTable` only for simple tables

Use normal JSX `<Table>` for complex tables.

---

# Phase 1 — Playground + Smoke Test alias

## Routes

Create:

```text
frontend/app/playground/page.tsx
```

Update or create:

```text
frontend/app/smoke-tests/page.tsx
```

`/smoke-tests` should either redirect to `/playground` or render the same component. Prefer redirect if clean.

## Purpose

Let an operator manually test:

```text
POST /v1/chat/completions
```

This closes the core loop:

```text
create project → issue API key → paste key → send gateway request → inspect request log
```

## Domain module

Create:

```text
frontend/lib/admin/playground.ts
```

But remember: this is not an admin endpoint. The playground sends a gateway request to:

```text
/v1/chat/completions
```

Do not use `adminSessionFetch` for the actual gateway call because gateway auth uses `Authorization: Bearer <project API key>`, not the admin cookie.

Create a small helper like:

```ts
sendPlaygroundChatCompletion({
  apiKey,
  payload,
  signal,
}): Promise<PlaygroundResult>
```

It should:

* call `${BACKEND_BASE}/v1/chat/completions`
* send `Authorization: Bearer ${apiKey}`
* send `Content-Type: application/json`
* parse JSON safely
* capture response status
* capture `X-Conexus-Request-Id` if present
* return a typed result
* never store or log the API key

## Form fields

Required:

* Project API key input, manual paste only
* Model input, default:

```text
conexus-fast
```

* User message textarea, default:

```text
Say hello in one sentence.
```

Optional:

* System message textarea
* Temperature
* Max tokens

Do not implement streaming in this phase unless it is already trivial. If not implemented, show:

```text
Streaming playground mode is not implemented yet. Non-streaming requests are supported.
```

## Payload builder

Create a pure helper, preferably in the same module or separate file:

```ts
buildChatCompletionPayload({
  model,
  systemMessage,
  userMessage,
  temperature,
  maxTokens,
})
```

Rules:

* include system message only when non-empty
* include user message
* include temperature only when valid number
* include max_tokens only when valid positive integer
* trim strings
* never include API key in payload

Example body:

```json
{
  "model": "conexus-fast",
  "messages": [
    { "role": "user", "content": "Say hello in one sentence." }
  ]
}
```

## Result display

On success, show:

* HTTP status
* request ID from `X-Conexus-Request-Id`, if present
* response id
* model
* provider
* fallback_used
* first assistant message content
* usage:

  * prompt tokens
  * completion tokens
  * total tokens
* raw JSON in `<JsonBlock>`

On error, show:

* HTTP status
* request ID if present
* normalized message
* safe raw JSON in `<JsonBlock>` if useful
* troubleshooting hints:

  * check project API key
  * check provider config
  * check model alias
  * check backend logs

## Security

* Do not persist API key in localStorage/sessionStorage.
* Do not include API key in raw JSON debug block.
* Do not include API key in error messages.
* Add “Clear key” button.
* Password-style input is acceptable, but a “show/hide” toggle may be added if simple.
* Do not auto-fill from project key list because plaintext keys are shown once only.

## Tests

Add tests for:

* payload builder omits empty system message
* payload builder includes non-empty system message
* payload builder validates max tokens
* payload builder validates temperature
* no localStorage/sessionStorage usage
* successful response renders request ID and content
* error response renders safe error
* API key is not rendered in error output

## Manual sanity after Phase 1

1. Start Conexus.
2. Login in frontend.
3. Create project.
4. Issue API key.
5. Copy key.
6. Open `/playground`.
7. Paste key.
8. Send request.
9. Confirm success or safe provider failure.
10. Go to Requests page and verify a request row was logged.

Stop after this phase and report.

---

# Phase 2 — Requests Explorer hardening

## Route

```text
frontend/app/requests/page.tsx
```

If it already exists, improve it. Do not rewrite unless needed.

## Domain module

Use or update:

```text
frontend/lib/admin/requests.ts
```

All query params must use `buildQuery`.

## Filters

Support as many as backend already supports:

* status
* project ID
* provider
* requested model
* request ID
* error code
* limit
* offset

Do not fake unsupported filters. If backend does not support one, omit it or document it as a gap.

## Table columns

* created at
* status
* request ID
* project
* requested model
* provider
* served model
* latency
* tokens
* estimated cost
* fallback
* error code

## Detail drawer

Use `DetailDrawer`.

Show:

* request ID
* project ID/name
* API key prefix only
* requested model
* provider/model served
* status
* latency
* prompt/completion/total tokens
* estimated cost
* fallback used
* error code/message
* created/completed timestamps
* gateway profile ID if present
* raw row JSON in `JsonBlock`

Do not show:

* raw prompt
* raw response
* full API key
* provider secret

## Tests

* empty state
* failed request row
* completed request row
* detail drawer opens
* filter query construction
* null token/cost fields do not crash

---

# Phase 3 — Activity / Audit

## Routes

Create:

```text
frontend/app/activity/page.tsx
```

Make `/audit` either:

* redirect to `/activity`, or
* reuse the same component.

Prefer `/activity` as the canonical route and keep `/audit` as compatibility alias.

## Domain module

Use or update:

```text
frontend/lib/admin/audit.ts
```

## Filters

* action
* actor
* resource type
* resource ID
* limit
* offset

## Table columns

* created at
* actor
* action
* resource type
* resource ID
* metadata summary

## Detail drawer

Show:

* event ID
* actor
* action
* resource type
* resource ID
* created at
* full metadata JSON

Do not show secrets from metadata if present. If metadata may contain secrets, redact obvious keys:

```text
api_key
apikey
token
secret
password
authorization
```

## Tests

* empty state
* row rendering
* drawer opens
* metadata JSON renders
* obvious secret-like metadata keys are redacted if redaction is implemented

---

# Phase 4 — Usage

## Route

```text
frontend/app/usage/page.tsx
```

## Domain module

Use or update:

```text
frontend/lib/admin/usage.ts
```

## Controls

Window selector:

* `24h`
* `7d`
* `30d`

## Summary cards

Use `MetricCard`.

Show:

* total requests
* completed requests
* failed requests
* success rate using `formatPercentRatio`
* fallback rate using `formatPercentRatio`
* prompt tokens
* completion tokens
* total tokens
* estimated cost
* average latency

## Breakdowns

Add sections if backend endpoints exist:

* by project
* by provider
* timeseries

Do not fake missing data.

## Important behavior

* empty DB should render cleanly
* null token/cost fields should render `"—"`
* streaming rows may have null tokens/cost; do not assume usage is present

## Tests

* empty usage
* ratio formatting
* null cost/token handling
* window selector triggers reload

---

# Phase 5 — Health + Settings

## Health route

```text
frontend/app/health/page.tsx
```

Calls:

* `/health`
* `/readyz`

These are not admin-cookie endpoints. Use normal fetch.

Show:

* backend base URL
* environment label
* health status
* readiness status
* last checked time
* raw JSON collapsible
* copy diagnostics JSON

Use `RefreshButton`.

Tests:

* healthy state
* failed readiness state
* raw JSON shown

## Settings route

```text
frontend/app/settings/page.tsx
```

Purpose:

Read-only operational config summary.

Show only safe frontend-known values:

* `BACKEND_BASE`
* environment label
* auth/session model description
* frontend version if available
* known frontend assumptions

If backend safe config endpoint exists, use it. If not, show:

```text
Backend safe config endpoint is not available yet.
```

Do not add a risky config endpoint that could leak secrets.

If adding backend endpoint, it must return only booleans/statuses like:

* provider config present/missing
* adapter registry enabled/disabled
* observability enabled/disabled
* canary routing enabled/disabled

Never return actual secret values.

---

# Phase 6 — Routing

## Route

```text
frontend/app/routing/page.tsx
```

## Domain module

Use or update:

```text
frontend/lib/admin/routing.ts
```

## Show

If backend exposes routing policy:

* default alias
* alias table:

  * alias
  * primary provider
  * primary model
  * fallback provider
  * fallback model

If provider candidates endpoint exists:

* provider
* source:

  * BO config
  * env
* active status
* label
* key mask
* last test status
* last tested at

Show warning if relevant:

```text
BO provider configs may not fully drive runtime provider selection yet. Verify backend wiring before production.
```

Tests:

* policy table renders
* provider candidates render
* warning renders when data is missing or runtime wiring is unclear

---

# Phase 7 — Adapter Profiles registry

## Route

```text
frontend/app/adapter-profiles/page.tsx
```

## Purpose

Read-only Conexus-side gateway adapter profile registry.

This is not the adaptation service profile page. It shows gateway registry state stored in Conexus.

## Backend rule

Do not call `/internal/*` from the browser.

First inspect backend:

* If admin read-only endpoints already exist, use them.
* If missing, add small read-only admin endpoints only:

  * `GET /admin/adapter-profiles`
  * `GET /admin/adapter-profiles/{gateway_profile_id}`
  * `GET /admin/adapter-profiles/{gateway_profile_id}/activations`

These endpoints must:

* require admin session
* be read-only
* not expose secrets
* not mutate lifecycle state
* not call adaptation service
* not imply live traffic routing

## Domain module

Create:

```text
frontend/lib/admin/adapterProfiles.ts
```

## Types

Add safe types to `frontend/lib/types.ts`:

* `GatewayAdapterProfileRow`
* `GatewayAdapterProfileDetail`
* `GatewayAdapterProfileActivationRow`
* list response if paginated

## Table columns

* gateway profile ID
* adapter profile ID
* domain key
* status
* composite score
* profile version
* evidence hash
* semantic context hash
* SLOD model version
* created at

## Detail drawer

Show:

* all profile fields
* metadata JSON
* activation history

## Required warning banner

Show this exact warning:

```text
Adapter profile registration is supported. Canary, promote, rollback, and traffic splitting may still be staged depending on backend configuration. This page shows gateway registry state, not guaranteed live traffic behavior.
```

## Tests

Frontend:

* warning banner renders
* table renders registered row
* drawer renders metadata
* activation history renders

Backend, if endpoints added:

* admin auth required
* list endpoint returns rows
* detail endpoint returns one row
* activations endpoint returns activation history
* no mutation happens

---

# Phase 8 — Limits landing page

## Route

```text
frontend/app/limits/page.tsx
```

## Purpose

Central landing page for limit and reservation operations.

Projects page already handles per-project limits. So `/limits` should not duplicate everything unless backend has cross-project endpoints.

Show:

* explanation of limit modes:

  * disabled
  * soft
  * hard
* link to Projects page
* project selector if easy
* selected project’s current limits if reusable
* stale reservations link/tooling if already exists

Do not add destructive repair actions without confirmation.

Tests:

* page renders
* links to Projects
* empty state works

---

# Navigation updates

Update `frontend/lib/navigation.ts` only after routes exist.

Add:

* `/playground` under Operations or Routing
* `/activity` under Operations
* `/health` under System
* `/settings` under System
* `/adapter-profiles` under Routing or Operations
* `/limits` under Operations

Keep `/audit` and `/smoke-tests` as aliases if already exposed.

Avoid navigation links to 404 pages.

---

# Domain modules

Create/update only as needed:

```text
frontend/lib/admin/playground.ts
frontend/lib/admin/requests.ts
frontend/lib/admin/audit.ts
frontend/lib/admin/usage.ts
frontend/lib/admin/health.ts
frontend/lib/admin/routing.ts
frontend/lib/admin/adapterProfiles.ts
frontend/lib/admin/settings.ts
```

Rules:

* thin wrappers only
* no UI logic
* all admin endpoints return `AdminResult<T>`
* all query params use `buildQuery`
* no unsupported endpoints
* no secrets

---

# Types

Update `frontend/lib/types.ts` only with safe response types.

Add types for:

* playground result
* health/readiness
* request list/detail if missing
* audit list/detail if missing
* usage summaries if missing
* adapter registry rows
* settings/config summary if safe endpoint exists

Do not weaken strict TypeScript.

---

# Documentation

Create/update:

```text
docs/frontend/FRONTEND_PAGES_EXPANSION_REVIEW.md
docs/frontend/FRONTEND_PAGES_EXPANSION_CHANGELOG.md
docs/frontend/BO_FRONTEND_CONVENTIONS.md
```

Include:

* pages added
* endpoints used
* backend endpoints added, if any
* placeholders/gaps
* security notes
* manual sanity checklist
* remaining limitations

Manual sanity checklist:

```text
[ ] Login works.
[ ] Create project.
[ ] Issue project API key.
[ ] Open Playground.
[ ] Paste API key.
[ ] Send request.
[ ] Request succeeds or fails safely.
[ ] Requests page shows the row.
[ ] Usage page loads and handles null/empty values.
[ ] Activity page shows login/project/key events.
[ ] Health page shows /health and /readyz.
[ ] Routing page loads.
[ ] Adapter Profiles page shows manual internal registration row if present.
[ ] No full secrets are displayed.
```

---

# Final validation

Frontend:

```bash
cd frontend
npm test -- --run
npm run build
```

Backend, only if backend endpoints were added:

```bash
cd backend
python -m pytest
python -m ruff check app tests
```

Do not run `npm run lint`.

---

# Final response format

When done, report:

1. Phases completed.
2. Pages added/changed.
3. Components reused.
4. Domain modules added/changed.
5. Backend endpoints added, if any.
6. Security constraints preserved.
7. Tests added/updated.
8. Exact validation results.
9. Manual sanity checklist status.
10. Remaining gaps.
11. Recommended next phase.
