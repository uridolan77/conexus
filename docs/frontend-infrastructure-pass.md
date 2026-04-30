## Current frontend assessment

The foundation is decent but uneven.

The app is already wrapped in a global `AppShell`, and `/login` correctly bypasses the BO shell.   The sidebar is centralized and already contains more routes than the screenshot shows, including Audit, Usage, Routing, Smoke Tests, and Adaptation pages. 

There is a useful shared UI component file with `PageHeader`, `Card`, `Button`, `Field`, `Table`, `CopyButton`, `JsonBlock`, `Stepper`, `ConfirmAction`, etc.  The CSS already has a strong token system and responsive shell/table/card styling.  The API helper exists, but it is still thin: `adminSessionFetch`, `readJsonSafe`, `formatApiError`, `formatDate`.  Types are centralized and already cover projects, providers, usage, routing, requests, audit logs, project limits, and reservations. 

The main weakness is that **page logic is too heavy and repetitive**. For example, the Projects page currently mixes project CRUD, key management, project limits, usage windows, stale reservations, formatting helpers, parsing helpers, forms, tables, and progress bars in one very large component.  That works now, but it will become painful when we add more BO pages.

The testing setup is good enough to expand: TypeScript is strict, Vitest runs with jsdom, and Testing Library cleanup is configured.    The known gap remains ESLint: `package.json` has `"lint": "next lint"` but ESLint dependencies/config are missing, so lint should not be forced until we add config. 

---

# What “make it perfect” means before adding pages

Do this as a **frontend infrastructure pass**, not a feature pass.

## Target improvements

1. **Navigation model**

   * Move sidebar links into a typed navigation config.
   * Group links into sections: Overview, Operations, Routing, Adaptation, System.
   * Make active route handling consistent.
   * Hide or mark pages that are not implemented yet.

2. **UI primitives**

   * Split `components/ui/index.tsx` into smaller files or at least harden the exports.
   * Add missing primitives:

     * `PageState`
     * `Toolbar`
     * `FilterBar`
     * `DetailDrawer`
     * `DataTable`
     * `MetricCard`
     * `InlineCode`
     * `CopyableCode`
     * `RefreshButton`
     * `ConfirmButton`
   * Remove inline styles from pages and move reusable styles into CSS classes.

3. **API client**

   * Replace ad hoc `fetch` handling with typed helpers:

     * `getAdminJson<T>()`
     * `postAdminJson<T>()`
     * `putAdminJson<T>()`
     * `deleteAdminJson<T>()`
     * `parseApiError()`
   * Normalize errors into one shape.
   * Preserve automatic redirect on 401.
   * Never accidentally log or render secret values.

4. **Formatting utilities**

   * Move all formatting to `lib/format.ts`:

     * date/time
     * cost
     * percent
     * tokens
     * latency
     * duration
     * null/empty values
     * status labels

5. **Domain-specific API modules**

   * Create:

     * `lib/admin/projects.ts`
     * `lib/admin/providers.ts`
     * `lib/admin/requests.ts`
     * `lib/admin/usage.ts`
     * `lib/admin/audit.ts`
     * `lib/admin/routing.ts`
     * later: `lib/admin/adapterProfiles.ts`
   * Pages should call functions, not hand-build URLs everywhere.

6. **Projects page decomposition**

   * Split the huge Projects page into:

     * `ProjectCreateCard`
     * `ProjectListCard`
     * `ProjectKeysCard`
     * `ProjectLimitsCard`
     * `ProjectUsageCard`
     * `StaleReservationsSummary`
   * Do not change behavior yet.
   * Preserve current UI functionality exactly.

7. **Test infrastructure**

   * Add tests for shared components.
   * Add tests for API error parsing.
   * Add tests for formatting.
   * Add smoke tests for navigation/sidebar.
   * Add a regression test that project API key plaintext is only displayed in the latest-issued-key state.

8. **Documentation**

   * Create `docs/frontend/FRONTEND_FOUNDATION_REVIEW.md`.
   * Create `docs/frontend/FRONTEND_FOUNDATION_CHANGELOG.md`.

---

# Cursor prompt: Frontend foundation hardening

Paste this into Cursor before adding any new pages.

```md id="mzv853"
You are working in the `conexus` repository.

Goal: perform a frontend foundation hardening pass before adding new BO pages.

Do not add major new pages yet. Do not redesign the product. Do not change backend APIs unless a tiny read-only support fix is unavoidable. This pass is about making the frontend infrastructure clean, consistent, testable, and ready for expansion.

Current frontend facts:
- Next.js app lives in `frontend/`.
- Global layout uses `AppShell`.
- Sidebar is in `frontend/components/bo/Sidebar.tsx`.
- Shared UI primitives are in `frontend/components/ui/index.tsx`.
- API helpers are in `frontend/lib/api.ts`.
- Types are in `frontend/lib/types.ts`.
- Styling is mostly in `frontend/app/globals.css`.
- Projects page is already large and mixes many responsibilities.
- `npm test -- --run` and `npm run build` should pass.
- Do not add lint to CI yet unless ESLint is actually installed/configured.

Primary objectives:

1. Navigation foundation
   - Extract sidebar links into a typed navigation config, e.g. `frontend/lib/navigation.ts`.
   - Group links into sections:
     - Overview
     - Operations
     - Routing
     - Adaptation
     - System
   - Preserve all currently working links.
   - Mark unavailable/unimplemented links clearly if needed.
   - Keep active-route logic correct.
   - Do not create new pages just to satisfy links in this pass unless they already exist.

2. API client foundation
   - Strengthen `frontend/lib/api.ts`.
   - Add typed helpers:
     - `getAdminJson<T>()`
     - `postAdminJson<TBody, TResult>()`
     - `putAdminJson<TBody, TResult>()`
     - `deleteAdminJson<TResult>()` if useful
     - `requestAdminJson<T>()`
   - Add a normalized `ApiError` / `ApiFailure` shape.
   - Add `parseApiError()` that handles:
     - FastAPI `{ detail: "..." }`
     - FastAPI validation arrays
     - `{ detail: { code, message } }`
     - plain text
     - empty response
     - network errors
   - Keep 401 redirect behavior for admin calls.
   - Do not leak secrets in error rendering.

3. Formatting foundation
   - Create `frontend/lib/format.ts`.
   - Move reusable formatters there:
     - `formatDateTime`
     - `formatCost`
     - `formatPercent`
     - `formatTokens`
     - `formatLatency`
     - `formatNullable`
     - `formatDurationSeconds`
   - Replace page-local duplicate formatting where safe.
   - Keep output stable and readable.

4. UI primitives hardening
   - Improve shared components without changing visual identity.
   - Add small reusable primitives if missing:
     - `Toolbar`
     - `FilterBar`
     - `DetailDrawer`
     - `DataTable` or table helper wrappers
     - `RefreshButton`
     - `InlineCode`
     - `CopyableCode`
     - `PageState`
   - Make components accessible:
     - buttons have type where appropriate
     - tables have aria-label
     - alerts use correct role
     - drawer/dialog can be closed by button and Escape if implemented
   - Do not introduce a large UI library.
   - Avoid inline styles in page components; prefer CSS classes.

5. CSS/token cleanup
   - Keep current design language.
   - Add missing utility classes needed to remove repeated inline styles:
     - progress bar
     - inline metadata row
     - toolbar
     - filter grid
     - drawer
     - code/value chips
     - section spacing
   - Preserve responsive behavior.
   - Do not switch to Tailwind or another styling system.

6. Projects page decomposition
   - Refactor `frontend/app/projects/page.tsx` into smaller components without changing behavior.
   - Suggested split:
     - `ProjectCreateCard`
     - `ProjectListCard`
     - `ProjectKeysCard`
     - `ProjectLimitsCard`
     - `ProjectLimitUsageCard`
     - `ProjectReservationsCard`
   - Keep the page route and visible behavior the same.
   - Preserve:
     - create project
     - select project
     - issue key
     - show plaintext key once
     - copy key
     - revoke key
     - view/update limits
     - view usage/reservation counters
   - Do not lose any current function.

7. Test improvements
   - Add tests for:
     - API error parser
     - format helpers
     - Sidebar active links/groups
     - CopyButton / CopyableCode behavior where feasible
     - Projects page key-created “shown once” behavior if practical
   - Do not over-test implementation details.
   - Keep tests fast and deterministic.

8. Documentation
   Create:
   - `docs/frontend/FRONTEND_FOUNDATION_REVIEW.md`
   - `docs/frontend/FRONTEND_FOUNDATION_CHANGELOG.md`

   Include:
   - current frontend architecture
   - components inventory
   - API helper model
   - navigation model
   - known gaps
   - what changed
   - what is ready for page expansion
   - remaining risks

Constraints:
- Do not add Playground, Activity, Usage, Adapter Profiles, or Settings as full new feature pages in this pass.
- Do not change backend endpoints unless absolutely necessary.
- Do not display or persist full secrets.
- Do not store project API keys in localStorage.
- Keep current Projects page behavior working.
- Do not introduce a large dependency.
- Run validation.

Validation:
From `frontend/` run:
- `npm test -- --run`
- `npm run build`

Do not run `npm run lint` unless ESLint has been properly installed/configured.

Final response:
1. Files changed.
2. Infrastructure improvements made.
3. Behavior preserved.
4. Tests added.
5. Validation results.
6. Remaining frontend foundation gaps.
```

---

# Specific review notes for the agent

Tell Cursor to watch these exact risks:

```md id="ae4x9x"
## Specific risks to watch

1. Projects page is too large.
   It currently combines project creation, key management, limits, usage counters, stale reservations, parsing, formatting, and table rendering. Refactor by extraction only; do not change behavior.

2. API error handling is inconsistent.
   Some pages set generic `"Unable to load..."` messages and discard backend details. Introduce a safe normalized error parser.

3. Formatting is scattered.
   Dashboard and Projects have local formatters. Move reusable formatting into `lib/format.ts`.

4. Sidebar links may point to routes that are not implemented yet.
   Do not create fake pages. Add a navigation config that can mark route status or group pages clearly.

5. UI primitives are all in one file.
   This is acceptable for now, but the exports should be consistent and reusable. If splitting is low-risk, split. If not, keep one barrel but organize sections clearly.

6. Avoid inline styles.
   Projects page uses inline progress-bar styles. Move these to CSS classes.

7. CopyButton assumes `navigator.clipboard` exists.
   Add safe fallback or graceful error handling for non-secure contexts/tests.

8. ConfirmAction uses `window.confirm`.
   Acceptable for now, but wrap it as `ConfirmButton`/`ConfirmAction` with stable behavior and tests.

9. Secret handling must remain strict.
   API key plaintext may appear only immediately after issue. Provider secrets must never be shown.

10. Build must remain clean.
   This pass is not successful unless `npm test -- --run` and `npm run build` pass.
```

---

# My recommended frontend foundation target

After this pass, the structure should look closer to:

```text id="0b4ytr"
frontend/
  app/
    layout.tsx
    globals.css
    page.tsx
    login/
    projects/
    providers/
    requests/
    ...
  components/
    bo/
      AppShell.tsx
      Sidebar.tsx
      navigation.tsx optional
    projects/
      ProjectCreateCard.tsx
      ProjectListCard.tsx
      ProjectKeysCard.tsx
      ProjectLimitsCard.tsx
      ProjectUsageCard.tsx
    ui/
      index.tsx
      or split:
      buttons.tsx
      cards.tsx
      table.tsx
      states.tsx
      drawer.tsx
  lib/
    api.ts
    format.ts
    navigation.ts
    types.ts
    admin/
      projects.ts
      providers.ts
      requests.ts
      usage.ts
      audit.ts
```

The goal is not “beautiful code for its own sake.” The goal is that when we add Playground, Requests detail, Activity, Usage, Adapter Profiles, and Settings, every page uses the same reliable foundations.

Start with this pass. Then adding pages will be much faster and much less messy.
