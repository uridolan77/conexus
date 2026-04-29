# Hard project limits and concurrency

## v0.7 behavior (current)

Hard limits use **reservation + reconciliation** on `project_usage_windows`, with
per-request rows in `project_gateway_limit_reservations`. Preflight also considers
legacy aggregates on `gateway_requests` for the active UTC day/month so existing
data continues to count toward caps.

**Semantics:** strict daily request admission (per process plus DB locks on
Postgres). Token and monthly cost limits are **reservation approximations** with
post-call reconciliation.

Details: [strict-limit-reservations.md](strict-limit-reservations.md).

## v0.6 behavior (historical)

Project **hard** limits were enforced by reading aggregates from `gateway_requests`
in `check_hard_limits` **before** the gateway inserted the new `gateway_requests`
row for the in-flight call. That insert happened in a **separate** short-lived
session/transaction (`start_request` via `_with_log_session`).

So each request saw counts **as of its preflight read**, not including other
in-flight requests that had not committed yet.

**Semantics:** **best-effort hard limit under concurrent bursts**, not a strict
per-project serial cap. Under burst traffic, more requests could complete than
`daily_request_limit` would allow if enforcement were strict.

## Risk (v0.6 only)

Operators who assumed “hard = never exceed N requests/day” could see N+1 or more
completed gateway calls under burst concurrency before v0.7.

## Alternative designs (reference)

1. **PostgreSQL row lock on `project_limits`** — superseded by dedicated usage
   window rows in v0.7.
2. **Redis atomic counters** — still valid for very high throughput; not required
   for Conexus v0.7.
3. **Dedicated counter / reservation table** — implemented as
   `project_usage_windows` + `project_gateway_limit_reservations`.
