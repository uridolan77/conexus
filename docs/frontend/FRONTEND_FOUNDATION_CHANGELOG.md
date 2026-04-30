# Frontend Foundation Changelog

## 2026-04-30 - Infrastructure Hardening Pass 2

### API client (`lib/api.ts`)
- Added `buildQuery(params)` — builds query strings, skips null/undefined/"", returns "" or "?a=1&b=x"
- Added path safety: typed helpers reject absolute `http(s)://` paths with `ok: false` (prevents accidental double-base-URL bugs)
- Added `AdminRequestOptions` type with optional `signal?: AbortSignal`; all helpers (`getAdminJson`, `postAdminJson`, `putAdminJson`, `deleteAdminJson`) now accept it
- `readJsonSafe` already returned `null` on empty body — behavior confirmed, no change needed for 204

### Domain modules (`lib/admin/`)
- All manual `URLSearchParams` construction replaced with `buildQuery`
- `routing.ts` removed duplicate `getProviderCandidates`; now re-exports `listProviderCandidates` from `providers.ts` as `getProviderCandidates` for backward compatibility
- `providers.ts` is canonical owner of `listProviderCandidates`

### New: `lib/useAdminResource.ts`
- Lightweight internal data-fetching hook
- Handles loading/error/data state machine, unmount guard, stale-response guard
- No external dependencies, no caching

### UI primitives (`components/ui/index.tsx`)
- `CopyButton`: added failure state ("Copy failed"), `onCopied`/`onError` callbacks, graceful execCommand fallback
- `PageState`: added `action` prop (forwarded to `EmptyState`)
- `DataTable`: added `emptyMessage?: ReactNode` for full-width empty rows
- `DetailDrawer`: switched to `aria-labelledby` + `useId`; close button label changed to "Close"
- New primitives: `FieldError`, `HelpText`, `CodeChip`, `StatusPill`, `SectionGap`

### CSS (`app/globals.css`)
- Added: `.page-stack`, `.toolbar-spread`, `.inline-meta`, `.data-state`, `.field-error`, `.help-text`

### Projects page (`app/projects/page.tsx`)
- All section error paths now call `setPageError(msg)` which clears stale success messages alongside setting error

### New docs
- `docs/frontend/FRONTEND_INFRASTRUCTURE_HARDENING_REVIEW.md`
- `docs/frontend/BO_FRONTEND_CONVENTIONS.md`

### Tests added (21 files → 145 tests)
- `test/lib/api.buildQuery.test.ts` (9 tests)
- `test/lib/api.requestAdminJson.test.ts` (7 tests)
- `test/lib/useAdminResource.test.ts` (8 tests)
- `test/components/page-state.test.tsx` (7 tests)
- `test/components/detail-drawer.test.tsx` (7 tests)
- `test/components/data-table.test.tsx` (5 tests)
- Updated `test/components/copy-button.test.tsx` (+4 tests)
- `test/projects/projects.switching.test.tsx` (2 tests)

---

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
