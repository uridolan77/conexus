# Hard project limits and concurrency

## Current behavior (v0.6)

Project **hard** limits (`limit_mode == hard`) are enforced by reading aggregates
from `gateway_requests` (daily request count, daily token sum, monthly cost sum)
in `check_hard_limits` **before** the gateway inserts the new `gateway_requests`
row for the in-flight call. That insert happens in a **separate** short-lived
session/transaction (`start_request` via `_with_log_session`).

So each request sees counts **as of its preflight read**, not including other
in-flight requests that have not committed yet.

**Semantics:** **best-effort hard limit under concurrent bursts**, not a strict
per-project serial cap. Under burst traffic, more requests can complete than
`daily_request_limit` (or token/cost caps) would allow if enforcement were
strict.

## Risk

Operators who assume “hard = never exceed N requests/day” may see N+1 or more
completed gateway calls when many clients hit the API at once.

## Recommended production implementations

Pick one (or combine) depending on scale and tolerance:

1. **PostgreSQL row lock on `project_limits`**  
   In one transaction: `SELECT ... FROM project_limits WHERE project_id = :id
   FOR UPDATE`, recompute usage, insert the `started` log row (or a
   reservation row), commit **before** calling the provider. Serializes limit
   checks per project on Postgres. SQLite does not offer the same `FOR UPDATE`
   semantics across all deployments — keep tests/docs explicit if you support
   SQLite in production.

2. **Redis atomic counters**  
   Increment daily/monthly counters with `INCR` / sliding windows; gate the
   provider call on the result. Shared across workers and replicas. This repo
   defers Redis until explicitly scoped.

3. **Dedicated counter / reservation table**  
   Insert a “slot” row or bump a counter in the same transaction as the
   preflight decision; cheaper than locking whole limit rows if designed well.

## This slice (v0.6)

- Behavior is **documented** as best-effort; code comments point here.
- A **concurrency regression test** documents that multiple concurrent requests
  can pass preflight when `daily_request_limit = 1` and no rows exist yet.
- **Strict** DB-backed locking in the gateway path is **deferred** to avoid a
  large cross-database refactor in this milestone.
