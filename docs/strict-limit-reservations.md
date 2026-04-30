# Strict limit reservations (v0.7)

Conexus **hard** project limits (`limit_mode == hard`) use DB-backed usage windows
(`project_usage_windows`) plus per-call rows (`project_gateway_limit_reservations`)
for admission control. Aggregate queries on `gateway_requests` remain for reporting,
auditing, and backward-compatible pre-checks against historical rows.

## Semantics

- **Daily request limit:** strict reservation before the provider runs. Legacy
  `gateway_requests` rows for the current UTC day are counted together with
  `request_count_reserved` so existing deployments behave as before v0.7.
- **Daily token limit:** reservation uses a conservative token budget
  (`max_tokens`, or `max_tokens + estimated_prompt_tokens` when an estimate is
  supplied). Actual usage reconciles after the provider responds; unused reserved
  tokens are released.
- **Monthly cost limit:** reservation uses `estimate_hard_monthly_reservation_cost_usd`.
  If the **requested** model id has explicit pricing, a single-model estimate is used
  (unchanged from plain `estimate_reservation_cost_usd`). If the requested name is not
  in the pricing table (e.g. a Conexus alias such as `conexus-default`), the gateway
  resolves **concrete** Anthropic and OpenAI targets from the model-alias config and
  takes the **maximum** per-candidate reservation cost (most conservative). If **any**
  candidate lacks explicit pricing, admission fails with
  `pricing_unavailable_for_hard_cost_limit`.
- **Failed / timed-out calls:** still consume the daily request reservation; token
  and cost reservations reconcile toward actuals (often zero).

## Blocked admission attempts

When hard limits reject a request before the provider runs, the gateway still writes a
`gateway_requests` row with `status=failed` and the limit error code. Those rows are
included in legacy daily/monthly aggregates and therefore **count toward request
totals** the same way other failed gateway calls do.

**Recommended direction (v0.8+):** blocked 429 admission attempts should **not** create
limit reservations (they never reach `reserve_gateway_request`), but may still log a
failed `gateway_requests` row for audit. They should **not** increase completed
reservation counters. Today, treat legacy aggregate totals as observational when
debugging admission.

## Concurrency

- **PostgreSQL:** `SELECT ... FOR UPDATE` on usage window rows serializes updates
  for strict semantics **when all gateway workers share one database**. Use Postgres
  in production for predictable row locking.
- **Process-local asyncio lock:** an `asyncio.Lock` per project serializes the
  **reserve** step within a single process only. It does **not** coordinate across
  workers or hosts. Multi-worker strictness still depends on database row locks
  (Postgres) plus a shared database.
- **SQLite:** weaker under true multi-connection concurrency. Tests use a shared
  in-memory pool (`StaticPool`). The per-project asyncio lock still helps avoid
  interleaving reserve vs `start_request` within one process.

## Stale reservations (v0.8)

If a process crashes after reserving usage but before reconcile, counters can remain
inflated. v0.8 adds **listing, classification, dry-run, and apply repair** (admin API,
back office, and CLI). See [stale-limit-reservation-repair.md](stale-limit-reservation-repair.md).

Orphan reservations (no `gateway_requests` row) **release** reserved slots/tokens/cost
without counting a completed request. Failed/completed gateway rows are **reconciled**
using the same rules as the live gateway path.

## Reconciliation

Each successful or failed gateway completion calls `reconcile_gateway_request` with
the reservation id from `gateway_requests.limit_reservation_id`. Reconcile is
idempotent (`reconciled_at` on the reservation row).

## Deployment notes

- Use **PostgreSQL** in production for predictable row locking.
- Run **Alembic** migrations (`0003_project_usage_windows_and_reservations`) before
  rolling out v0.7.
- If **hard monthly cost limits** are enabled, keep `pricing.yaml` (or overrides)
  aligned with models you expose to clients.
- For multi-replica admin login rate limiting, use a distributed backend when
  implemented; today only `in_memory` is wired.

See also [hard-limit-concurrency.md](hard-limit-concurrency.md) for v0.6 vs v0.7 history.
