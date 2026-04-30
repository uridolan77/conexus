Goal: run a comprehensive automatic testing and regression-hardening pass for the current Conexus repo.

Context:
- This repo has a Python FastAPI backend under `backend/`.
- Backend test/lint tooling is pytest + ruff from `backend/pyproject.toml`.
- This repo has a Next/Vitest frontend under `frontend/`; `package.json` defines:
  - `npm test` → `vitest run`
  - `npm run build` → `next build`
- Recent work added:
  - adaptation BO proxy/UI for deployment lifecycle
  - adaptation v0.5 run ops: cancel/retry/resume
  - drift status/check
  - queue diagnostics/repair
  - runtime adapter profile registry
  - internal observability endpoint
  - admin RBAC
  - idempotency forwarding
  - Docker/static_config and docker-compose local sanity updates

Do not touch `uridolan77/conexus.adaptation`.
Do not change `/v1/chat/completions` response shape.
Do not add new major features.
Do not rewrite architecture.
Do not commit build artifacts.
Do not commit secrets or `.env`.

You may apply small low-risk fixes only if tests expose a real bug, especially:
- proxy identity/role stripping
- malformed JSON handling
- missing frontend guards
- missing test fixtures
- minor docs/test corrections

============================================================
PHASE 0 — Baseline inventory
============================================================

1. Inspect current git status.
2. Identify changed/untracked files.
3. Confirm no build artifacts are about to be committed:
   - `frontend/tsconfig.tsbuildinfo`
   - `node_modules/`
   - `__pycache__/`
   - `.pytest_cache/`
   - `.next/`
   - local `.env`
4. Inspect current testing commands from:
   - `backend/pyproject.toml`
   - `frontend/package.json`

Do not run destructive commands.

============================================================
PHASE 1 — Run full baseline verification
============================================================

Backend:

```powershell
cd backend
python -m pytest -q
python -m ruff check .

Frontend:

cd frontend
npm test -- --run
npm run build

Repo root:

docker compose config

If any command fails:

capture the exact failure
identify whether it is test bug, code bug, fixture issue, environment issue, or unrelated local dependency issue
fix only low-risk issues
rerun the smallest failing test first, then full suite
============================================================
PHASE 2 — Backend proxy regression tests

Focus file:

backend/tests/test_admin_adaptation_proxy.py

Add or strengthen tests for the adaptation ops proxy.

Required route coverage:

Run operations:

POST /admin/adaptation/runs/{run_id}/cancel
POST /admin/adaptation/runs/{run_id}/retry
POST /admin/adaptation/runs/{run_id}/resume

Drift:

GET /admin/adaptation/profiles/{profile_id}/drift-status
POST /admin/adaptation/profiles/{profile_id}/check-drift

Queue:

GET /admin/adaptation/runs/queue/diagnostics
POST /admin/adaptation/runs/queue/repair/dry-run
POST /admin/adaptation/runs/queue/repair

For each POST operation, test:

required permission blocks before upstream call
Conexus injects the admin identity
browser-supplied user IDs are ignored
upstream ProblemDetails is preserved
malformed JSON returns 400 and does not proxy

Specifically test identity-stripping against alternate casing:

requestedByUserId
RequestedByUserId
requested_by_user_id
cancelledByUserId
createdByUserId
requestedByUserId
userId
roles
approverRoles

Important:
If current code merges browser JSON after injected identity, add a helper that strips identity/role-like keys case-insensitively before proxying, then add tests proving it.

Required tests:

queue_repair_dry_run_ignores_pascal_case_RequestedByUserId
queue_repair_apply_ignores_snake_case_requested_by_user_id
queue_repair_apply_ignores_roles
cancel_run_ignores_pascal_case_CancelledByUserId
retry_run_ignores_pascal_case_CreatedByUserId
resume_run_ignores_pascal_case_RequestedByUserId

Idempotency:

retry forwards Idempotency-Key
resume forwards Idempotency-Key
publish/activate/promote/rollback still forward Idempotency-Key
============================================================
PHASE 3 — Backend registry/runtime tests

Focus areas:

internal adapter profile registry
active/canary runtime state
gateway request association
observability endpoint
readiness hardening

Add or verify tests:

Internal registry:

internal register requires X-Internal-Api-Key
missing key fails
change-me / too-short prod key fails readiness when registry is enabled
duplicate register by adapterProfileId returns same gatewayProfileId
DB-level uniqueness prevents duplicate adapter_profile_id
DB-level uniqueness prevents duplicate gateway_profile_id
duplicate register with conflicting domain/evidence returns existing row without mutating, or documented behavior

Runtime activation:

one canary per domain
one active per domain
promote preserves activation history
rollback restores previous active when available
duplicate/corrupt active rows resolve deterministically newest-first
duplicate/corrupt canary rows resolve deterministically newest-first

Gateway association:

request with explicit valid X-Conexus-Gateway-Profile-Id logs association
explicit unknown gateway profile returns 400
request with X-Conexus-Domain-Key attaches active/canary profile when available
request without profile/domain preserves existing behavior
response shape remains unchanged

Observability:

internal observability requires API key
returns request count
returns error rate
returns p95 latency
returns cost per answer
unknown profile returns 404 or documented empty behavior
============================================================
PHASE 4 — Frontend API client tests

Focus:

frontend/lib/adaptationApi.ts
frontend/lib/adaptationTypes.ts
frontend/lib/adaptationNormalize.ts
existing adaptation Vitest tests

Add or verify tests:

Run ops:

cancelRun posts only { reason }, no user ID
retryRun posts no user ID and sends Idempotency-Key
resumeRun posts no user ID and sends Idempotency-Key

Drift:

getProfileDriftStatus parses latest assessment
checkProfileDrift posts optional kind
failed ProblemDetails parses and renders

Queue diagnostics:

getQueueDiagnostics forwards query params
parses totalIssueCount
parses issue rows
defaults missing arrays to []

Queue repair:

queueRepairDryRun does not send requestedByUserId
queueRepairApply does not send requestedByUserId
repair result parser defaults actions to []

Deployment:

publish/activate/promote/rollback still do not send user IDs or roles
deployment actions send Idempotency-Key
duplicate/idempotent response renders success feedback if wasDuplicate is present
============================================================
PHASE 5 — Frontend UI tests

Run detail page:

queued run shows Cancel
running run shows Cancel
failed run shows Retry + Resume
completed run shows no destructive operations
cancel requires confirmation or explicit click path
retry success shows new run link
resume 409 shows ProblemDetails

Profile detail:

drift panel renders empty state
drift panel renders warning/critical severity
Check drift calls API and refreshes
runtime state panel still renders
deployment events still render

Queue page:

diagnostics summary renders
issue table renders
manual-review issue has no Apply button
dry-run all calls API
apply all requires typing APPLY
apply all is disabled before dry-run if that is the intended UX
after apply, diagnostics refreshes

Sidebar:

/adaptation/queue link exists and points correctly
============================================================
PHASE 6 — Docker/local sanity checks

Verify:

backend/Dockerfile includes static_config
docker-compose.yml port overrides work:
POSTGRES_PORT
BACKEND_PORT
FRONTEND_PORT
docker compose config passes
new sanity-check doc is safe and contains no secrets

Do not run long Docker integration unless quick and already supported locally.

============================================================
PHASE 7 — Final verification

Run full suite again:

Backend:

cd backend
python -m pytest -q
python -m ruff check .

Frontend:

cd frontend
npm test -- --run
npm run build

Repo:

docker compose config
git status --short
============================================================
REPORT

Report:

baseline results
tests added/updated
bugs found
fixes applied
remaining risks
exact final command results
changed files
whether working tree is clean

If all good, commit and push with a conventional message:

test(adaptation): harden ops proxy and BO regression coverage

If source fixes were needed, use:

fix(adaptation): harden ops proxy identity stripping

or combine clearly:

fix(adaptation): harden ops proxy identity stripping and tests