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
- **Monthly cost limit:** reservation uses `estimate_reservation_cost_usd`, which
  requires the model to exist in the pricing table. If the model is unknown and a
  hard monthly cost cap is set, the gateway returns `pricing_unavailable_for_hard_cost_limit`.
- **Failed / timed-out calls:** still consume the daily request reservation; token
  and cost reservations reconcile toward actuals (often zero).

## Concurrency

- **PostgreSQL:** `SELECT ... FOR UPDATE` on usage window rows serializes updates
  for strict semantics across workers sharing one database.
- **SQLite:** weaker under true multi-connection concurrency. Tests use a shared
  in-memory pool (`StaticPool`). In addition, an **asyncio lock per project**
  serializes the reserve step in-process so concurrent gateway tasks do not
  interleave between reservation commit and `start_request`.

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
