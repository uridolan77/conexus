# Frontend Foundation Review

This document captures the architecture, component inventory, and readiness state of the Conexus back-office frontend after the foundation hardening pass.

## Architecture

**Framework:** Next.js 14.2.5 (App Router)  
**Language:** TypeScript 5.5.3 (strict mode)  
**Styling:** Vanilla CSS with CSS custom properties (no Tailwind, no CSS-in-JS)  
**Testing:** Vitest 2.x + @testing-library/react + jsdom  
**State:** Local component state (`useState` + `useEffect`) — no external state manager  
**Auth:** Cookie-based session (`conexus_admin_session`); middleware enforces auth on all routes except `/login` and internal Next.js paths

## Directory Structure

```
frontend/
  app/
    layout.tsx            — Root layout (AppShell wrapping)
    globals.css           — Design tokens + all utility classes
    page.tsx              — Dashboard
    login/page.tsx        — Login (bypasses AppShell)
    projects/page.tsx     — Projects orchestrator (slim after decomposition)
    providers/page.tsx
    requests/page.tsx
    usage/page.tsx
    audit/page.tsx
    routing/page.tsx
    smoke-tests/page.tsx
    adaptation/
      plans/page.tsx  [id]/page.tsx
      runs/page.tsx   [id]/page.tsx
      profiles/page.tsx  [id]/page.tsx
      queue/page.tsx
  components/
    bo/
      AppShell.tsx        — Global layout shell
      Sidebar.tsx         — Sidebar (consumes navigation config)
    ui/
      index.tsx           — Shared UI primitives barrel
    projects/
      ProjectCreateCard.tsx
      ProjectListCard.tsx
      ProjectKeysCard.tsx
      ProjectLimitsCard.tsx
      ProjectUsageCard.tsx
    adaptation/           — Adaptation-specific panels (pre-existing)
  lib/
    api.ts                — HTTP client, typed helpers, error parsing
    format.ts             — Formatting utilities
    navigation.ts         — Typed navigation config (sections + items)
    types.ts              — All domain types
    admin/
      projects.ts         — Project API functions
      providers.ts        — Provider API functions
      requests.ts         — Requests API functions
      usage.ts            — Usage API functions
      audit.ts            — Audit log API functions
      routing.ts          — Routing policy API functions
    adaptationApi.ts      — Adaptation-specific API client (pre-existing)
    adaptationTypes.ts    — Adaptation domain types (pre-existing)
    adaptationNormalize.ts — Adaptation data normalizers (pre-existing)
  middleware.ts           — Cookie session auth middleware
  test/
    lib/
      api.adminSessionFetch.test.ts
      api.adminSessionFetch.node.test.ts
      format.test.ts
      parseApiError.test.ts
    components/
      sidebar.test.tsx
      copy-button.test.tsx
    projects/
      key-shown-once.test.tsx
      stale-reservations.page.test.tsx
    middleware-matcher.test.ts
    requests.test.tsx
    usage.test.tsx
    adaptation.test.tsx
```

## API Client Model

**Transport:** `adminSessionFetch` (cookie credentials, auto-redirect on 401)

**Typed helpers:**
- `getAdminJson<T>(path)` → `AdminResult<T>`
- `postAdminJson<TBody, TResult>(path, body)` → `AdminResult<TResult>`
- `putAdminJson<TBody, TResult>(path, body)` → `AdminResult<TResult>`
- `deleteAdminJson<TResult>(path)` → `AdminResult<TResult>`

**Error model:**
```ts
type ApiError = { message: string; detail?: unknown; status?: number };
type AdminResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };
```

**Error parser:** `parseApiError(error, status?)` normalizes:
- FastAPI `{ detail: "string" }`
- FastAPI validation `{ detail: [{ msg, loc }] }`
- Nested `{ detail: { code, message } }`
- Plain string, Error instance, null/undefined, unknown shapes

**Domain API modules** in `lib/admin/` expose typed functions that pages call instead of hand-building URLs.

## Navigation Model

`lib/navigation.ts` exports `NAV_SECTIONS: NavSection[]` with four groups:

| Section | Routes |
|---|---|
| Overview | `/` |
| Operations | `/projects`, `/providers`, `/requests`, `/usage`, `/audit` |
| Routing | `/routing`, `/smoke-tests` |
| Adaptation | `/adaptation/plans`, `/adaptation/runs`, `/adaptation/queue`, `/adaptation/profiles` |

`Sidebar.tsx` renders group headings (`<p class="nav-group-label">`) and link lists from the config. Adding a new route only requires an entry in the config, not a Sidebar edit.

## Component Inventory

### Shared UI primitives (`components/ui/index.tsx`)

| Component | Purpose |
|---|---|
| `PageHeader` | Page title + eyebrow + description + optional actions |
| `SectionHeader` | Section title + description + optional actions |
| `Card` | Surface container |
| `Button` | Primary / secondary / danger / ghost variants |
| `LinkButton` | `<a>` styled as button |
| `Field` + `Input` + `Select` + `Textarea` + `FormRow` | Form primitives |
| `Badge` + `StatusBadge` | Tone-colored labels |
| `Alert` + `ErrorState` | Informational/error banners |
| `EmptyState` + `LoadingState` | Data state placeholders |
| `Table` | Accessible table wrapper |
| `CopyButton` | Copy-to-clipboard (with fallback) |
| `CopyableCode` | Inline code + copy button |
| `InlineCode` | `<code>` with chip styling |
| `SecretValue` | Styled secret display |
| `KeyValueGrid` | `<dl>` label/value pairs |
| `StatCard` + `MetricCard` | Metric displays (MetricCard adds delta) |
| `Stepper` | Step-by-step progress |
| `ConfirmAction` + `ConfirmButton` | `window.confirm` wrapper |
| `JsonBlock` | Collapsible raw JSON view |
| `PageState` | Loading / error / empty / content switcher |
| `Toolbar` | Horizontal action strip |
| `FilterBar` | Responsive filter grid |
| `RefreshButton` | Labeled refresh button |
| `DataTable` | Column-def driven table |
| `DetailDrawer` | Slide-in panel (keyboard + click dismissal) |

### Projects components (`components/projects/`)

| Component | Responsibility |
|---|---|
| `ProjectCreateCard` | Create project form with validation |
| `ProjectListCard` | Projects table + select action |
| `ProjectKeysCard` | Issue/revoke keys; plaintext shown once |
| `ProjectLimitsCard` | Limit mode + value form; syncs from parent |
| `ProjectUsageCard` | Usage bars + reservation counters + stale summary |

## Formatting Utilities (`lib/format.ts`)

| Function | Output |
|---|---|
| `formatDateTime(v)` | Intl medium date + short time; `"—"` for null |
| `formatCost(v)` | USD 4dp; `"—"` for null |
| `formatPercent(v)` | `"73%"`; `"—"` for null |
| `formatTokens(v)` | Comma-separated integer; `"—"` for null |
| `formatLatency(ms)` | `"<1ms"` / `"12ms"` / `"1.2s"`; `"—"` for null |
| `formatNullable(v)` | `"—"` for null/undefined/empty |
| `formatDurationSeconds(s)` | `"45s"`, `"2m 5s"`, `"1h 3m"` |
| `computePercent(current, limit)` | Capped at 999; null when limit absent |

## Known Gaps

1. **ESLint is not configured.** `package.json` has `"lint": "next lint"` but no ESLint packages are installed. Do not run `npm run lint` in CI until this is fixed.
2. **No React Query / SWR.** Data fetching uses raw `useEffect` + `useState`. As pages grow, consider adopting a data-fetching library.
3. **Projects page uses `window.confirm`** via `ConfirmAction`. Acceptable for now, but not accessible. A modal-based confirmation is the eventual target.
4. **No pagination in domain modules.** `listRequests` and `listAuditLogs` support offset/limit, but the UI pages manage their own cursor state.
5. **`lib/admin/providers.ts` duplicates `listProviderCandidates`** (also in `lib/admin/routing.ts`). These can be consolidated when providers/routing pages migrate to the domain modules.
6. **Pages have not yet been migrated to use domain modules.** The modules exist and are tested, but existing pages still call `adminSessionFetch` directly. Migrate incrementally when editing pages.

## Ready for Page Expansion

The following foundations are solid:
- Navigation: add an entry to `NAV_SECTIONS` in `lib/navigation.ts`
- API: call functions from `lib/admin/` or write a new `lib/admin/<domain>.ts`
- Formatting: use `formatCost`, `formatTokens`, `formatLatency`, etc. — no more local formatters
- UI: `PageState` wraps loading/error/empty; `Toolbar` + `FilterBar` for page controls; `DataTable` for tables; `DetailDrawer` for panels
- Tests: add to `test/lib/` for utilities, `test/components/` for components
