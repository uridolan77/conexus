# Prompt — BO Frontend Infrastructure Hardening Pass

````md id="l8bx20"
You are working in the `conexus` repository.

Goal: perform one more frontend infrastructure hardening pass so this frontend can serve as a reusable BO foundation for Conexus and future BO/admin systems.

Do not add feature pages yet. Do not implement Playground, Activity, Adapter Profiles, Settings, or other new BO pages in this pass. This is infrastructure only.

Context:
The previous foundation passes added:
- typed navigation config
- grouped sidebar
- typed admin API helpers
- `lib/format.ts`
- `lib/admin/*` domain API modules
- decomposed Projects components
- shared UI primitives
- tests for formatting, API parsing, sidebar, copy button, and Projects behavior
- docs under `docs/frontend/`

Prompt A correction pass already fixed:
- percent ratio formatting
- `formatDate` delegation
- unsupported `deleteProject`
- Projects page load-error visibility

Now we want to make the frontend infrastructure cleaner, more consistent, more reusable, and safer before building more BO pages.

Validation required:
From `frontend/`:
- `npm test -- --run`
- `npm run build`

Do not run or enforce `npm run lint`; ESLint is not configured yet.

Hard constraints:
- No new feature pages.
- No backend endpoint changes.
- No large UI library.
- No Tailwind/shadcn/MUI/Radix.
- No React Query/SWR in this pass unless explicitly justified and very low-risk. Prefer small internal hooks first.
- Do not store secrets in localStorage/sessionStorage.
- Do not expose provider keys or internal keys.
- Project API key plaintext may only be shown immediately after creation.
- Preserve all existing frontend behavior.
- Keep diffs focused and reviewable.

---

## Phase 1 — BO infrastructure inventory

Review current frontend infrastructure and create/update:

`docs/frontend/FRONTEND_INFRASTRUCTURE_HARDENING_REVIEW.md`

Include:

1. Current architecture summary.
2. Navigation model.
3. API client model.
4. Domain API modules.
5. Formatting utilities.
6. UI primitives.
7. Projects decomposition.
8. Test coverage.
9. Known risks.
10. What should become reusable BO conventions.

Do not just repeat the existing foundation review. This should be a critical infrastructure review focused on reuse across future BOs.

---

## Phase 2 — Establish reusable BO conventions

Create:

`docs/frontend/BO_FRONTEND_CONVENTIONS.md`

This should be a practical handbook for future BO pages.

Include conventions for:

### Page structure

Every BO page should follow this pattern:

```tsx
<PageHeader ... />

{pageError && <ErrorState message={pageError} />}

<Card>
  <SectionHeader ... />
  <PageState loading={...} error={...} empty={...}>
    ...
  </PageState>
</Card>
````

### Data fetching

Pages should not hand-build URLs where a domain API module exists.

Preferred pattern:

```ts
const result = await listProjects();
if (!result.ok) {
  setError(result.error.message);
  return;
}
setProjects(result.data);
```

### Error handling

* Use `AdminResult<T>`.
* Use `parseApiError`.
* Do not render raw unknown objects directly except in explicit debug JSON blocks.
* Do not render secrets from errors.

### Formatting

Use:

* `formatDateTime`
* `formatCost`
* `formatPercentRatio`
* `formatPercentValue`
* `formatTokens`
* `formatLatency`
* `formatNullable`
* `formatDurationSeconds`

Never create local page-level formatters unless the format is genuinely page-specific.

### Tables

Use:

* normal JSX `<Table>` for complex tables
* `DataTable` only for simple read-only tables

### Drawers

Use `DetailDrawer` for row details, but document:

* current limitation: no focus trap yet
* must include close button
* must not show secrets

### Secrets

Rules:

* provider secret: never display
* project API key plaintext: display once after creation only
* internal API key: never display
* auth/encryption secrets: never display
* copied values must be explicit user action only

### Testing

For every new BO page:

* utility tests for pure functions
* component test for empty/error/loaded states
* at least one user-flow test when a form mutates data

---

## Phase 3 — API client hardening

Review `frontend/lib/api.ts`.

Improve safely:

1. Add path safety:

   * `requestAdminJson` should accept relative admin paths such as `/admin/projects`.
   * Reject or safely handle accidental absolute URLs unless intentionally allowed.
   * Do not allow an accidental double backend base like `http://localhost:8000http://...`.

2. Add query helper:

   * `buildQuery(params: Record<string, string | number | boolean | null | undefined>): string`
   * It should skip null/undefined/empty-string values.
   * It should return `""` if no params.
   * It should return `"?a=1&b=x"` otherwise.

3. Add typed no-content handling:

   * Some endpoints may return empty 204 or empty body.
   * `requestAdminJson<void>` should not fail on empty response.
   * Keep behavior compatible with current code.

4. Add optional request options:

   * `requestAdminJson<T>(path, { method, body, signal })`
   * Preserve existing helper signatures.
   * Support `AbortController` in future pages.

5. Improve error parser:

   * Ensure FastAPI validation arrays produce readable messages.
   * Include status in `ApiError`.
   * Never stringify large detail into `message`.
   * Keep raw detail separately.

Add/update tests:

* relative path behavior
* query builder skips null/undefined/empty
* empty response handling
* validation-array parsing
* network error handling

Do not break existing callers.

---

## Phase 4 — Add lightweight data-fetching hooks

Create:

`frontend/lib/useAdminResource.ts`

Do not add external dependencies.

Provide small internal hooks:

```ts
type ResourceState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setData: React.Dispatch<React.SetStateAction<T | null>>;
};
```

Implement:

```ts
useAdminResource<T>(
  loader: () => Promise<AdminResult<T>>,
  deps: React.DependencyList,
  options?: {
    initialData?: T | null;
    loadOnMount?: boolean;
  }
): ResourceState<T>
```

Requirements:

* Handles loading/error/data consistently.
* Prevents state update after unmount.
* Guards against stale responses overwriting newer responses.
* Does not swallow errors.
* Does not redirect manually; admin API layer handles 401.
* No caching yet.

Add tests:

* successful load sets data
* failed load sets error
* reload works
* stale response does not overwrite newer response if feasible
* no state update after unmount if feasible

Do not migrate all pages to this hook yet. Migrate one low-risk component/page only if it clearly improves code. Otherwise document it as ready for future pages.

---

## Phase 5 — UI primitive tightening

Review `frontend/components/ui/index.tsx`.

Do not over-abstract.

Improve safely:

### CopyButton

* Current fallback uses `document.execCommand("copy")`.
* Keep fallback, but handle failure gracefully.
* Add optional `onCopied` and `onError` callbacks if useful.
* Do not throw UI-breaking errors if copy fails.
* Button should show:

  * `Copied` on success
  * `Copy failed` briefly on failure, if feasible

### PageState

Make it more generally useful:

* `loading`
* `error`
* `empty`
* `emptyTitle`
* `emptyBody`
* `children`
* optional `action`
* optional `loadingLabel`

### DetailDrawer

Tighten without overbuilding:

* Escape closes.
* Backdrop closes.
* Close button has accessible label.
* Body scroll works.
* Add `aria-labelledby` instead of only `aria-label` if simple.
* Document no focus trap yet.

### DataTable

Keep it lightweight:

* Make empty rows easy:

  * `emptyMessage?: ReactNode`
* Do not force all pages to use it.
* Confirm row keys are stable.

### New tiny primitives if useful

Add only if low-risk:

* `FieldError`
* `HelpText`
* `CodeChip`
* `StatusPill` alias around `Badge`
* `SectionGap`

Update tests:

* CopyButton success and failure/fallback.
* PageState loading/error/empty/content.
* DetailDrawer closes on Escape and close button.
* DataTable empty state if implemented.

---

## Phase 6 — CSS hardening

Review `frontend/app/globals.css`.

Goals:

* Keep current visual identity.
* Make spacing and page composition more consistent.
* Remove need for inline styles in future pages.

Add/refine classes:

```css
.page-stack
.section-gap
.toolbar
.toolbar-spread
.filter-bar
.inline-meta
.progress-bar
.progress-bar-fill
.progress-bar-fill-danger
.code-chip
.copyable-code
.drawer
.drawer-backdrop
.drawer-panel
.drawer-header
.drawer-body
.data-state
```

Check responsive behavior:

* Sidebar on small screens.
* Tables overflow horizontally.
* Drawers fit mobile widths.
* Cards do not overflow.

Do not perform a full redesign.

---

## Phase 7 — Domain module consistency pass

Review all files under:

`frontend/lib/admin/`

Make them consistent.

Rules:

* All functions return `Promise<AdminResult<T>>`.
* All URL construction uses `buildQuery` where query params exist.
* No business/UI logic in domain modules.
* No unsupported endpoints.
* Function names should be predictable:

  * `listX`
  * `getX`
  * `createX`
  * `updateX`
  * `testX`
  * `revokeX`
  * `repairX`
* Remove duplicates if obvious and safe.
* If two modules need the same endpoint, document ownership or re-export one from the other.

Pay attention to:

* provider candidates duplicated between providers/routing modules
* requests/audit pagination query construction
* usage window query construction
* stale reservations query construction

Add tests for domain modules only where practical by mocking `fetch`.

---

## Phase 8 — Projects page final tightening

Review:

* `frontend/app/projects/page.tsx`
* `frontend/components/projects/*`

Goals:

* Preserve behavior.
* Reduce duplicated loading/error boilerplate only if safe.
* Ensure all section fetch failures are visible.
* Ensure success messages clear when a new error occurs, if appropriate.
* Ensure selecting a project clears stale latest-issued-key.
* Ensure project creation auto-selects the created project reliably.
* Ensure key plaintext is not shown after switching projects.
* Ensure revoking key refreshes key list and project list.
* Ensure limits save refreshes usage and reservations.

Do not redesign Projects.

Add/adjust tests if needed:

* switching projects clears latest key
* create project auto-selects
* failed section load shows error
* revoking key calls refresh callbacks

---

## Phase 9 — Documentation update

Update:

* `docs/frontend/FRONTEND_FOUNDATION_REVIEW.md`
* `docs/frontend/FRONTEND_FOUNDATION_CHANGELOG.md`

Create:

* `docs/frontend/FRONTEND_INFRASTRUCTURE_HARDENING_REVIEW.md`
* `docs/frontend/BO_FRONTEND_CONVENTIONS.md`

Include:

* what changed
* what is now reusable across BOs
* what remains intentionally simple
* what not to do when adding pages
* remaining gaps:

  * ESLint not configured
  * no React Query/SWR
  * DetailDrawer no focus trap
  * window.confirm still used
  * no design-token extraction into package yet

---

## Phase 10 — Validation

Run from `frontend/`:

```bash
npm test -- --run
npm run build
```

Do not run `npm run lint`.

Final response:

1. Files changed.
2. Infrastructure improvements made.
3. Bugs or risks fixed.
4. Tests added/updated.
5. Validation results.
6. Whether the frontend is now ready for adding pages.
7. Remaining gaps before extracting this as a reusable BO template/package.

````

---

## My recommendation

Run that as a **single infrastructure pass**, not a page-building pass.

After it passes, the next prompt should be much smaller:

```text
Implement Playground only, using BO conventions.
````

Then:

```text
Implement Requests explorer.
```

Then:

```text
Implement Activity/Audit.
```

This will keep the frontend from turning into another vibe-coded pile.
