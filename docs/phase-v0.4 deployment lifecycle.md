# Plan — Conexus BO proxy/UI for `conexus.adaptation` v0.4 deployment lifecycle

## Goal

Update **`uridolan77/conexus`** so the Back Office can safely operate the new `conexus.adaptation` v0.4 lifecycle:

```text
publish → activate canary → promote → rollback
```

The critical rule: **the browser must never send deployment roles directly to `conexus.adaptation`.** The Conexus backend proxy must inject identity and roles server-side.

`conexus.adaptation` now exposes v0.4 endpoints such as publish, activate-canary, promote, rollback, activations, and active-profile. The current Conexus proxy only covers plans, runs, manifests, run profile, profile list/get, approve, and start-run. 

The current frontend adaptation API client likewise only supports existing plan/run/profile read operations plus approve/start-run. 

---

# Non-goals

Do **not** implement in this phase:

```text
real gateway traffic switching inside Conexus Gateway
new auth system
service-to-service JWT
KGB/SLOD UI editing
drift monitoring
automatic rollback
background jobs
retry/cancel/resume
direct browser calls to conexus.adaptation
```

This phase is a **BO proxy + operator UI integration**, not a new lifecycle engine.

---

# Phase 1 — Backend proxy deployment identity

## Current issue

The proxy currently has:

```python
def _temporary_identity() -> tuple[str, list[str]]:
    return ("admin-user", ["ComplianceReviewer"])
```

and uses that for plan approve/start-run. 

That is insufficient for v0.4 deployment because v0.4 requires roles like:

```text
AdaptationPublisher
AdaptationOperator
ComplianceReviewer
```

## Add identity mapping

Add helper in `backend/app/api/admin_adaptation.py`:

```python
def _deployment_identity(admin: AdminSession) -> tuple[str, list[str]]:
    ...
```

Initial pragmatic behavior:

```text
user_id = admin.username or admin.user_id
roles = ["ComplianceReviewer", "AdaptationPublisher", "AdaptationOperator"]
```

Better behavior, if admin roles already exist in Conexus:

```text
map Conexus admin capabilities → adaptation roles
```

Suggested mapping:

```text
Conexus super/admin → ComplianceReviewer, AdaptationPublisher, AdaptationOperator
read-only admin → no deployment roles
```

If Conexus does not yet have roles, use the pragmatic all-deployment-roles mapping but document it as temporary.

## Add tests

```text
deployment_identity_includes_required_roles_for_admin
deployment_identity_uses_admin_session_identity_not_browser_body
```

---

# Phase 2 — Backend proxy endpoints

Add these routes under `backend/app/api/admin_adaptation.py`.

## 2.1 Get run evaluation evidence

```http
GET /admin/adaptation/runs/{run_id}/evaluation
```

Proxy to:

```http
GET /adaptation-runs/{run_id}/evaluation
```

Why: BO run detail needs the v0.3j persisted evidence projection before publish decisions.

Behavior:

* requires admin session
* preserves upstream 200/400/404 ProblemDetails
* 404 evidence-missing should be displayed in UI as “No evaluation evidence available”

## 2.2 Publish profile

```http
POST /admin/adaptation/profiles/{profile_id}/publish
```

Proxy to:

```http
POST /adapter-profiles/{profile_id}/publish
```

Browser request body should only allow:

```json
{
  "notes": "optional operator note"
}
```

Proxy injects:

```json
{
  "publishedByUserId": "<admin identity>",
  "roles": ["AdaptationPublisher", "..."],
  "notes": "..."
}
```

Do not accept `roles` or `publishedByUserId` from browser.

## 2.3 Activate canary

```http
POST /admin/adaptation/profiles/{profile_id}/activate-canary
```

Browser body:

```json
{
  "canaryPercent": 10
}
```

Proxy injects:

```json
{
  "activatedByUserId": "<admin identity>",
  "roles": ["AdaptationOperator", "..."],
  "canaryPercent": 10
}
```

Validate in Conexus proxy before forwarding:

* `canaryPercent >= 1`
* `canaryPercent <= 50`

## 2.4 Promote

```http
POST /admin/adaptation/profiles/{profile_id}/promote
```

Browser body can be `{}`.

Proxy injects:

```json
{
  "userId": "<admin identity>",
  "roles": ["AdaptationOperator", "..."]
}
```

## 2.5 Rollback

```http
POST /admin/adaptation/profiles/{profile_id}/rollback
```

Browser body:

```json
{
  "reason": "why rollback is needed"
}
```

Proxy injects:

```json
{
  "userId": "<admin identity>",
  "roles": ["AdaptationOperator", "ComplianceReviewer", "..."],
  "reason": "..."
}
```

Validate:

* non-empty reason
* trim whitespace

## 2.6 List activations

```http
GET /admin/adaptation/profiles/{profile_id}/activations
```

Proxy to:

```http
GET /adapter-profiles/{profile_id}/activations
```

## 2.7 Active profile by domain

```http
GET /admin/adaptation/domains/{domain_key}/active-profile
```

Proxy to:

```http
GET /domains/{domainKey}/active-profile
```

Use URL encoding. Domain key should be lowercased only if the adaptation service expects normalized keys; otherwise preserve and let upstream validate.

---

# Phase 3 — Backend proxy tests

Add tests in `backend/tests/test_admin_adaptation_proxy.py`.

## Required tests

```text
GET_run_evaluation_requires_admin
GET_run_evaluation_forwards_to_upstream
GET_run_evaluation_preserves_404_problem_details

POST_publish_requires_admin
POST_publish_injects_admin_identity_and_roles
POST_publish_does_not_forward_browser_roles
POST_publish_preserves_409_problem_details

POST_activate_canary_injects_identity_roles_and_percent
POST_activate_canary_rejects_invalid_percent_before_proxy

POST_promote_injects_identity_and_roles

POST_rollback_injects_identity_roles_and_reason
POST_rollback_rejects_empty_reason

GET_profile_activations_forwards_to_upstream
GET_domain_active_profile_forwards_to_upstream

adaptation_service_missing_returns_503
upstream_timeout_returns_504
upstream_connect_error_returns_502
```

## Security-specific test

The most important test:

```text
browser_supplied_roles_are_ignored_for_deployment_actions
```

Example browser body:

```json
{
  "roles": ["FakeSuperAdmin"],
  "publishedByUserId": "attacker",
  "notes": "x"
}
```

Expected upstream body should contain Conexus-injected identity/roles, not attacker fields.

---

# Phase 4 — Frontend types and normalization

Current `frontend/lib/adaptationApi.ts` imports only plan/run/profile types and normalizers. 

Add types in `frontend/lib/adaptationTypes.ts`.

## Deployment types

```ts
export type PublishAdapterProfileResult = {
  adapterProfileId: string;
  gatewayProfileId: string;
  status: string;
};

export type AdapterProfileActivationResult = {
  activationId: string;
  adapterProfileId: string;
  status: string;
};

export type PromoteAdapterProfileResult = {
  adapterProfileId: string;
  status: string;
};

export type RollbackAdapterProfileResult = {
  adapterProfileId: string;
  status: string;
};

export type AdapterProfileActivation = {
  id: string;
  adapterProfileId: string;
  domainKey: string;
  status: string;
  canaryPercent: number;
  previousActiveProfileId?: string | null;
  rollbackReason?: string | null;
  createdAt: string;
  activatedAt?: string | null;
  rolledBackAt?: string | null;
};
```

## Evaluation evidence types

Add BO-safe DTO types matching `/evaluation`:

```ts
export type EvaluationEvidence = {
  id: string;
  runId: string;
  planId: string;
  domainKey: string;
  evalSetId: string;
  createdAt: string;
  compositeScore: number;
  projectionVersion: string;
  evidenceHash: string;
  metrics: EvaluationMetric[];
  gates: EvaluationGateResult[];
  securitySummary: EvaluationSecuritySummary;
  questions: EvalQuestionEvidence[];
};

export type EvalQuestionEvidence = {
  questionId: string;
  question: string;
  category: string;
  answerExcerpt: string;
  answered: boolean;
  requiredSourceIds: string[];
  requiredDocumentIds: string[];
  requiredChunkIds: string[];
  retrievedContexts: RetrievedContextEvidence[];
  citationValidation: CitationValidationResult;
  estimatedCost: number;
  latencyMs: number;
};
```

Keep fields optional/tolerant if the adaptation response casing varies.

## Add normalizers

In `frontend/lib/adaptationNormalize.ts`, add:

```text
normalizeEvaluationEvidence
normalizeActivationList
normalizePublishResult
normalizeActivationResult
normalizePromoteResult
normalizeRollbackResult
```

Rules:

* accept camelCase and snake_case
* default missing arrays to `[]`
* default nullable text fields to `null`
* preserve unknown status strings rather than throwing

---

# Phase 5 — Frontend API client methods

Extend `frontend/lib/adaptationApi.ts`.

Add:

```ts
getRunEvaluation(runId: string)

publishProfile(profileId: string, input: { notes?: string })

activateCanary(profileId: string, input: { canaryPercent: number })

promoteProfile(profileId: string)

rollbackProfile(profileId: string, input: { reason: string })

listProfileActivations(profileId: string)

getActiveProfile(domainKey: string)
```

Important:

* browser body must not contain roles/user IDs
* use `/admin/adaptation/...` only
* use `adminSessionFetch`
* preserve ProblemDetails parsing

Example:

```ts
publishProfile: (profileId, input) =>
  requestAdaptation(
    `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/publish`,
    normalizePublishResult,
    { method: "POST", body: JSON.stringify({ notes: input.notes ?? null }) },
  )
```

---

# Phase 6 — Run detail UI: evaluation evidence viewer

## Current route

```text
/adaptation/runs/[id]
```

Add fetch:

```text
GET /admin/adaptation/runs/{id}/evaluation
```

## Behavior

If 404:

* do not fail whole page
* show:

```text
No evaluation evidence projection is available for this run.
```

If 200:
show sections:

```text
Evaluation Summary
Security Summary
Metrics
Gate Results
Question Evidence
Citation Issues
Retrieved Context Excerpts
```

## Question evidence UI

For each question:

* question id
* category
* answered
* latency
* estimated cost
* citation passed/failed
* lexical support score
* answer excerpt
* retrieved context excerpts
* source/document/chunk IDs
* citation issues

Use collapsible sections if existing UI supports it. Otherwise, simple cards/tables are fine.

## Highlighting

```text
blocking citation issues → red/error
non-blocking issues → warning
failed gates → red/error
passed gates → success
```

Do not display full raw context beyond returned excerpts.

---

# Phase 7 — Profile detail UI: deployment lifecycle controls

## Current route

```text
/adaptation/profiles/[id]
```

Add fetches:

```text
GET /admin/adaptation/profiles/{id}/activations
GET /admin/adaptation/domains/{domainKey}/active-profile
```

## Add deployment panel

Show:

```text
Current profile status
ApprovedForRuntime
GatewayProfileId
CanaryPercent
PublishedAt
ActivatedAt
RolledBackAt
RollbackReason
Active profile for this domain
Activation history
```

## Actions by status

Use profile status to show available actions.

### If `Approved`

Show:

```text
Publish
```

Modal/form:

* notes optional
* confirmation copy:
  “This registers the adapter profile with the gateway registration service. It does not necessarily shift production traffic unless activation follows.”

### If `Published`

Show:

```text
Activate Canary
```

Input:

* canary percent 1–50
* default 10

### If `Canary`

Show:

```text
Promote to Active
Rollback
```

Rollback requires reason.

### If `Active`

Show:

```text
Rollback
Retire
```

Retire only if adaptation backend actually exposes it. If not, do not add.

### If `RolledBack` / `Retired`

Show no primary actions.

## Confirmation and safety copy

Deployment actions should require confirmation text/button, not one-click.

Examples:

```text
Publish profile?
Activate 10% canary?
Promote canary profile to active?
Rollback active/canary profile?
```

## Post-action behavior

After success:

* refresh profile
* refresh activations
* refresh active profile
* show success message
* keep user on profile detail page

On failure:

* show `ProblemDetails` via `AdaptationErrorBanner`

---

# Phase 8 — Profile list UI improvements

On `/adaptation/profiles` add columns if not already present:

```text
Status
ApprovedForRuntime
DomainKey
CompositeScore
GatewayProfileId
CanaryPercent
PublishedAt
ActivatedAt
```

Filters:

* status
* domainKey
* approvedForRuntime

Action links:

* View
* active/canary badges

Do not add bulk deployment actions.

---

# Phase 9 — Shared UI components

Add or reuse components under `frontend/components/adaptation/`.

Suggested:

```text
DeploymentStatusBadge
DeploymentActionPanel
ActivationHistoryTable
EvaluationEvidencePanel
QuestionEvidenceCard
CitationIssueTable
RetrievedContextExcerptTable
DeploymentConfirmDialog
```

Keep styling simple and consistent with existing BO components.

Do not introduce a new UI library.

---

# Phase 10 — Frontend tests

Add tests in `frontend/test/adaptation.test.tsx` or split file.

## API client tests

```text
publishProfile_posts_notes_only
activateCanary_posts_percent_only
rollback_posts_reason_only
getRunEvaluation_parses_questions_and_trace_id_problem
```

## Run detail tests

```text
run_detail_loads_evaluation_evidence
run_detail_evidence_404_shows_no_evidence_message
run_detail_highlights_blocking_citation_issue
run_detail_displays_retrieved_context_excerpt
```

## Profile detail tests

```text
profile_detail_approved_shows_publish_button
profile_detail_published_shows_activate_canary_button
profile_detail_canary_shows_promote_and_rollback_buttons
publish_action_calls_proxy_and_refreshes
activate_canary_rejects_invalid_percent_client_side
rollback_requires_reason
activation_history_renders_rows
```

---

# Phase 11 — Backend docs

Update or add:

```text
docs/phase-v0.9-adaptation-deployment-bo.md
```

or update the existing adaptation BO doc.

Document:

* new proxy endpoints
* browser does not send roles
* proxy injects identity and roles
* deployment role mapping is temporary unless real Conexus roles exist
* Conexus BO does not directly change traffic unless gateway registration/activation is wired to real gateway behavior
* ProblemDetails pass-through
* evidence viewer uses truncated excerpts only

---

# Phase 12 — Manual QA checklist

Use local Conexus + local adaptation service.

## Scenario A — Evidence view

```text
1. Run adaptation plan.
2. Open /adaptation/runs/{id}.
3. Evidence panel loads.
4. Questions, citations, gates, context excerpts visible.
```

## Scenario B — Publish

```text
1. Open Approved profile.
2. Click Publish.
3. Confirm.
4. Profile status becomes Published.
5. GatewayProfileId visible.
6. Activation history/event visible if exposed.
```

## Scenario C — Canary

```text
1. Open Published profile.
2. Activate 10% canary.
3. Profile status becomes Canary.
4. CanaryPercent visible.
```

## Scenario D — Promote

```text
1. Open Canary profile.
2. Promote to Active.
3. Domain active profile endpoint returns this profile.
```

## Scenario E — Rollback

```text
1. Rollback Active/Canary profile with reason.
2. Status becomes RolledBack.
3. Previous active restored if adaptation backend supports it.
```

---

# Definition of done

This phase is complete when:

```text
Conexus backend proxies all v0.4 deployment lifecycle endpoints.
Conexus proxy injects admin identity and deployment roles.
Browser never sends roles/user IDs to adaptation.
Run detail page can display persisted evaluation evidence.
Profile detail page can publish, activate canary, promote, and rollback.
Profile detail page shows activation history and active-domain profile.
Deployment failures show ProblemDetails.
Frontend tests cover deployment actions and evidence view.
Backend proxy tests prove identity/role injection and error pass-through.
No direct browser calls to conexus.adaptation exist.
```

---

# Suggested Cursor prompt

```text
Continue in `uridolan77/conexus`.

Goal: implement Conexus BO proxy/UI for `conexus.adaptation` v0.4 deployment lifecycle.

Context:
- `conexus.adaptation` v0.4 exposes:
  - GET /adaptation-runs/{id}/evaluation
  - POST /adapter-profiles/{id}/publish
  - POST /adapter-profiles/{id}/activate-canary
  - POST /adapter-profiles/{id}/promote
  - POST /adapter-profiles/{id}/rollback
  - GET /adapter-profiles/{id}/activations
  - GET /domains/{domainKey}/active-profile
- Current Conexus proxy in backend/app/api/admin_adaptation.py only covers plans/runs/manifests/run-profile/profile-list/profile-get/approve/start-run.
- Current frontend/lib/adaptationApi.ts only covers existing plan/run/profile methods.
- Browser must never call the adaptation service directly.
- Browser must never send roles or user IDs for deployment actions.
- Conexus backend proxy must inject admin identity and adaptation deployment roles.

Do not touch `conexus.adaptation`.
Do not add real gateway traffic shifting.
Do not add drift monitoring.
Do not add cancel/retry/resume.
Do not add a new auth system.
Do not expose ADAPTATION_API_BASE_URL to browser.
Do not add raw roles/user IDs to frontend request bodies.

Tasks:

1. Backend proxy identity.

In backend/app/api/admin_adaptation.py:
- add deployment identity helper based on AdminSession.
- for now, map admin session to:
  - ComplianceReviewer
  - AdaptationPublisher
  - AdaptationOperator
- add TODO: replace with real Conexus admin role mapping before production.

2. Add backend proxy endpoints:

GET /admin/adaptation/runs/{run_id}/evaluation
  -> GET /adaptation-runs/{run_id}/evaluation

POST /admin/adaptation/profiles/{profile_id}/publish
  -> POST /adapter-profiles/{profile_id}/publish
  browser body only: { notes?: string }
  inject: publishedByUserId, roles

POST /admin/adaptation/profiles/{profile_id}/activate-canary
  -> POST /adapter-profiles/{profile_id}/activate-canary
  browser body only: { canaryPercent: number }
  validate 1 <= canaryPercent <= 50
  inject: activatedByUserId, roles

POST /admin/adaptation/profiles/{profile_id}/promote
  -> POST /adapter-profiles/{profile_id}/promote
  browser body: {}
  inject: userId, roles

POST /admin/adaptation/profiles/{profile_id}/rollback
  -> POST /adapter-profiles/{profile_id}/rollback
  browser body only: { reason: string }
  validate non-empty reason
  inject: userId, roles

GET /admin/adaptation/profiles/{profile_id}/activations
  -> GET /adapter-profiles/{profile_id}/activations

GET /admin/adaptation/domains/{domain_key}/active-profile
  -> GET /domains/{domainKey}/active-profile

Preserve upstream ProblemDetails response bodies/status codes.

3. Backend tests.

In backend/tests/test_admin_adaptation_proxy.py add tests:
- all new endpoints require admin
- run evaluation forwards and preserves 404
- publish injects admin identity/roles
- publish ignores browser-supplied roles/user IDs
- activate-canary validates percent and injects identity/roles
- promote injects identity/roles
- rollback rejects empty reason
- rollback injects identity/roles/reason
- activations forwards
- active-profile forwards
- upstream timeout/connect error behavior still works

4. Frontend types and normalizers.

Update:
- frontend/lib/adaptationTypes.ts
- frontend/lib/adaptationNormalize.ts

Add typed DTOs/normalizers for:
- EvaluationEvidence
- EvalQuestionEvidence
- RetrievedContextEvidence
- CitationValidationResult
- EvaluationSecuritySummary
- PublishAdapterProfileResult
- AdapterProfileActivationResult
- PromoteAdapterProfileResult
- RollbackAdapterProfileResult
- AdapterProfileActivation

Normalize camelCase + snake_case.
Default arrays to [].
Keep unknown status strings.

5. Frontend API client.

Update frontend/lib/adaptationApi.ts with:
- getRunEvaluation(runId)
- publishProfile(profileId, { notes? })
- activateCanary(profileId, { canaryPercent })
- promoteProfile(profileId)
- rollbackProfile(profileId, { reason })
- listProfileActivations(profileId)
- getActiveProfile(domainKey)

Use only /admin/adaptation routes.
Use adminSessionFetch.
Do not include roles/user IDs in browser body.

6. Run detail evidence UI.

Update /adaptation/runs/[id]:
- fetch evaluation evidence
- if 404, show "No evaluation evidence projection is available for this run."
- if 200, show:
  - evaluation summary
  - security summary
  - metrics
  - gates
  - question evidence
  - citation issues
  - retrieved context excerpts
- highlight failed blocking issues/gates.

7. Profile deployment UI.

Update /adaptation/profiles/[id]:
- fetch profile
- fetch activations
- fetch active profile for profile.domainKey
- show deployment panel:
  - status
  - approvedForRuntime
  - gatewayProfileId
  - canaryPercent
  - publishedAt
  - activatedAt
  - rolledBackAt
  - rollbackReason
  - current active profile for domain
- show actions based on status:
  - Approved -> Publish
  - Published -> Activate Canary
  - Canary -> Promote, Rollback
  - Active -> Rollback
  - RolledBack/Retired -> no primary actions
- require confirmation for publish/promote/rollback.
- activate canary requires percent 1-50.
- rollback requires reason.
- refresh profile/activations/active profile after success.
- show ProblemDetails errors via AdaptationErrorBanner.

8. Profile list polish.

Update /adaptation/profiles if easy:
- show status badges for Published/Canary/Active/RolledBack
- show gatewayProfileId/canaryPercent if available
- no bulk actions.

9. Shared components.

Add/reuse:
- DeploymentStatusBadge
- DeploymentActionPanel
- ActivationHistoryTable
- EvaluationEvidencePanel
- QuestionEvidenceCard
- CitationIssueTable
- RetrievedContextExcerptTable

Keep styling simple.

10. Frontend tests.

Add tests:
- publishProfile posts notes only, not roles/user IDs
- activateCanary posts percent only
- rollback posts reason only
- run detail evidence 404 shows no evidence message
- run detail renders question evidence and blocking citation issue
- profile detail Approved shows Publish
- profile detail Published shows Activate Canary
- profile detail Canary shows Promote and Rollback
- activate canary rejects invalid percent
- rollback requires reason
- activation history renders

11. Docs.

Add/update a doc:
- docs/phase-v0.9-adaptation-deployment-bo.md
or update existing adaptation BO doc.

Document:
- new proxy endpoints
- proxy identity/role injection
- browser never sends roles
- evidence endpoint displays truncated excerpts only
- deployment actions currently call deterministic registration/stub on adaptation side
- real gateway traffic shifting is separate future work

12. Run:

Backend:
cd backend
pytest -q
ruff check .

Frontend:
cd frontend
npm test -- --run
npm run build

Report:
- files changed
- proxy endpoints added
- frontend routes/components updated
- tests added/updated
- backend test result
- frontend test/build result
- deviations
```

This should be the next Conexus phase before moving to `conexus.adaptation` v0.5. It makes the v0.4 lifecycle actually operable from the BO while keeping the trust boundary in the right place: **browser → Conexus BO → adaptation service**, never browser → adaptation service.
