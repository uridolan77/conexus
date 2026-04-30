# Frontend Foundation Changelog

## 2026-04-30 - Post-hardening correction pass

### Correctness fixes

- Percent formatting now has explicit semantics in `frontend/lib/format.ts`:
  - `formatPercentRatio(0.73)` -> `"73.0%"`
  - `formatPercentValue(73)` -> `"73%"`
  - `formatPercent` now delegates to ratio semantics (`formatPercentRatio`) to align with backend ratio fields such as `success_rate`, `fallback_rate`, and `errorRate`.
- Legacy `formatDate` in `frontend/lib/api.ts` now delegates to `formatDateTime` in `frontend/lib/format.ts` while remaining exported for backward compatibility.
- Removed unsupported `deleteProject` helper from `frontend/lib/admin/projects.ts` because a confirmed backend delete endpoint is not part of the current contract.
- Restored visible load errors in `frontend/app/projects/page.tsx` for failed section fetches (`fetchKeys`, `fetchLimits`, `fetchUsage`, `fetchReservations`, `fetchStale`) without replacing the whole page with a hard-failure state.

### Test updates

- Updated `frontend/test/lib/format.test.ts` for ratio-aware percent formatting and explicit percent formatter coverage.
- Added `frontend/test/lib/api.formatDate.test.ts` to lock legacy date helper delegation behavior.
- Added `frontend/test/projects/projects.page.error-visibility.test.tsx` to verify section-fetch failures render a visible alert.

### Remaining known gaps

- ESLint is not configured yet (`npm run lint` remains intentionally disabled for CI).
- Data fetching still uses local `useState` + `useEffect` (no React Query/SWR).
- `window.confirm` is still used in projects actions.
- `DetailDrawer` supports dismissal but does not trap focus yet.
- Page migration to domain modules in `frontend/lib/admin/*` is still incremental.
