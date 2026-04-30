
# Conexus BO UX Tightening Plan — Audit First, Then Implementation

You are working in the `conexus` repository.

Goal: perform a comprehensive UX review and produce a concrete tightening plan for the Conexus BO frontend.

Do **not** immediately redesign or implement broad changes. First inspect the current UI, repo structure, screenshots, and user comments. Then produce a prioritized UX plan that can be implemented safely in small phases.

The BO currently has functional pages for:

- Dashboard
- Projects
- Providers
- Playground
- Requests
- Usage
- Activity / Audit
- Health
- Settings
- Routing
- Adapter Profiles
- Limits
- Adaptation pages

The system is functionally usable, but the UX needs tightening: layout, spacing, table behavior, hierarchy, empty states, loading states, form density, page consistency, navigation clarity, and overall polish.

---

## Inputs

Use all available context:

1. Current frontend code.
2. Current BO conventions.
3. Screenshots provided by Uri.
4. Uri’s comments on what feels ugly, confusing, too dense, too empty, broken, or awkward.
5. Existing test/build constraints.

If screenshots are provided, review them page by page and reference the visible issues directly.

---

## Hard constraints

Do not:

- Add a large UI framework.
- Add Tailwind, shadcn/ui, MUI, Radix, Ant Design, Chakra, etc.
- Rewrite the app.
- Change backend endpoints unless absolutely necessary.
- Add new product features during the audit.
- Break existing behavior.
- Expose secrets.
- Store API keys in browser storage.
- Remove existing diagnostics/debug capability.
- Run or require `npm run lint` unless ESLint is configured.

Use existing frontend foundations:

- `components/ui/index.tsx`
- `app/globals.css`
- `lib/navigation.ts`
- `lib/api.ts`
- `lib/format.ts`
- `lib/admin/*`
- `lib/useAdminResource.ts`
- `lib/redaction.ts`
- `docs/frontend/BO_FRONTEND_CONVENTIONS.md`

Validation after any implementation phase:

```bash
cd frontend
npm test -- --run
npm run build
````

---

# Phase 1 — UX audit only

Inspect the current frontend and produce:

```text
docs/frontend/CONEXUS_BO_UX_AUDIT.md
```

Do not implement UI changes yet.

The audit must cover:

## 1. Global shell and navigation

Review:

* sidebar grouping
* active state clarity
* route naming
* density
* hierarchy
* mobile behavior
* whether “Smoke Tests” should still appear separately if it redirects to Playground
* whether Adaptation should be visually separated from Conexus gateway operations
* whether System pages are too hidden or too prominent

Questions to answer:

* Can a user understand where to go?
* Are pages grouped by mental model?
* Are there too many sidebar items?
* Are labels operationally clear?
* Is any route misleading?

## 2. Page-level hierarchy

For each page, review:

* page title
* eyebrow
* description
* primary action
* secondary actions
* first visible card
* whether the user understands what to do next

Pages to inspect:

```text
/
 /projects
 /providers
 /playground
 /requests
 /usage
 /activity
 /health
 /settings
 /routing
 /adapter-profiles
 /limits
 /adaptation/plans
 /adaptation/runs
 /adaptation/queue
 /adaptation/profiles
```

For each page, classify UX state:

```text
Good / Acceptable / Needs tightening / Confusing / Broken
```

## 3. Visual density and spacing

Review:

* card spacing
* table spacing
* form spacing
* vertical rhythm
* grid behavior
* too much unused space
* too much crammed information
* inconsistent gaps
* long code/ID fields
* wrapping behavior

Identify repeated CSS fixes that should become utilities.

## 4. Tables

Tables are likely the biggest issue.

Review every table for:

* horizontal overflow
* too many columns
* long IDs
* unreadable rows
* repeated copy buttons
* poor mobile behavior
* lack of sticky/contextual actions
* unclear primary column
* missing row detail affordance
* inconsistent status badges
* empty values shown inconsistently

Especially inspect:

* Requests table
* Adapter Profiles table
* Activity table
* Projects key table
* Usage breakdown tables
* Adaptation tables

Recommend for each table:

* keep table
* reduce columns
* move details into drawer
* add compact mode
* add column grouping
* add “important columns first”
* add responsive card layout
* add horizontal scroll improvements

## 5. Forms

Review forms for:

* too many fields visible at once
* unclear required/optional distinction
* poor validation timing
* unclear helper text
* button placement
* destructive action confirmations
* whether filters should be collapsible

Especially inspect:

* Projects create/key forms
* Providers forms
* Playground form
* Requests filters
* Activity filters
* Limits forms

Recommend:

* inline validation improvements
* compact filter layout
* collapsible advanced filters
* better primary/secondary button alignment
* clearer field hints

## 6. States

Review consistency of:

* loading states
* empty states
* error states
* success states
* partial failure states
* stale data after refresh
* disabled buttons
* “unknown” vs “—”
* null token/cost display

Every page should have:

```text
loading
empty
error
loaded
refresh/retry where useful
```

Identify pages that do not.

## 7. Detail drawers

Review:

* width
* readability
* close behavior
* title clarity
* sectioning
* JSON placement
* whether raw JSON overwhelms the page
* whether IDs are copyable
* whether metadata is redacted
* whether drawer should have tabs/sections

Especially inspect:

* Requests detail drawer
* Activity detail drawer
* Adapter Profile detail drawer

## 8. Status and semantic color

Review:

* badge consistency
* success/warning/danger/info usage
* status names
* whether warning banners are too visually loud
* whether all statuses are understandable

Recommend a status vocabulary:

```text
completed
failed
started
active
revoked
registered
canary
promoted
rolled_back
unknown
```

## 9. Operational clarity

For every page, answer:

* What is this page for?
* What should the operator do here?
* What is safe to click?
* What is dangerous?
* What is read-only?
* What indicates success?
* What indicates failure?
* What is merely diagnostic?

Flag ambiguous or misleading wording.

## 10. Accessibility and keyboard UX

Review lightweight accessibility issues:

* button labels
* aria labels
* table labels
* form labels
* drawer close behavior
* focus visibility
* color contrast
* keyboard navigation
* lack of focus trap in drawer

Do not overbuild accessibility yet, but create a practical backlog.

## 11. Responsive behavior

Review expected breakpoints:

* desktop 1440px
* laptop 1280px
* small laptop 1024px
* tablet-ish 768px

Identify:

* broken grids
* table overflow
* sidebar problems
* cards too narrow
* drawer width issues

## 12. Reusable BO template quality

Because this frontend may be reused for future BOs, identify:

* which components are reusable
* which are too Conexus-specific
* which CSS utilities should become generic
* which patterns should be documented
* what should not be abstracted yet

---

# Phase 2 — Produce a prioritized UX improvement plan

Create:

```text
docs/frontend/CONEXUS_BO_UX_TIGHTENING_PLAN.md
```

The plan must be structured as:

## P0 — UX bugs

Only include issues that block use or mislead the operator.

Examples:

* broken route
* table unusable due to overflow
* action appears to work but does nothing
* error hidden
* dangerous action unclear
* secret displayed
* page crashes

## P1 — High-value polish

Examples:

* Requests filters too dense
* Adapter Profiles table too wide
* raw JSON too prominent
* inconsistent status badges
* unclear empty states
* poor primary action placement

## P2 — Design-system improvements

Examples:

* standard page layout wrapper
* consistent table toolbar
* reusable filter panel
* compact ID display component
* metadata drawer sections
* status vocabulary

## P3 — Nice-to-have

Examples:

* saved filters
* keyboard shortcuts
* column visibility controls
* CSV export
* theme refinements

For each item include:

```text
ID:
Page/component:
Problem:
Impact:
Recommended fix:
Risk:
Files likely touched:
Test coverage:
Screenshot reference, if available:
```

---

# Phase 3 — Define implementation slices

Create a safe implementation roadmap.

Each slice must be small enough to review independently.

Suggested slices:

## Slice 1 — Global layout and navigation polish

Likely files:

```text
frontend/components/bo/Sidebar.tsx
frontend/lib/navigation.ts
frontend/app/globals.css
frontend/components/ui/index.tsx
```

Possible work:

* improve sidebar grouping
* improve active state
* reduce visual noise
* make redirected aliases less prominent
* add System group
* improve page max-width behavior

## Slice 2 — Table readability pass

Likely files:

```text
frontend/components/ui/index.tsx
frontend/app/globals.css
frontend/app/requests/page.tsx
frontend/app/activity/page.tsx
frontend/app/adapter-profiles/page.tsx
```

Possible work:

* compact ID component
* copyable ID cell
* table overflow utilities
* hidden low-priority columns
* better detail drawer usage
* consistent empty cells

## Slice 3 — Filter/forms pass

Likely files:

```text
frontend/app/requests/page.tsx
frontend/app/activity/page.tsx
frontend/app/playground/page.tsx
frontend/components/ui/index.tsx
frontend/app/globals.css
```

Possible work:

* collapsible advanced filters
* filter toolbar
* better validation
* clear/apply button placement
* active filter summary chips

## Slice 4 — Detail drawer/readability pass

Likely files:

```text
frontend/components/ui/index.tsx
frontend/app/requests/page.tsx
frontend/app/activity/page.tsx
frontend/app/adapter-profiles/page.tsx
```

Possible work:

* sectioned drawers
* better JSON placement
* copyable IDs
* metadata redaction display note
* drawer width rules

## Slice 5 — Page-by-page empty/error/loading states

Likely files:

```text
frontend/app/*/page.tsx
frontend/components/ui/index.tsx
```

Possible work:

* consistent `PageState`
* actionable empty states
* retry buttons
* partial failure banners
* stale data indicators

## Slice 6 — Visual finish

Likely files:

```text
frontend/app/globals.css
frontend/components/ui/index.tsx
```

Possible work:

* card hierarchy
* better spacing tokens
* badge consistency
* muted text consistency
* code chip styling
* dashboard cards

---

# Phase 4 — Do not implement until review

After producing the audit and plan, stop.

Final response should include:

1. Top 10 UX issues.
2. Highest-impact first implementation slice.
3. Which pages need screenshots/comments from Uri.
4. Which changes are safe and low-risk.
5. Which changes require product/design decision.
6. Whether implementation should start with global layout, tables, or Requests page.

Do not start implementation unless explicitly asked.

---

# Later implementation prompt template

When Uri approves the plan, use this format for each implementation slice:

```md
You are working in `conexus`.

Implement UX tightening slice: <slice name>.

Scope:
- <exact files/pages>
- <exact problems to fix>

Constraints:
- No new product features.
- No backend endpoint changes unless explicitly stated.
- No large dependencies.
- Preserve behavior.
- Preserve tests.
- Add/update focused tests.

Validation:
cd frontend
npm test -- --run
npm run build

Final response:
1. Files changed.
2. UX problems fixed.
3. Behavior preserved.
4. Tests added/updated.
5. Validation results.
6. Remaining UX issues.
```

---

# Specific pages Uri should screenshot/comment on

Ask Uri to capture these after running the local stack:

1. Dashboard
2. Projects page with at least one project and one key
3. Providers page
4. Playground after a successful or failed request
5. Requests page with at least one row
6. Request detail drawer
7. Usage page
8. Activity page
9. Activity detail drawer
10. Adapter Profiles page with the manual registered profile
11. Adapter Profile detail drawer
12. Routing page
13. Limits page
14. Health page
15. Settings page

For each screenshot, Uri should add comments in this format:

```text
Page:
What feels wrong:
What I expected:
What confused me:
What feels ugly:
What is too dense:
What is missing:
Priority: low / medium / high
```

```

When you get home, send screenshots plus rough comments. The best first implementation slice will probably be **tables + detail drawers**, especially Requests, Activity, and Adapter Profiles.
```
