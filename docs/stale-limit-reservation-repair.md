# Stale limit reservation repair (v0.8)

## What “stale” means

A **stale** row is a `project_gateway_limit_reservations` record with:

- `reconciled_at IS NULL`
- `created_at` older than the configured stale threshold (default **900s** via `LIMIT_RESERVATION_STALE_AFTER_SECONDS`)

These appear when the gateway process stops between **reserve** and **reconcile** (crash, kill, deploy), or when reconciliation never ran despite a terminal `gateway_requests` row.

## Classification

| Situation | Repair kind | Typical action |
|-----------|-------------|----------------|
| No `gateway_requests` row linked by `limit_reservation_id` | `no_gateway_request` | **Release** reserved counters; do **not** increment completed request count |
| Gateway request `failed` | `gateway_request_failed` | Reconcile like a normal failure (request slot → completed; tokens/cost from actuals, usually 0) |
| Gateway request `completed` but reservation still open | `gateway_request_completed_without_reconcile` | Reconcile using logged tokens and estimated cost |
| Gateway request `started`, not completed, age &lt; force threshold | `gateway_request_started_but_not_completed` | **Skip** automatic apply; review (e.g. long stream) |
| Same, age ≥ force threshold (default **3600s**, `LIMIT_RESERVATION_FORCE_REPAIR_AFTER_SECONDS`) | (same kind) | Mark request failed, then reconcile as failed |

Long-running **streaming** calls may look “started” for a long time; avoid setting the force threshold too low in production.

## Safe workflow

1. **List** stale reservations (BO or CLI).
2. **Dry-run** repair for a reservation to preview counter deltas.
3. **Apply** repair for clearly safe kinds (orphan release, failed, completed-without-reconcile).
4. Re-check **Project Limits → Admission counters** for the project.
5. If the same reservations keep appearing, investigate crashes or client retries.

## Admin API

- `GET /admin/projects/limits/reservations/stale` — query params: `project_id`, `older_than_seconds`, `limit`. Response includes `total_count`, `oldest_age_seconds`, and `items`.
- `POST /admin/projects/limits/reservations/{reservation_id}/repair/dry-run`
- `POST /admin/projects/limits/reservations/{reservation_id}/repair` — JSON body optional `{ "reason": "..." }`

All require an admin session. Actions are **audited**.

## CLI

From the `backend` directory (with `DATABASE_URL` and `ENCRYPTION_KEY` set):

```bash
python -m app.cli limits list-stale-reservations --older-than-seconds 900
python -m app.cli limits repair-stale-reservations --older-than-seconds 900 --dry-run
python -m app.cli limits repair-stale-reservations --older-than-seconds 900 --apply
```

Optional: `--project-id <id>`.

## Health checks

Stale reservations **do not** fail `/readyz`; they are operational noise, not deploy blockers.
