Missing BO pages after foundation fixes


You are working in the `conexus` repository.

Goal: add the missing operational BO pages using the frontend foundation that now exists.

Do this only after the foundation correction pass is complete and both commands pass:
- `npm test -- --run`
- `npm run build`

Important constraints:
- Do not redesign the whole app.
- Do not introduce a large UI framework.
- Reuse existing components:
  - `PageHeader`
  - `Card`
  - `SectionHeader`
  - `PageState`
  - `Toolbar`
  - `FilterBar`
  - `RefreshButton`
  - `DataTable` only if it remains simple
  - `DetailDrawer`
  - `JsonBlock`
  - `InlineCode`
  - `CopyableCode`
  - `MetricCard`
- Use `frontend/lib/admin/*` domain API modules where available.
- Add new domain API modules only when needed.
- Do not expose secrets.
- Do not store project API keys in localStorage.
- Do not show raw provider keys.
- Do not show prompts/responses unless the backend explicitly returns them and it is safe.
- Do not call `/internal/*` endpoints directly from the browser.
- If a backend endpoint is missing, add a small read-only `/admin/*` endpoint only when safe. Otherwise create a clear placeholder and document the gap.
- Keep tests/build passing.

Pages to implement or complete:

1. `/playground`
2. `/smoke-tests` alias or redirect to `/playground`
3. `/requests` improvement if already present
4. `/activity`
5. `/audit` alias or existing page alignment with `/activity`
6. `/usage` improvement if already present
7. `/health`
8. `/settings`
9. `/adapter-profiles`
10. `/routing` improvement if already present
11. `/limits` if not already covered sufficiently by project detail/Projects page

Implementation order:

---

## Phase 1 — Playground / Smoke Test

Route:
- `frontend/app/playground/page.tsx`
- `frontend/app/smoke-tests/page.tsx` should either redirect to `/playground` or render the same component.

Purpose:
Let the operator test `POST /v1/chat/completions`.

Fields:
- API key input, manual paste only for now.
- Model input, default `conexus-fast`.
- System message textarea, optional.
- User message textarea, default `Say hello in one sentence.`
- Temperature input, default optional.
- Max tokens input, optional.
- Stream toggle optional. If streaming is hard, document as not implemented yet.

Request:
- POST `${BACKEND_BASE}/v1/chat/completions`
- Header: `Authorization: Bearer <manual key>`
- Body:
```json
{
  "model": "conexus-fast",
  "messages": [
    { "role": "user", "content": "Say hello in one sentence." }
  ]
}

Show result:

HTTP status
X-Conexus-Request-Id response header if present
model
provider
fallback_used
content
usage
raw JSON collapsible

Show error:

status
normalized message
raw JSON collapsible if safe
request ID if present
hint: “Check provider config and project API key.”

Security:

Do not persist API key in localStorage/sessionStorage.
Provide a “clear key” button.
Never include API key in logs or UI error output.

Tests:

payload builder includes system message only when non-empty.
no localStorage usage.
error state renders.
Phase 2 — Requests Explorer

Route:

frontend/app/requests/page.tsx

Purpose:
Inspect gateway request logs.

If already implemented, harden it to use foundation components and domain API module.

Use or create:

frontend/lib/admin/requests.ts

Required filters:

status
project id/name if supported
provider
requested model
request ID
error code
limit/offset pagination

Table columns:

created at
status
request ID
project
requested model
provider
served model
latency
tokens
cost
fallback
error code

Detail drawer:

request ID
project id/name
API key prefix
requested model
provider/model
status
latency
tokens
estimated cost
fallback used
error code/message
created/completed timestamps
gateway profile ID if available
raw JSON if safe

Do not show:

raw prompt
raw response
full project API key
provider secret

Tests:

empty state
failed request row
detail drawer opens
filters build expected query string where practical
Phase 3 — Activity / Audit

Routes:

frontend/app/activity/page.tsx
frontend/app/audit/page.tsx should redirect to /activity or reuse same component.

Purpose:
Human-readable audit log explorer.

Use or create:

frontend/lib/admin/audit.ts

Filters:

action
actor
resource type
resource ID
limit/offset

Table columns:

created at
actor
action
resource type
resource ID
metadata summary

Detail drawer:

full metadata JSON
copy resource ID
related links if obvious

Important:

Existing direct internal registration should appear as gateway.adapter_profile.registered if backend audit endpoint includes it.
Login/project/key actions should appear.

Tests:

empty state
row rendering
metadata drawer
Phase 4 — Usage

Route:

frontend/app/usage/page.tsx

Purpose:
Show usage/cost rollups.

Use or create:

frontend/lib/admin/usage.ts

Controls:

window selector: 24h, 7d, 30d

Summary cards:

total requests
completed requests
failed requests
success rate using formatPercentRatio
fallback rate using formatPercentRatio
total tokens
prompt tokens
completion tokens
estimated cost
average latency

Breakdown sections:

by project
by provider
timeseries if backend endpoint exists

Important:

Handle null token/cost fields gracefully.
Do not assume streaming rows always have usage.
Do not crash with empty DB.

Tests:

empty usage
ratio formatting
null cost/token handling
Phase 5 — Health

Route:

frontend/app/health/page.tsx

Purpose:
Make backend and frontend operational state obvious.

Calls:

/health
/readyz

Show:

backend base URL
frontend environment label
health status
readiness status
raw JSON collapsible
last checked time

Actions:

Refresh
Copy diagnostics JSON

Tests:

healthy state
failed readiness state
raw JSON shown
Phase 6 — Settings

Route:

frontend/app/settings/page.tsx

Purpose:
Read-only operational config summary.

Do not expose secret values.

Show:

frontend backend base URL
environment label
cookie/session assumptions
known feature flags if backend exposes them
adapter registry configured/enabled if exposed
canary routing status if exposed
provider mode if exposed

If backend does not expose config:

Show what the frontend can know.
Add a “Backend config endpoint not available” info card.
Document backend endpoint gap.

Do not add risky backend config endpoint unless it returns only safe configured/missing booleans.

Phase 7 — Routing

Route:

frontend/app/routing/page.tsx

Purpose:
Explain routing and model alias behavior.

Use or create:

frontend/lib/admin/routing.ts

Show:

routing policy if endpoint exists
provider candidates if endpoint exists
alias table:
alias
primary provider/model
fallback provider/model
provider source:
BO config
env
last test status

If backend runtime still uses env-driven providers:

Show warning:
“BO provider configs may not fully drive runtime provider selection yet. Verify backend wiring before production.”

Tests:

policy table renders
warning renders when relevant data unavailable
Phase 8 — Adapter Profiles registry

Route:

frontend/app/adapter-profiles/page.tsx

Purpose:
Read-only Conexus-side gateway adapter profile registry.

Do not call /internal/* from browser.

First inspect backend:

If admin read-only endpoints already exist, use them.
If not, add small read-only admin endpoints:
GET /admin/adapter-profiles
GET /admin/adapter-profiles/{gateway_profile_id}
GET /admin/adapter-profiles/{gateway_profile_id}/activations
These endpoints must require admin session.
They must not mutate anything.
They must not expose secrets.

Table columns:

gateway profile ID
adapter profile ID
domain key
status
composite score
profile version
evidence hash
semantic context hash
SLOD model version
created at

Detail drawer:

all fields
metadata JSON
activation history

Warning banner:
“Adapter profile registration is supported. Canary, promote, rollback, and traffic splitting may still be staged depending on backend configuration. This page shows gateway registry state, not guaranteed live traffic behavior.”

Tests:

manual registered row renders if API returns it
warning banner renders
detail drawer renders metadata
Phase 9 — Limits page

Route:

frontend/app/limits/page.tsx

Purpose:
Consolidated limits/reservation view across projects.

If Projects page already handles enough of this:

Make /limits a landing page that links to Projects limit cards and stale reservations.
Add only safe cross-project summary if backend supports it.

Show:

project selector
current project limits
current reservation counters
stale reservation summary
link to repair tools if existing

Do not add destructive actions without confirmation.

Domain API modules

Create/update as needed:

frontend/lib/admin/playground.ts
frontend/lib/admin/requests.ts
frontend/lib/admin/audit.ts
frontend/lib/admin/usage.ts
frontend/lib/admin/health.ts
frontend/lib/admin/routing.ts
frontend/lib/admin/adapterProfiles.ts
frontend/lib/admin/settings.ts

Keep them thin:

URL construction
typed result
no UI logic
Types

Update frontend/lib/types.ts only with safe response types.

Add types for:

playground response if needed
health/readiness
adapter profile registry rows
activation rows
settings/config summary if endpoint exists

Do not weaken strict TypeScript.

UI/UX requirements

All pages must have:

PageHeader
loading state
empty state
error state
refresh action where useful
no crash on empty DB
no crash on backend 401; adminSessionFetch redirect handles it
no secret leakage

Use:

formatDateTime
formatCost
formatPercentRatio
formatTokens
formatLatency
formatNullable
Documentation

Create/update:

docs/frontend/FRONTEND_PAGES_EXPANSION_REVIEW.md
docs/frontend/FRONTEND_PAGES_EXPANSION_CHANGELOG.md

Include:

pages added
endpoints used
backend endpoints added, if any
placeholders/gaps
manual sanity checklist
known limitations
security notes

Manual sanity checklist:

Login.
Create project.
Issue API key.
Open Playground.
Paste API key.
Send request.
Check Requests page shows row.
Check Usage page updates or safely shows null/empty.
Check Activity page shows login/project/key actions.
Check Health page.
Check Adapter Profiles page shows manual internal registration row if present.
Validation

From frontend/:

npm test -- --run
npm run build

If backend endpoints are added:
From backend/:

python -m pytest
python -m ruff check app tests

Do not run npm run lint; ESLint is not configured.

Final response:

Pages added/changed.
Components reused.
Domain modules added/changed.
Backend endpoints added, if any.
Security constraints preserved.
Tests added.
Exact validation results.
Remaining gaps and recommended next step.

-