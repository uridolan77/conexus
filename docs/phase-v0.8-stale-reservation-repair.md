# Phase v0.8 — Stale reservation repair (implementation summary)

## Delivered

- **Config:** `LIMIT_RESERVATION_STALE_AFTER_SECONDS` (default 900, min 60), `LIMIT_RESERVATION_FORCE_REPAIR_AFTER_SECONDS` (default 3600, min 300).
- **Service:** `app/services/project_limit_reservation_repair_service.py` — `list_stale_reservations`, `count_stale_reservations`, `repair_stale_reservation` (dry-run / apply).
- **Release-only path:** `release_orphan_limit_reservation` in `app/services/project_limit_reservation_service.py` for reservations with no gateway request (no completed-request slot increment).
- **Admin routes** on `app/api/admin_project_limits.py` under `/admin/projects/limits/...`.
- **Audit:** `project.limit_reservation.repair_dry_run`, `repair_applied`, `repair_skipped`.
- **CLI:** `python -m app.cli limits list-stale-reservations` and `repair-stale-reservations`.
- **BO:** Projects page shows stale **count** and **oldest age**; `/projects/stale-reservations` lists rows with dry-run / repair.

## Not in scope

Redis, background workers, public `/v1/chat/completions` response changes, adaptation package.

## See also

- [stale-limit-reservation-repair.md](stale-limit-reservation-repair.md) — operator guide
- [phase-v0.8-Stale Reservation Repair + Operational Admin Tools.md](phase-v0.8-Stale%20Reservation%20Repair%20+%20Operational%20Admin%20Tools.md) — full design notes
