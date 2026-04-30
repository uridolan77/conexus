# Phase v0.3d — Adaptation Back Office Frontend

## Goal

Add an Adaptation Review Console to the existing Conexus BO frontend.

The BO should let operators browse, review, approve, run, and inspect adaptation workflows produced by `conexus.adaptation`.

This phase connects the Conexus BO to the adaptation service through API calls. It does **not** implement gateway publishing, profile activation, canary deployment, or rollback.

---

## Why this belongs in `conexus`

`conexus` is the gateway and BO product. The BO should be the unified operator console for:

```text
providers
projects
API keys
gateway requests
costs
latency
errors
adaptation plans
adaptation runs
adapter profiles
evaluation results
````

`conexus.adaptation` remains the backend orchestration service. The UI belongs here.

---

## Required backend dependency

This phase assumes `conexus.adaptation` has completed v0.3c and exposes:

```text
GET /adaptation-plans
GET /adaptation-plans/{id}
GET /adaptation-plans/{id}/runs
POST /adaptation-plans/{id}/approve
POST /adaptation-plans/{id}/run

GET /adaptation-runs
GET /adaptation-runs/{id}
GET /adaptation-runs/{id}/manifest
GET /adaptation-runs/{id}/adapter-profile

GET /adapter-profiles
GET /adapter-profiles/{id}
```

---

## Environment configuration

Add adaptation service URLs.

For browser-side calls:

```env
NEXT_PUBLIC_ADAPTATION_API_BASE_URL=http://localhost:5000
```

For server-side calls, if needed:

```env
ADAPTATION_API_BASE_URL=http://conexus-adaptation:5000
```

Use the existing frontend/backend URL conventions in `conexus`.

---

## Scope

### In scope

* Add Adaptation section to BO navigation.
* Add list/detail pages for adaptation plans.
* Add list/detail pages for adaptation runs.
* Add list/detail pages for adapter profiles.
* Add approve action for draft plans.
* Add start-run action for approved plans.
* Add metrics/gates review UI.
* Add loading, error, and empty states.
* Add API client module for adaptation service.

### Out of scope

* No adapter-profile publishing.
* No activation/canary/rollback UI.
* No drift dashboard.
* No real-time run streaming.
* No retry/cancel/resume UI.
* No editing of evaluation policies.
* No corpus upload UI.
* No KGB/SLOD management.

---

## Navigation

Add a top-level or sidebar section:

```text
Adaptation
  Plans
  Runs
  Profiles
```

Routes:

```text
/adaptation/plans
/adaptation/plans/:id
/adaptation/runs
/adaptation/runs/:id
/adaptation/profiles
/adaptation/profiles/:id
```

---

## API client

Create an adaptation API client module.

Suggested file:

```text
frontend/lib/adaptationApi.ts
```

or equivalent based on the repo’s current structure.

Methods:

```ts
listPlans(params)
getPlan(id)
approvePlan(id, body)
startRun(planId, body)

listRuns(params)
getRun(id)
getRunManifest(id)
getProfileByRunId(runId)
listRunsForPlan(planId)

listProfiles(params)
getProfile(id)
```

The client should:

```text
use ADAPTATION_API_BASE_URL / NEXT_PUBLIC_ADAPTATION_API_BASE_URL
handle non-2xx responses consistently
surface ProblemDetails detail/title where available
support query params
```

---

# Screens

## 1. Adaptation Plans List

Route:

```text
/adaptation/plans
```

Purpose:

Show all adaptation plans needing review or inspection.

Columns:

```text
CreatedAt
DomainKey
TaskDescription
RecommendedStrategy
RecipeKey
Status
RequiresHumanApproval
CreatedByUserId
```

Filters:

```text
domainKey
status
strategy
requiresHumanApproval
```

Actions:

```text
View
Approve when status is Draft
Start Run when status is Approved
```

UX notes:

* Use status badges.
* Highlight plans requiring human approval.
* Truncate long task descriptions.
* Preserve raw IDs in a copyable way.

---

## 2. Adaptation Plan Detail

Route:

```text
/adaptation/plans/:id
```

Sections:

```text
Summary
Constraints
Quality Targets
Data Sources
Planner Decision
Avoided Strategies
Planning Reasons
Approval State
Runs for this Plan
```

Actions:

```text
Approve
Start Run
Open Latest Run
```

Show planning reasons as a table:

```text
Severity
Code
Message
```

Show avoided strategies as badges.

Approval panel:

```text
Status
RequiresHumanApproval
ApprovedByUserId
ApprovedAt
RejectedByUserId
RejectedReasonCode
RejectedAt
```

---

## 3. Adaptation Runs List

Route:

```text
/adaptation/runs
```

Columns:

```text
CreatedAt
DomainKey
PlanId
RecipeKey
Status
StepCount
StartedAt
CompletedAt
FailedAt
```

Filters:

```text
domainKey
status
planId
recipeKey
```

Actions:

```text
View Run
View Manifest
View Adapter Profile if exists
```

UX notes:

* Failed runs should be visually distinct.
* Completed runs should link to profile when a profile exists.
* Missing profile should show “No profile produced”.

---

## 4. Adaptation Run Detail

Route:

```text
/adaptation/runs/:id
```

Sections:

```text
Run Summary
Step Timeline
Manifest Summary
Adapter Profile Link
```

Run summary fields:

```text
RunId
PlanId
DomainKey
RecipeKey
RecipeVersion
Status
CreatedAt
StartedAt
CompletedAt
FailedAt
```

Step table:

```text
StepKey
ExecutorKey
Status
StartedAt
CompletedAt
ErrorCode
ErrorMessage
```

Manifest summary:

```text
RunnerVersion
PlannerVersion
CorpusSnapshotId
IndexManifestId
Step output hashes
```

Do not show full raw JSON by default, but allow expanding/copying manifest JSON if available.

---

## 5. Adapter Profiles List

Route:

```text
/adaptation/profiles
```

Columns:

```text
CreatedAt
DomainKey
Status
ApprovedForRuntime
CompositeScore
ModelProfile
PromptProfile
RetrievalProfile
SafetyProfile
```

Filters:

```text
domainKey
status
approvedForRuntime
planId
runId
```

Actions:

```text
View Profile
Open Run
Open Plan
```

UX notes:

* `ApprovedForRuntime = true` should be visibly marked.
* Profiles with failed blocking gates should be marked as rejected or unsafe.
* Do not add publish/activate buttons yet.

---

## 6. Adapter Profile Detail

Route:

```text
/adaptation/profiles/:id
```

Sections:

```text
Profile Summary
Composite Score
Metrics
Gate Results
Runtime Profile Keys
Links
```

Profile summary:

```text
ProfileId
PlanId
RunId
DomainKey
Status
ApprovedForRuntime
CompositeScore
CreatedAt
EvaluatedAt
ApprovedAt
```

Runtime profile keys:

```text
ModelProfile
PromptProfile
RetrievalProfile
SafetyProfile
ToolProfile
```

Metrics table:

```text
Metric Key
Value
Threshold
Passed
```

Gate results table:

```text
Gate Key
Blocking
Passed
Message
```

UX rules:

* Failed blocking gates should be highlighted strongly.
* Non-blocking failures should be visible but less severe.
* Show exact metric keys because this is an internal BO.
* Keep raw values available for audit/debugging.

---

## Component suggestions

Reusable components:

```text
StatusBadge
BooleanBadge
ScoreBadge
ProblemAlert
EmptyState
LoadingState
MetricTable
GateResultTable
ReasonTable
StepTimelineTable
CopyableId
```

Do not overbuild charts yet. Tables and badges are enough for v0.3d.

---

## Error handling

The adaptation API returns ProblemDetails-style errors. The BO should display:

```text
title
detail
traceId, if present
```

Common cases:

```text
400 invalid query/filter
403 approval role/policy problem
404 missing plan/run/profile
409 invalid state, such as approving/running wrong status
500 unexpected service error
```

---

## Actions

## Approve plan

Available when:

```text
plan.status == Draft
```

Request:

```http
POST /adaptation-plans/{id}/approve
```

Body:

```json
{
  "approvedByUserId": "admin-user",
  "approverRoles": ["ComplianceReviewer"]
}
```

For v0.3d, the current admin identity/roles can be provided using the existing BO auth context or a temporary local value if auth integration is not ready.

## Start run

Available when:

```text
plan.status == Approved
```

Request:

```http
POST /adaptation-plans/{id}/run
```

Body:

```json
{
  "createdByUserId": "admin-user"
}
```

After success:

```text
navigate to /adaptation/runs/{runId}
```

---

## Visual priority

The BO should optimize for review and trust:

```text
What was planned?
Why was this strategy selected?
Who approved it?
What run was executed?
Which steps ran?
What artifacts were produced?
What profile was produced?
Did the profile pass gates?
Why is it approved or rejected?
```

Avoid hiding details behind excessive abstraction. This is an internal operator console.

---

## Tests

Add tests according to the frontend stack used in `conexus`.

Minimum tests:

```text
AdaptationPlansList renders rows from mocked API
AdaptationPlanDetail renders planning reasons
Approve action calls correct endpoint
StartRun action calls correct endpoint
AdaptationRunsList renders run statuses
AdaptationRunDetail renders step table
AdapterProfilesList renders composite score and status
AdapterProfileDetail highlights failed blocking gate
API client surfaces ProblemDetails detail
```

---

## Definition of done

v0.3d is complete when:

* BO has an Adaptation navigation section.
* Operators can list and open adaptation plans.
* Operators can approve eligible plans.
* Operators can start a run from an approved plan.
* Operators can list and inspect adaptation runs.
* Operators can view run manifests.
* Operators can list and inspect adapter profiles.
* Metrics and gate results are visible.
* Failed blocking gates are clearly highlighted.
* No publish/canary/rollback UI exists yet.
* Frontend build passes.
* Tests pass.
