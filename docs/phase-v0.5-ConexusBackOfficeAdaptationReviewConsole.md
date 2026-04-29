Goal: implement the Conexus Back Office Adaptation Review Console, using the existing Conexus backend proxy endpoints.

Important:
- Work only in the `conexus` respo.
- Do not modify `conexus.adaptation`.
- Do not call `conexus.adaptation` directly from the browser.
- Browser must call same-origin Conexus backend proxy endpoints under `/admin/adaptation/*`.
- Do not add publishing/canary/rollback UI yet.
- Do not add adapter-profile activation.
- Do not add KGB/SLOD UI.
- Do not add retry/cancel/resume UI.

Current backend context:
- Conexus already has `/admin/adaptation/*` proxy endpoints.
- Conexus core hardening is done:
  - provider timeouts
  - YAML model aliases
  - login rate limiting
  - audit logging
  - `/admin/routing/model-aliases`
- `conexus.adaptation` now exposes:
  - `GET /adaptation-plans`
  - `GET /adaptation-plans/{id}`
  - `GET /adaptation-plans/{id}/runs`
  - `POST /adaptation-plans/{id}/approve`
  - `POST /adaptation-plans/{id}/run`
  - `GET /adaptation-runs`
  - `GET /adaptation-runs/{id}`
  - `GET /adaptation-runs/{id}/manifest`
  - `GET /adaptation-runs/{id}/adapter-profile`
  - `GET /adapter-profiles`
  - `GET /adapter-profiles/{id}`

Use the Conexus proxy equivalent routes. If the proxy route names differ, inspect `backend/app/api/admin_adaptation.py` and follow the existing mapping.

## Implementation status (Conexus repo)

The Adaptation Review Console described in this document is **implemented** in this repository:

| Area | Location |
|------|----------|
| Admin proxy | `backend/app/api/admin_adaptation.py` |
| Proxy tests | `backend/tests/test_admin_adaptation_proxy.py` |
| Typed DTOs + normalization | `frontend/lib/adaptationTypes.ts`, `frontend/lib/adaptationNormalize.ts` |
| API client | `frontend/lib/adaptationApi.ts` |
| ProblemDetails UI | `frontend/components/adaptation/ProblemAlert.tsx` |
| Shared adaptation UI | `frontend/components/adaptation/CopyableId.tsx`, `ScoreBadge.tsx` |
| BO routes | `frontend/app/adaptation/plans/`, `runs/`, `profiles/` |
| Sidebar links | `frontend/components/bo/Sidebar.tsx` |
| Frontend tests | `frontend/test/adaptation.test.tsx` |

The client uses `BACKEND_BASE` / same-origin rules from `frontend/lib/api.ts` (relative `/admin/adaptation/*` when the BO origin matches the API origin). Approve/run POST bodies are `{}` from the browser; the proxy injects temporary identity per `_temporary_identity()` in `admin_adaptation.py`.

### Remaining / out of scope for this doc

- **Production identity**: replace hardcoded `admin-user` / roles with authenticated BO admin when product-ready (TODO in proxy code).
- **Not in scope**: publish, activate, canary, rollback, retry/cancel/resume, KGB/SLOD (see Constraints below).

============================================================
PHASE 1 — Adaptation API client
============================================================

Add a frontend API client module for the BO.

Suggested file:
- `frontend/lib/adaptationApi.ts`

Methods:
- `listPlans(params)`
- `getPlan(id)`
- `approvePlan(id)`
- `startRun(planId)`
- `listRuns(params)`
- `getRun(id)`
- `getRunManifest(id)`
- `getProfileByRunId(runId)`
- `listRunsForPlan(planId)`
- `listProfiles(params)`
- `getProfile(id)`

Rules:
- Use relative same-origin URLs:
  - `/admin/adaptation/plans`
  - `/admin/adaptation/runs`
  - `/admin/adaptation/profiles`
- Include credentials if existing BO client pattern requires it.
- Reuse existing fetch/API conventions in the frontend.
- Surface ProblemDetails-style errors:
  - title
  - detail
  - status
  - traceId if present
- Keep types close to backend DTOs.

Add TypeScript types:
- `AdaptationPlanListItem`
- `AdaptationPlan`
- `AdaptationRunListItem`
- `AdaptationRun`
- `AdaptationRunManifest`
- `AdapterProfileListItem`
- `AdapterProfile`
- `EvaluationMetric`
- `EvaluationGateResult`
- `PlanningReason`
- `AdaptationRunStep`

============================================================
PHASE 2 — Navigation
============================================================

Add a BO navigation section:

Adaptation
- Plans
- Runs
- Profiles

Routes:
- `/adaptation/plans`
- `/adaptation/plans/[id]`
- `/adaptation/runs`
- `/adaptation/runs/[id]`
- `/adaptation/profiles`
- `/adaptation/profiles/[id]`

Follow the current Next.js/App Router structure in the repo.

Do not break existing BO pages.

============================================================
PHASE 3 — Plans list page
============================================================

Route:
- `/adaptation/plans`

Features:
- Fetch `GET /admin/adaptation/plans`
- Render table columns:
  - CreatedAt
  - DomainKey
  - TaskDescription
  - RecommendedStrategy
  - RecipeKey
  - Status
  - RequiresHumanApproval
  - CreatedByUserId

Filters:
- domainKey
- status
- strategy
- requiresHumanApproval

Actions:
- View
- Approve when status is `Draft`
- Start Run when status is `Approved`

UX:
- Use status badges.
- Highlight `RequiresHumanApproval`.
- Truncate long task descriptions.
- Show loading state.
- Show empty state.
- Show API error state.

============================================================
PHASE 4 — Plan detail page
============================================================

Route:
- `/adaptation/plans/[id]`

Fetch:
- `GET /admin/adaptation/plans/{id}`
- `GET /admin/adaptation/plans/{id}/runs`

Sections:
- Summary
- Constraints
- Quality Targets
- Data Sources
- Planner Decision
- Avoided Strategies
- Planning Reasons
- Approval State
- Runs for this Plan

Actions:
- Approve
- Start Run
- Open latest run

Approve behavior:
- Call `POST /admin/adaptation/plans/{id}/approve`
- Backend proxy should inject temporary admin identity/roles if implemented there.
- If frontend must send a body, use current temporary values:
  - approvedByUserId: "admin-user"
  - approverRoles: ["ComplianceReviewer"]

Start run behavior:
- Call `POST /admin/adaptation/plans/{id}/run`
- If frontend must send a body, use:
  - createdByUserId: "admin-user"
- On success, navigate to `/adaptation/runs/{runId}`.

Add TODO comment:
- Replace temporary user values with authenticated BO admin identity when available.

============================================================
PHASE 5 — Runs list page
============================================================

Route:
- `/adaptation/runs`

Fetch:
- `GET /admin/adaptation/runs`

Columns:
- CreatedAt
- DomainKey
- PlanId
- RecipeKey
- Status
- StepCount
- StartedAt
- CompletedAt
- FailedAt

Filters:
- domainKey
- status
- planId
- recipeKey

Actions:
- View Run
- View Manifest
- View Adapter Profile if available

UX:
- Failed runs should be visually distinct.
- Completed runs should link to profile when profile exists.
- Missing profile should show “No profile produced”.

============================================================
PHASE 6 — Run detail page
============================================================

Route:
- `/adaptation/runs/[id]`

Fetch:
- `GET /admin/adaptation/runs/{id}`
- `GET /admin/adaptation/runs/{id}/manifest`
- `GET /admin/adaptation/runs/{id}/adapter-profile`

Sections:
- Run Summary
- Step Timeline/Table
- Manifest Summary
- Adapter Profile Link

Step table columns:
- StepKey
- ExecutorKey
- Status
- StartedAt
- CompletedAt
- ErrorCode
- ErrorMessage

Manifest summary:
- RunnerVersion
- PlannerVersion
- CorpusSnapshotId
- IndexManifestId
- Step output hashes

If profile endpoint returns 404:
- Show “No adapter profile produced yet.”
- Do not treat as page failure.

============================================================
PHASE 7 — Adapter profiles list page
============================================================

Route:
- `/adaptation/profiles`

Fetch:
- `GET /admin/adaptation/profiles`

Columns:
- CreatedAt
- DomainKey
- Status
- ApprovedForRuntime
- CompositeScore
- ModelProfile
- PromptProfile
- RetrievalProfile
- SafetyProfile

Filters:
- domainKey
- status
- approvedForRuntime
- planId
- runId

Actions:
- View Profile
- Open Run
- Open Plan

UX:
- `ApprovedForRuntime = true` should be clearly marked.
- Profiles with failed blocking gates should be visually marked.
- Do not add publish/activate buttons yet.

============================================================
PHASE 8 — Adapter profile detail page
============================================================

Route:
- `/adaptation/profiles/[id]`

Fetch:
- `GET /admin/adaptation/profiles/{id}`

Sections:
- Profile Summary
- Composite Score
- Metrics
- Gate Results
- Runtime Profile Keys
- Links to Plan and Run

Profile summary:
- ProfileId
- PlanId
- RunId
- DomainKey
- Status
- ApprovedForRuntime
- CompositeScore
- CreatedAt
- EvaluatedAt
- ApprovedAt

Runtime profile keys:
- ModelProfile
- PromptProfile
- RetrievalProfile
- SafetyProfile
- ToolProfile if present

Metrics table:
- Metric Key
- Value
- Threshold
- Passed

Gate results table:
- Gate Key
- Blocking
- Passed
- Message

UX:
- Failed blocking gates should be highlighted strongly.
- Non-blocking failures should be visible but less severe.
- Keep exact metric/gate keys visible.
- Raw IDs should be copyable.

============================================================
PHASE 9 — Shared UI components
============================================================

Add or reuse components:

- StatusBadge
- BooleanBadge
- ScoreBadge
- ProblemAlert
- EmptyState
- LoadingState
- CopyableId
- MetricTable
- GateResultTable
- PlanningReasonTable
- StepTimelineTable

Do not overbuild charts yet. Tables and badges are enough.

============================================================
PHASE 10 — Tests
============================================================

Add frontend tests according to existing test style.

Minimum:
- AdaptationPlansList renders rows from mocked API.
- AdaptationPlanDetail renders planning reasons.
- Approve action calls correct endpoint.
- StartRun action calls correct endpoint and navigates to run page.
- AdaptationRunsList renders run statuses.
- AdaptationRunDetail renders step table.
- RunDetail handles missing adapter profile 404 gracefully.
- AdapterProfilesList renders composite score and status.
- AdapterProfileDetail highlights failed blocking gate.
- API client surfaces ProblemDetails detail.

If frontend test setup makes some interaction tests expensive, add the core rendering/API-client tests and report the limitation.

============================================================
PHASE 11 — Backend proxy tests if missing
============================================================

Inspect existing backend tests for `admin_adaptation`.

If missing, add tests for:
- `/admin/adaptation/plans` requires admin session
- list query params are forwarded
- upstream 400 ProblemDetails body is preserved
- upstream 404 ProblemDetails body is preserved
- missing `ADAPTATION_API_BASE_URL` returns 503
- upstream connection error returns 502
- upstream timeout returns 504
- approve endpoint sends temporary identity payload if proxy injects it
- run endpoint sends temporary createdBy payload if proxy injects it

Use existing test style. Do not over-refactor proxy code unless necessary.

============================================================
Constraints
============================================================

Do not implement:
- profile publish
- activate canary
- promote
- rollback
- drift status
- retry/cancel/resume
- KGB/SLOD
- direct browser calls to adaptation service
- new auth system
- new charting library
- major styling overhaul

Do not expose:
- provider API keys
- raw secrets
- adaptation service internal URL in browser

============================================================
Run checks
============================================================

Backend:
```bash
cd backend
pytest -q
ruff check .