# Conexus Phase v0.8 — Stale Reservation Repair + Operational Admin Tools

## Goal

v0.7 introduced SQL-backed project limit reservations and reconciliation. The gateway now reserves project usage before provider calls, logs the request, then reconciles the reservation on success/failure. The flow is visible in `gateway_service.py`: reserve, start request, provider call, finish request, reconcile reservation. 

v0.8 should handle the remaining production problem: **what happens when the process dies between reservation and reconciliation?**

The goal is:

```text
1. Detect stale/unreconciled limit reservations.
2. Safely repair or release them.
3. Give admins visibility into stuck reservations and usage windows.
4. Add operational endpoints/tools for manual repair.
5. Keep current gateway response shapes unchanged.
```

Do **not** add Redis, background queues, full billing overhaul, or multi-replica distributed workers in this phase.

---

# Current v0.7 baseline

The reservation service currently creates daily/monthly usage windows, reserves request/token/cost budget, creates a `ProjectGatewayLimitReservation`, and later reconciles it by moving reserved counts into completed counts. 

The current BO query returns the current daily/monthly reservation snapshot:

```text
request_count_reserved
request_count_completed
token_count_reserved
token_count_completed
cost_reserved
cost_completed
```

via `load_project_limit_reservations_snapshot`. 

The missing piece is a **repair path** for reservations where:

```text
reservation exists
gateway request may or may not exist
reservation.reconciled_at is null
reservation is older than threshold
process may have crashed before normal reconcile
```

---

# Phase v0.8a — Stale reservation model and query service

## Add operational classification

Create a service:

```text
backend/app/services/project_limit_reservation_repair_service.py
```

Add dataclasses:

```python
@dataclass(frozen=True, slots=True)
class StaleReservationCandidate:
    reservation_id: str
    project_id: str
    created_at: datetime
    age_seconds: int
    daily_window_id: str
    monthly_window_id: str | None
    request_slots: int
    tokens_reserved: int
    cost_reserved: float
    gateway_request_id: str | None
    gateway_request_status: str | None
    gateway_request_completed_at: datetime | None
    repair_kind: str
    recommended_action: str
```

Repair kinds:

```text
no_gateway_request
gateway_request_failed
gateway_request_completed_without_reconcile
gateway_request_started_but_not_completed
unknown
```

Recommended actions:

```text
release
reconcile_from_request
hold
manual_review
```

## Add query function

```python
async def list_stale_reservations(
    session: AsyncSession,
    *,
    older_than_seconds: int,
    project_id: str | None = None,
    limit: int = 100,
    now: datetime,
) -> list[StaleReservationCandidate]:
```

Rules:

```text
Only reservations where reconciled_at is null.
Only reservations older than threshold.
Join gateway_requests on limit_reservation_id.
Classify based on request status/completed_at/tokens/cost.
```

Suggested default threshold:

```text
15 minutes
```

Config:

```text
LIMIT_RESERVATION_STALE_AFTER_SECONDS=900
```

---

# Phase v0.8b — Repair/release logic

Add function:

```python
async def repair_stale_reservation(
    session: AsyncSession,
    *,
    reservation_id: str,
    mode: Literal["dry_run", "apply"],
    now: datetime,
) -> ReservationRepairResult:
```

Add result:

```python
@dataclass(frozen=True, slots=True)
class ReservationRepairResult:
    reservation_id: str
    project_id: str
    repair_kind: str
    action: str
    applied: bool
    message: str
    before: ReservationWindowDelta
    after: ReservationWindowDelta | None
```

## Repair rules

### 1. No gateway request exists

Meaning:

```text
reservation was created, but request row was never started
```

Action:

```text
release reserved request/token/cost
mark reservation reconciled_at
```

This covers crash between reservation and `start_request`.

### 2. Gateway request exists and failed

Meaning:

```text
request row exists
status failed
reservation not reconciled
```

Action:

```text
move reserved request slot to completed request count
release reserved token/cost
mark reconciled_at
```

Why: failed requests should still count as request attempts, but should not hold token/cost reservation.

### 3. Gateway request completed successfully but reservation not reconciled

Meaning:

```text
request row has success fields / completed_at / token counts / cost
reservation not reconciled
```

Action:

```text
move request slot to completed
move actual tokens to token_count_completed
move actual cost to cost_completed
release reserved token/cost
mark reconciled_at
```

### 4. Gateway request started but not completed

Meaning:

```text
request row exists
completed_at is null
reservation old
```

Action depends on age:

```text
if older than stale threshold but not very old: hold/manual_review
if older than force threshold: mark request failed and reconcile as failed
```

Add second config:

```text
LIMIT_RESERVATION_FORCE_REPAIR_AFTER_SECONDS=3600
```

Do **not** force-repair streaming requests too aggressively.

---

# Phase v0.8c — Admin endpoints

Add endpoints under existing admin project limits area.

## List stale reservations

```http
GET /admin/projects/limits/reservations/stale
```

Query params:

```text
project_id optional
older_than_seconds optional
limit default 100
```

Response:

```json
{
  "now": "...",
  "olderThanSeconds": 900,
  "items": [
    {
      "reservationId": "...",
      "projectId": "...",
      "createdAt": "...",
      "ageSeconds": 1200,
      "repairKind": "no_gateway_request",
      "recommendedAction": "release",
      "tokensReserved": 500,
      "costReserved": 0.02,
      "gatewayRequestId": null
    }
  ]
}
```

## Dry-run repair

```http
POST /admin/projects/limits/reservations/{reservation_id}/repair/dry-run
```

## Apply repair

```http
POST /admin/projects/limits/reservations/{reservation_id}/repair
```

Request:

```json
{
  "reason": "stale reservation repair after provider crash"
}
```

Response:

```json
{
  "reservationId": "...",
  "repairKind": "gateway_request_failed",
  "action": "reconcile_failed_request",
  "applied": true,
  "message": "...",
  "before": {},
  "after": {}
}
```

Security:

```text
admin session required
audit log required
```

---

# Phase v0.8d — Audit logs

Add audit actions:

```text
project.limit_reservation.repair_dry_run
project.limit_reservation.repair_applied
project.limit_reservation.repair_skipped
```

Metadata:

```text
reservation_id
project_id
repair_kind
action
reason
admin_user_id
before/after counters if compact
```

Do not log secrets or request bodies.

---

# Phase v0.8e — CLI repair command

Add CLI commands in `backend/app/cli.py`:

```bash
python -m app.cli limits list-stale-reservations --older-than-seconds 900
python -m app.cli limits repair-stale-reservations --older-than-seconds 900 --dry-run
python -m app.cli limits repair-stale-reservations --older-than-seconds 900 --apply
```

Reason: if the admin UI is unavailable, operators still need repair tools.

CLI output should include:

```text
reservation id
project id
age
repair kind
recommended action
dry-run/apply status
```

---

# Phase v0.8f — BO visibility

Extend the existing Projects page “Admission counters” block.

Add:

```text
Stale reservations count
Oldest stale reservation age
Link/button: View stale reservations
```

Add a simple admin panel:

```text
Project limits → Reservations → Stale
```

Columns:

```text
Project
Reservation ID
Age
Reserved request slots
Reserved tokens
Reserved cost
Gateway request status
Recommended action
Dry-run
Repair
```

Do not overbuild charts.

---

# Phase v0.8g — Health/readiness warning

Do not make `/readyz` fail because stale reservations exist. That would create noisy deployment behavior.

Instead add optional diagnostic endpoint or include a warning only in admin status:

```http
GET /admin/system/operational-warnings
```

For v0.8, optional. Simpler: show warnings only in reservation admin panel.

---

# Phase v0.8h — Tests

## Unit tests

```text
list_stale_reservations_no_gateway_request
list_stale_reservations_failed_gateway_request
list_stale_reservations_completed_without_reconcile
list_stale_reservations_started_not_completed
repair_no_gateway_request_releases_reserved_counts
repair_failed_request_moves_request_to_completed_releases_token_cost
repair_completed_request_reconciles_actual_tokens_and_cost
repair_is_idempotent_when_already_reconciled
repair_dry_run_does_not_mutate
```

## API tests

```text
GET_stale_reservations_requires_admin
GET_stale_reservations_returns_candidates
POST_repair_dry_run_requires_admin
POST_repair_dry_run_does_not_mutate
POST_repair_applies_and_audits
POST_repair_missing_reservation_returns404
```

## Gateway regression tests

```text
reservation_repair_after_start_request_failure
reservation_repair_after_success_finish_without_reconcile
reservation_repair_does_not_double_count_reconciled_reservation
```

## Frontend tests

```text
projects_page_shows_stale_reservation_count
stale_reservations_panel_renders_items
repair_button_calls_endpoint
dry_run_button_does_not_apply
```

---

# Phase v0.8i — Docs

Add:

```text
docs/stale-limit-reservation-repair.md
docs/phase-v0.8-stale-reservation-repair.md
```

Update:

```text
docs/strict-limit-reservations.md
docs/hard-limit-concurrency.md
```

Document:

```text
what stale reservations are
why they happen
which states are auto-repairable
which states require manual review
how request/token/cost counters are adjusted
CLI commands
admin endpoints
safe production workflow
```

Production workflow:

```text
1. Run list stale reservations in dry-run mode.
2. Review repair kinds.
3. Apply repair for safe categories.
4. Recheck project usage windows.
5. Investigate repeated stale reservations.
```

---

# Important policy decisions

## 1. Should blocked 429 attempts count as daily requests?

Current v0.7 behavior logs blocked attempts as failed `gateway_requests`. That can affect legacy aggregates. Decide and document.

Recommended:

```text
Blocked 429 admission attempts should not create reservations, but may be logged as failed gateway requests for audit/abuse visibility.
They should not increase completed reservation counters.
```

Later, if abuse counting needs a separate metric, add `admission_denied_count`.

## 2. Should stale failed requests count as completed request slots?

Recommended:

```text
Yes. If a provider call was attempted, it counts as a request attempt.
```

## 3. Should no-gateway-request reservations count as completed requests?

Recommended:

```text
No. If no gateway request row exists, release the request slot.
```

---

# Definition of done

v0.8 is complete when:

```text
Stale unreconciled reservations can be listed.
Each stale reservation is classified with a recommended action.
Safe repairs can be dry-run.
Safe repairs can be applied idempotently.
Counters are corrected without double-counting.
Manual repair writes audit logs.
CLI repair tools exist.
BO shows stale reservation visibility.
Docs explain operational workflow.
All backend and frontend tests pass.
```

---

# Suggested Cursor prompt

```text
Continue in `uridolan77/conexus`.

Goal: implement Phase v0.8 — stale reservation repair + operational admin tools.

Current state:
- v0.7 added DB-backed project limit reservations:
  - project_usage_windows
  - project_gateway_limit_reservations
  - gateway_requests.limit_reservation_id
- gateway flow now reserves, starts request log, calls provider, finishes request, and reconciles reservation.
- BO has GET /admin/projects/{project_id}/limits/reservations for current usage windows.
- Need repair tooling for process crash / unreconciled reservation scenarios.

Do not touch `conexus.adaptation`.
Do not add Redis.
Do not add background workers.
Do not change public /v1/chat/completions response shape.
Do not redesign billing.
Do not remove existing gateway_requests reporting.

Tasks:

1. Add config.

In backend/app/core/config.py:
- LIMIT_RESERVATION_STALE_AFTER_SECONDS default 900, min 60
- LIMIT_RESERVATION_FORCE_REPAIR_AFTER_SECONDS default 3600, min 300

Update .env.example.

2. Add stale reservation repair service.

Create:
- backend/app/services/project_limit_reservation_repair_service.py

Add:
- StaleReservationCandidate
- ReservationRepairResult
- ReservationWindowDelta or equivalent compact before/after model

Implement:
- list_stale_reservations(session, project_id?, older_than_seconds, limit, now)
- repair_stale_reservation(session, reservation_id, mode: dry_run|apply, now)

Classify:
- no_gateway_request
- gateway_request_failed
- gateway_request_completed_without_reconcile
- gateway_request_started_but_not_completed
- unknown

Repair behavior:
- no_gateway_request: release reserved request/token/cost, mark reconciled
- failed request: move request slot to completed, release token/cost, mark reconciled
- completed request: reconcile actual tokens/cost from gateway_requests, mark reconciled
- started but not completed: hold/manual_review unless older than FORCE threshold; if forced, mark request failed and reconcile as failed
- already reconciled: idempotent no-op

Use row locks on Postgres where practical.
Keep SQLite tests working.

3. Add admin API endpoints.

Under existing admin project/limits router:
- GET /admin/projects/limits/reservations/stale
- POST /admin/projects/limits/reservations/{reservation_id}/repair/dry-run
- POST /admin/projects/limits/reservations/{reservation_id}/repair

All require admin session.

Repair request:
- reason optional string

Responses:
- typed Pydantic models
- no secrets
- clear repair_kind/action/applied/message

4. Add audit logs.

Audit:
- project.limit_reservation.repair_dry_run
- project.limit_reservation.repair_applied
- project.limit_reservation.repair_skipped

Metadata:
- reservation_id
- project_id
- repair_kind
- action
- reason
- applied
- before/after compact counters

5. Add CLI commands.

In backend/app/cli.py or existing CLI structure:
- limits list-stale-reservations --older-than-seconds 900
- limits repair-stale-reservations --older-than-seconds 900 --dry-run
- limits repair-stale-reservations --older-than-seconds 900 --apply

Keep output simple and readable.

6. BO/frontend.

Extend project limits/admission counters UI:
- show stale reservations count
- oldest stale age if available
- add a basic stale reservations panel/page

Panel columns:
- project id
- reservation id
- age
- repair kind
- recommended action
- reserved request slots
- reserved tokens
- reserved cost
- gateway request status
- dry-run button
- repair button

Use existing adminSessionFetch.

7. Tests.

Backend unit tests:
- list stale no gateway request
- list stale failed request
- list stale completed unreconciled request
- dry-run does not mutate
- repair no gateway request releases counts
- repair failed request moves request to completed and releases token/cost
- repair completed request reconciles actual tokens/cost
- repair already reconciled is idempotent

API tests:
- list stale requires admin
- list stale returns candidates
- dry-run requires admin and does not mutate
- repair applies and writes audit
- missing reservation returns 404

Frontend tests:
- stale reservation panel renders candidates
- dry-run button calls endpoint
- repair button calls endpoint
- empty state renders

8. Docs.

Add:
- docs/phase-v0.8-stale-reservation-repair.md
- docs/stale-limit-reservation-repair.md

Update:
- docs/strict-limit-reservations.md
- docs/hard-limit-concurrency.md

Document:
- stale reservation causes
- repair classifications
- dry-run/apply workflow
- CLI commands
- admin endpoints
- production guidance

9. Run:

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
- endpoints added
- CLI commands added
- tests added/updated
- backend test result
- frontend test/build result
- deviations
```

This phase should make v0.7 production-safe enough to operate: not just strict admission, but recovery when reality interrupts the happy path.
