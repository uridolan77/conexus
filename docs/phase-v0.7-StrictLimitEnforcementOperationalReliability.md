Phase v0.7 — Strict Limit Enforcement + Operational Reliability
```

The main unresolved backend risk is that project “hard” limits are currently documented as **best-effort under concurrency**. `check_hard_limits` reads aggregate `gateway_requests` rows before the new request row is committed, so concurrent bursts can pass together. The code now documents this explicitly. 

---

# Phase v0.7 — Strict Limit Enforcement + Operational Reliability

## Goal

Move Conexus from “good MVP gateway” to “safer production gateway” by making limit behavior explicit, improving enforcement, and making failures auditable.

Scope:

```text
1. strict or semi-strict project limit reservations
2. usage counter / reservation model
3. request lifecycle correctness
4. better operator visibility
5. deployment docs
```

Do **not** touch `conexus.adaptation` in this phase.

---

# 0. Tiny post-v0.6 polish first

Before v0.7, do the small cleanup from the last review:

```text
1. Guard Anthropic stream __aexit__ so cleanup errors do not mask original errors.
2. Add middleware tests for /adaptation protection.
3. Add docs note: ADMIN_LOGIN_RATE_LIMIT_BACKEND currently supports only in_memory.
```

This should be one tiny commit.

---

# 1. Decide hard-limit semantics

Current semantics:

```text
daily request limit: best-effort under concurrency
daily token limit: aggregate-based, post-fact
monthly cost limit: aggregate-based, post-fact
```

Target semantics for v0.7:

```text
daily request limit: strict reservation
daily token limit: reservation-based approximation
monthly cost limit: reservation-based approximation
```

Important distinction:

```text
Requests can be strictly counted before provider call.
Tokens/cost cannot be perfectly known before provider call.
```

So implement token/cost as reservation + reconciliation, not perfect prediction.

---

# 2. Add project usage counter / reservation table

Add a new table, for example:

```text
project_usage_windows
```

Fields:

```text
id
project_id
window_kind              -- daily | monthly
window_start_utc
window_end_utc
request_count_reserved
request_count_completed
token_count_reserved
token_count_completed
cost_reserved
cost_completed
created_at
updated_at
```

Unique index:

```text
(project_id, window_kind, window_start_utc)
```

Add Alembic migration.

Reason: aggregate queries over `gateway_requests` are fine for reporting, but strict admission control needs one row to lock/update atomically.

---

# 3. Add `ProjectLimitReservationService`

Create:

```text
backend/app/services/project_limit_reservation_service.py
```

Core methods:

```python
async def reserve_gateway_request(
    session,
    *,
    project_id: str,
    limits: ProjectLimit,
    requested_max_tokens: int,
    estimated_max_cost: float,
    now: datetime,
) -> LimitReservationResult
```

```python
async def reconcile_gateway_request(
    session,
    *,
    reservation_id: str,
    actual_tokens: int,
    actual_cost: float,
    status: str,
) -> None
```

Reservation result:

```python
@dataclass
class LimitReservationResult:
    allowed: bool
    reservation_id: str | None
    block: LimitBlock | None
```

Behavior:

```text
1. Get/create daily usage window row.
2. Lock row if DB supports it.
3. Check request_count_reserved against daily_request_limit.
4. Increment request_count_reserved if allowed.
5. Reserve estimated tokens if daily_token_limit configured.
6. Get/create monthly usage window row.
7. Reserve estimated cost if monthly_cost_limit configured.
8. Return reservation id.
```

For SQLite/dev, use transaction behavior as best available. For Postgres, use row lock:

```sql
SELECT ... FOR UPDATE
```

---

# 4. Request lifecycle integration

Current gateway flow:

```text
check limits
call provider
write gateway request log
```

New flow:

```text
load project limits
reserve usage
if blocked: return 429
create request id
call provider
write gateway request log
reconcile reservation with actual usage/cost/status
```

For provider failure:

```text
daily request still counts
reserved token/cost should be released or reconciled to actual 0
gateway_request row still records failure
```

For timeout/cancellation:

```text
daily request still counts
token/cost reservation reconciles to 0 unless usage known
request status = failed / timeout
```

---

# 5. Token/cost reservation policy

Add clear policy.

Initial conservative formula:

```text
reserved_tokens = requested max_tokens + estimated prompt tokens
```

If prompt token count is not available before provider call:

```text
reserved_tokens = max_tokens
```

For cost:

```text
reserved_cost = estimate from model pricing and reserved_tokens
```

If pricing unavailable:

```text
reserved_cost = 0
```

Do not block on unknown cost unless monthly_cost_limit is configured and pricing is missing. In that case choose one:

Recommended:

```text
If monthly cost hard limit is configured and pricing is unknown, block with "pricing_unavailable_for_hard_cost_limit".
```

This is stricter and safer.

---

# 6. Preserve existing aggregate reporting

Do not remove current `GatewayRequest` aggregate usage queries.

They are still useful for:

```text
BO reporting
auditing
historical usage
debugging
cost analysis
```

The new counter table is for admission control.

The existing composite index on `gateway_requests(project_id, created_at)` remains valuable for reporting and fallback aggregate checks.

---

# 7. Add tests

## Unit tests

```text
reserve_allows_under_daily_request_limit
reserve_blocks_at_daily_request_limit
reserve_increments_daily_window
reserve_uses_utc_day_window
reserve_uses_utc_month_window
reconcile_moves_reserved_to_completed
reconcile_releases_unused_token_reservation
cost_limit_blocks_when_reserved_cost_exceeds_limit
```

## Concurrency tests

```text
strict_daily_request_limit_allows_only_one_under_concurrency
strict_daily_request_limit_blocks_remaining_concurrent_requests
```

This should replace or invert the current test that documents best-effort behavior.

## Gateway integration tests

```text
gateway_hard_daily_request_limit_is_strict_under_concurrency
gateway_provider_not_called_when_reservation_blocked
gateway_failed_provider_call_reconciles_reservation
gateway_timeout_reconciles_reservation
```

---

# 8. BO visibility

Add backend admin endpoint:

```http
GET /admin/projects/{project_id}/limits/reservations
```

or extend current limits usage endpoint.

Return:

```json
{
  "project_id": "...",
  "daily": {
    "window_start": "...",
    "window_end": "...",
    "request_count_reserved": 10,
    "request_count_completed": 9,
    "token_count_reserved": 10000,
    "token_count_completed": 8500
  },
  "monthly": {
    "cost_reserved": 12.34,
    "cost_completed": 10.91
  }
}
```

Frontend can be a small addition to project limits page:

```text
Current reserved usage
Completed usage
Remaining limits
```

Do not overbuild charts.

---

# 9. Docs

Add:

```text
docs/strict-limit-reservations.md
```

Update:

```text
docs/hard-limit-concurrency.md
```

Document:

```text
v0.6 behavior: best-effort aggregate preflight
v0.7 behavior: reservation/counter-based admission control
request limits are strict
token/cost limits are reservation approximations
failed requests count against request limits
actual usage reconciles after provider response
SQLite behavior may be weaker than Postgres under true concurrency
```

---

# 10. Deployment notes

Add production recommendation:

```text
Use Postgres for strict reservation semantics.
SQLite is local/dev only.
Run Alembic migrations before deployment.
Set provider pricing config if monthly cost hard limits are enabled.
Use distributed login limiter before multi-replica deployment.
```

---

# Definition of done

v0.7 is done when:

```text
1. Daily request hard limit is strict under concurrent gateway traffic.
2. Token and cost limits use explicit reservation + reconciliation semantics.
3. Provider is not called when reservation blocks the request.
4. Failed provider calls reconcile reservations safely.
5. BO can inspect current reserved/completed limit usage.
6. Docs no longer describe hard limits as merely best-effort, except for SQLite/dev caveat.
7. Backend tests prove concurrency behavior.
8. Existing gateway response shapes remain unchanged.
```

---

# Recommended implementation order

```text
1. Tiny post-v0.6 polish commit.
2. Add project_usage_windows migration/model.
3. Add ProjectLimitReservationService.
4. Integrate non-streaming gateway path.
5. Integrate streaming gateway path.
6. Add concurrency tests.
7. Add BO/backend visibility endpoint.
8. Add small frontend display if quick.
9. Update docs.
```

## Decision I recommend

Use **DB-backed reservations**, not Redis, for the next phase.

Reason:

```text
- You already have SQLAlchemy/Alembic.
- Usage enforcement belongs close to project limits and gateway request records.
- Redis can come later for rate limiting / high-throughput counters.
- DB-backed reservations are easier to audit.
```

Redis is useful later, but for Conexus v0.7 the database is the better source of truth.
