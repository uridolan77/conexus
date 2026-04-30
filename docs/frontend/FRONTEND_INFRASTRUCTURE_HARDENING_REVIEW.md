# Frontend Infrastructure Hardening Review

**Date:** 2026-04-30  
**Pass:** Hardening Pass 2 — infrastructure only, no new feature pages.

---

## Architecture summary

Next.js 14 app-router, React 18, TypeScript 5.5. Zero external runtime dependencies beyond Next/React. CSS custom properties design system (no Tailwind, no shadcn, no MUI). Vitest + Testing Library for tests.

Pages live in `app/` (app router). Shared logic lives in `lib/`. Domain API modules live in `lib/admin/`. Components live in `components/`.

---

## Navigation model

`lib/navigation.ts` exports `NAV_SECTIONS` — a typed array of `{ label, items: NavItem[] }`. `AppShell` + `Sidebar` read it. No hardcoded nav in components. Pages are in: Gateway (dashboard, projects, providers, requests, usage, routing), Operations (audit, smoke-tests, stale-reservations), Adaptation (plans, runs, profiles, queue).

---

## API client model

`lib/api.ts` exposes:
- `BACKEND_BASE` — env-aware backend origin
- `adminSessionFetch` — cookie-authenticated fetch with 401 → login redirect
- `readJsonSafe` — safe JSON parse, returns `null` on empty body
- `parseApiError` — normalizes FastAPI validation arrays, nested detail, status codes into `ApiError`
- `AdminResult<T>` — `{ ok: true; data: T } | { ok: false; error: ApiError }`
- `buildQuery` — query string builder, skips null/undefined/"" (added Pass 2)
- `getAdminJson`, `postAdminJson`, `putAdminJson`, `deleteAdminJson` — typed helpers, all now accept `{ signal? }` option (added Pass 2)
- Path safety: helpers reject absolute `http(s)://` URLs with a clear error (added Pass 2)

---

## Domain API modules (`lib/admin/`)

| Module | Owns |
|---|---|
| `projects.ts` | listProjects, createProject, keys (issue/revoke), limits (get/save/usage/reservations), getStaleReservations |
| `providers.ts` | listProviders, createProvider, revokeProvider, testProvider, **listProviderCandidates** (canonical owner) |
| `routing.ts` | getRoutingPolicy, getModelAliases; re-exports listProviderCandidates as getProviderCandidates |
| `requests.ts` | listRequests, getRequest |
| `audit.ts` | listAuditLogs |
| `usage.ts` | getUsageSummary, getUsageByProject, getUsageByProvider, getUsageTimeseries |

All functions return `Promise<AdminResult<T>>`. All query params built with `buildQuery` (Pass 2). No business logic inside modules.

---

## Data-fetching hook (`lib/useAdminResource.ts`)

Added Pass 2. Lightweight internal hook for admin pages:
- `ResourceState<T>`: `{ data, loading, error, reload, setData }`
- Unmount guard via `mountedRef`
- Stale-response guard via generation counter
- No caching, no redirect handling (API layer does that)
- No external dependencies
- Use for all new pages. Migrating existing pages is optional.

---

## Formatting utilities (`lib/format.ts`)

`formatDateTime`, `formatCost`, `formatPercentRatio`, `formatPercentValue`, `formatTokens`, `formatLatency`, `formatDurationSeconds`, `formatNullable`, `computePercent`. See `BO_FRONTEND_CONVENTIONS.md` for usage table.

---

## UI primitives (`components/ui/index.tsx`)

Pass 2 additions and changes:
- **CopyButton**: now shows "Copy failed" on clipboard + execCommand failure; `onCopied`/`onError` callbacks
- **PageState**: added `action` prop (passed to EmptyState)
- **DataTable**: added `emptyMessage?: ReactNode` for empty rows
- **DetailDrawer**: switched from `aria-label` to `aria-labelledby` pointing to title h3 (via `useId`)
- **New primitives**: `FieldError`, `HelpText`, `CodeChip`, `StatusPill`, `SectionGap`

---

## CSS (`app/globals.css`)

Pass 2 additions:
- `.page-stack` — vertical grid of page sections
- `.toolbar-spread` — toolbar with space-between alignment
- `.inline-meta` — small inline metadata cluster
- `.data-state` — padding container for loading/error/empty regions
- `.field-error` — red validation text
- `.help-text` — muted helper text

Existing from Pass 1: `.toolbar`, `.filter-bar`, `.progress-bar*`, `.drawer*`, `.code-chip`, `.copyable-code`, `.section-gap`.

Responsive breakpoints: sidebar collapses at 900px; nav list folds to 1 column at 560px; tables always overflow-x scroll.

---

## Projects page (`app/projects/page.tsx`)

Pass 2 fixes:
- All section fetch errors use `setPageError(msg)` which also calls `setSuccess(null)` — success messages now clear when a new error occurs
- Selecting a project already cleared `latestIssuedKey` via `useEffect` (confirmed, no change needed)
- Revoke key already calls `fetchKeys` + `fetchProjects` (confirmed)
- Limits save already calls `fetchProjects` + `fetchUsage` + `fetchReservations` (confirmed)

---

## Test coverage

**21 test files, 145 tests** passing after Pass 2.

Pass 2 added:
- `test/lib/api.buildQuery.test.ts` — 9 cases (null skips, encoding, empty, multi-param)
- `test/lib/api.requestAdminJson.test.ts` — 7 cases (path safety, empty response, signal, network error)
- `test/lib/useAdminResource.test.ts` — 8 cases (success, failure, reload, unmount guard, initialData)
- `test/components/page-state.test.tsx` — 7 cases (loading, error, empty, action, children)
- `test/components/detail-drawer.test.tsx` — 7 cases (closed, open, close button, backdrop, Escape, aria-labelledby)
- `test/components/data-table.test.tsx` — 5 cases (headers, rows, emptyMessage)
- `test/components/copy-button.test.tsx` — 4 new cases (failure state, onCopied, onError callbacks)
- `test/projects/projects.switching.test.tsx` — 2 cases (key not shown, page renders)

---

## Reusable BO conventions

Documented in `docs/BO_FRONTEND_CONVENTIONS.md`. Key points:
1. Page structure: PageHeader → ErrorState → Card → SectionHeader → PageState → content
2. Data: use domain modules + AdminResult<T>; use `useAdminResource` for new pages
3. Errors: parseApiError; never render raw objects; secrets rules
4. Formatting: only `lib/format.ts` functions; no local formatters
5. Primitives: `DataTable` with emptyMessage; `DetailDrawer` with Escape+backdrop close; `CopyButton` with failure feedback
6. Tests: utility, component (empty/error/loaded), user-flow (one mutation test per page)

---

## Remaining gaps

- **ESLint** not configured — needed before extracting as reusable package
- **DetailDrawer** has no focus trap — documented, not yet built
- **`window.confirm`** used in `ConfirmAction` — acceptable for now
- **No React Query / SWR** — `useAdminResource` covers immediate needs
- **No design-token package extraction** — post-MVP
- **`useAdminResource` migration** of existing pages deferred — opt-in as pages are touched
