# Conexus BO UX Tightening Plan

**Based on:** `CONEXUS_BO_UX_AUDIT.md` (2026-04-30, code-derived)  
**Status:** Awaiting Uri screenshots and comments before P1+ implementation.

---

## P0 — UX bugs (block use or mislead operator)

---

### P0-01 — "Smoke Tests" sidebar item silently redirects to Playground

**Page/component:** `lib/navigation.ts`, `app/smoke-tests/page.tsx`  
**Problem:** The "Smoke Tests" nav entry causes a client-side redirect to `/playground`. The operator clicks "Smoke Tests", lands on "Playground", and the browser URL changes. This looks like a broken navigation or a routing error.  
**Impact:** Operators who click "Smoke Tests" expecting a different page experience confusion and distrust of the BO navigation.  
**Recommended fix:** Remove "Smoke Tests" from `NAV_SECTIONS` in `navigation.ts`. Optionally rename the Playground item to "Playground / Smoke Tests" and update its description.  
**Risk:** Low — the route still works via direct URL; this is a nav cleanup only.  
**Files likely touched:** `frontend/lib/navigation.ts`  
**Test coverage:** No test for nav items; smoke test route redirect is not tested.  

---

### P0-02 — `.main` has no `margin: 0 auto` — content left-aligns on wide screens

**Page/component:** `app/globals.css` (`.main` class)  
**Problem:** `.main { width: 100%; max-width: 1280px; }` without `margin-inline: auto` causes the content area to align flush-left on screens wider than ~1560px (280px sidebar + 1280px content + spacing). On 1920px+ monitors the right side of the page is blank white space.  
**Impact:** Looks visually broken on large monitors. Every page is affected.  
**Recommended fix:** Add `margin-inline: auto` to `.main`.  
**Risk:** Very low — CSS-only, layout-neutral on smaller screens.  
**Files likely touched:** `frontend/app/globals.css`  
**Test coverage:** No visual regression tests.  

---

### P0-03 — Adapter Profiles table status rendered as plain text (no badge)

**Page/component:** `app/adapter-profiles/page.tsx`  
**Problem:** The `status` column renders `{r.status}` as plain text. All other status columns in the app use `Badge` or `StatusBadge`. The "registered", "canary", "promoted", "rolled_back" values are indistinguishable at a glance.  
**Impact:** Operator cannot quickly scan profile statuses.  
**Recommended fix:** Wrap `r.status` in a `<Badge tone={...}>` with appropriate tone mapping.  
**Risk:** Low.  
**Files likely touched:** `frontend/app/adapter-profiles/page.tsx`  
**Test coverage:** None for status rendering.  

---

## P1 — High-value polish

---

### P1-01 — Requests table: reduce from 14 columns to ~7

**Page/component:** `app/requests/page.tsx`  
**Problem:** 14 columns overflow at any normal viewport. Full UUIDs in the Request ID cell cause tall rows. "Requested model" and "Served model" are mostly identical for non-fallback requests. "API key prefix" and "Error code" are low-scan-value columns.  
**Impact:** Most visible page in the BO. Table is the primary daily operator view.  
**Recommended fix:**  
- Keep: Created, Status, Project, Model (combine or use served model with fallback indicator), Latency, Cost, Action  
- Move to drawer only: Request ID (copyable in drawer), API key prefix, Requested model, Served model, Error code  
- Replace Request ID cell `div.stack-tight` with a compact `CodeChip` showing first 8 chars + CopyButton in the drawer  
- Show Fallback as an inline indicator on the Status badge (e.g., "completed + fallback" or a secondary badge) rather than a dedicated column  
**Risk:** Medium — visual change to primary operational view. Must be tested with real data.  
**Files likely touched:** `frontend/app/requests/page.tsx`, `frontend/components/ui/index.tsx`  
**Screenshot reference:** Request table screenshot needed.  

---

### P1-02 — Requests filter panel: collapse advanced filters

**Page/component:** `app/requests/page.tsx`  
**Problem:** 20+ filter fields are always fully visible. Most operators use 2–4 filters (Status, Project, date range, maybe model). The advanced filters (latency range, token range, cost range, completed timestamp) take up a full card and are rarely used.  
**Impact:** Page feels overwhelming before operator even sees the table.  
**Recommended fix:**  
- Keep visible: Status, Project, Model search, Date range (created), Limit, Sort  
- Move to collapsible "Advanced filters" `<details>`: API key ID, Error code, Provider, Requested model, Served model, Fallback, Completed timestamp range, Latency/token/cost ranges  
- Add an active-filter summary chip row when any filter is applied (e.g., `status: failed × | project: MyApp ×`)  
**Risk:** Medium — behavior change to filter interaction. Preserve URL state.  
**Files likely touched:** `frontend/app/requests/page.tsx`, `frontend/app/globals.css`  
**Screenshot reference:** Request filter form screenshot needed.  

---

### P1-03 — Adapter Profiles table: reduce from 11 columns and add human-readable headers

**Page/component:** `app/adapter-profiles/page.tsx`  
**Problem:** 11 columns including two raw hash values (`evidence_hash`, `semantic_context_hash`) rendered with `wrap-anywhere`. Column headers are snake_case engineering identifiers.  
**Impact:** Table is nearly unreadable. Scroll width is extreme.  
**Recommended fix:**  
- Keep in table: Domain key, Status (with badge), Composite score, Version, Created at, View  
- Move to drawer only: gateway_profile_id, adapter_profile_id, evidence_hash, semantic_context_hash, slod_model_version  
- Rename headers: "Domain", "Status", "Score", "Version", "Created"  
- In drawer: keep all details, add copy buttons for IDs and hashes  
**Risk:** Medium.  
**Files likely touched:** `frontend/app/adapter-profiles/page.tsx`  
**Screenshot reference:** Adapter profiles table screenshot needed.  

---

### P1-04 — Request detail drawer: remove redundant raw JSON block

**Page/component:** `app/requests/page.tsx`  
**Problem:** `<JsonBlock value={detail} title="Raw row JSON" />` passes the entire `detail` object to the drawer. This object is already fully rendered in the KV grid above it. The JSON block adds significant scroll to the drawer and exposes raw field names mixed with rendered values.  
**Impact:** Drawer becomes very tall. Operators must scroll past all KV items just to reach the copy button if they want the request ID.  
**Recommended fix:**  
- Remove the `JsonBlock` from the drawer. The KV grid already shows all fields.  
- OR: replace with a `JsonBlock` that shows only fields not in the KV grid (none in this case, so remove it).  
- Request ID should have a `CopyableCode` component at the top of the drawer, not buried in the KV grid.  
**Risk:** Low — no functional change, purely presentational.  
**Files likely touched:** `frontend/app/requests/page.tsx`  

---

### P1-05 — Limits page: replace with redirect or integrate into Projects

**Page/component:** `app/limits/page.tsx`, `lib/navigation.ts`  
**Problem:** The Limits page has no data. It's three static cards with text and links. Operators who click "Limits" expect to see limit status, not a landing page pointing to Projects.  
**Impact:** Operators feel confused and may think limit data is missing/broken.  
**Recommended fix (option A):** Add a live summary table of all project limits to the Limits page, fetching project limits in aggregate.  
**Recommended fix (option B):** Remove "Limits" from the sidebar and fold the "Stale reservations" link into the Projects page sidebar or Projects page itself.  
**Risk:** Medium for option A (backend may not have an aggregate endpoint). Low for option B.  
**Files likely touched:** `frontend/app/limits/page.tsx`, `frontend/lib/navigation.ts`  

---

### P1-06 — Pagination: replace "Offset N" with "X–Y of Z"

**Page/component:** `app/requests/page.tsx`, `app/activity/page.tsx`, `app/adapter-profiles/page.tsx`  
**Problem:** Pagination shows "Offset 0", "Offset 50" etc. This is an internal implementation detail, not a user-friendly page indicator.  
**Impact:** Minor but consistently rough. Every paginated page has this issue.  
**Recommended fix:** Replace with a computed label "Showing X–Y of Z" using the pattern already computed as `rangeLabel` in some pages. Standardize across all paginated pages.  
**Risk:** Very low.  
**Files likely touched:** All three paginated pages.  

---

### P1-07 — Routing page: remove persistent warning banner or make it conditional

**Page/component:** `app/routing/page.tsx`  
**Problem:** A warning banner fires when any env candidate exists OR no candidates exist, showing the same message: "BO provider configs may not fully drive runtime provider selection yet." Operators see this on every load and learn to ignore it.  
**Impact:** Warning banners lose meaning when always visible. Real issues will be overlooked.  
**Recommended fix:**  
- Only show the warning if `candidates.length === 0` (no routing is possible at all — genuinely critical).  
- Replace the env-candidate warning with an inline note in the Provider Candidates table row (e.g., a `neutral` badge on "env fallback" source).  
**Risk:** Low.  
**Files likely touched:** `frontend/app/routing/page.tsx`  

---

### P1-08 — Adaptation Plans summary cards: use StatCard/MetricCard components

**Page/component:** `app/adaptation/plans/page.tsx`  
**Problem:** The three summary cards each use `Card > SectionHeader > KeyValueGrid` with a single item. This is verbose and renders as three large cards for three numbers. The `StatCard` and `MetricCard` components exist precisely for this use case.  
**Impact:** Page starts with three oversized cards before the filter form. Inconsistent with Dashboard and Usage page patterns.  
**Recommended fix:** Replace the three summary cards with a `grid-3` of `StatCard` or `MetricCard` components.  
**Risk:** Very low.  
**Files likely touched:** `frontend/app/adaptation/plans/page.tsx`  

---

### P1-09 — Adaptation Plans/Runs status filter: use Select with known values

**Page/component:** `app/adaptation/plans/page.tsx`, `app/adaptation/runs/page.tsx`  
**Problem:** Status filter is a free-text `Input`. Operators don't know valid status values (Draft, Approved, Running, Completed, Failed).  
**Impact:** Filter is unusable without prior knowledge of the API vocabulary.  
**Recommended fix:** Replace with a `Select` offering known values: Any, Draft, Approved, Running, Completed, Failed.  
**Risk:** Low. If unknown statuses appear in data, keep an "Other..." free-text fallback.  
**Files likely touched:** `frontend/app/adaptation/plans/page.tsx`, `frontend/app/adaptation/runs/page.tsx`  

---

### P1-10 — Adaptation Runs table: reduce timestamp columns from 3 to 1

**Page/component:** `app/adaptation/runs/page.tsx`  
**Problem:** Three separate columns for "Started", "Completed", "Failed" timestamps — most are `—`. This makes the table very wide for low-density information.  
**Impact:** Table overflows horizontally.  
**Recommended fix:** Replace with a single "Updated" or "Last event" column showing the most recent non-null timestamp (failed_at > completed_at > started_at). Move individual timestamps to the drawer/detail view.  
**Risk:** Low — no data is lost, just moved.  
**Files likely touched:** `frontend/app/adaptation/runs/page.tsx`  

---

## P2 — Design-system improvements

---

### P2-01 — Consolidate status badge vocabulary into `StatusBadge`

**Problem:** `StatusBadge` covers provider/key/health statuses only. Requests, Adapter Profiles, and Adaptation pages use ad-hoc tone mapping. When a new status appears, it needs updating in multiple places.  
**Recommended fix:** Extend `StatusBadge` to accept all known statuses:  
```
completed | failed | started | active | revoked | ok | passed | never |
running | not-run | registered | canary | promoted | rolled_back |
draft | approved | unknown
```
Each maps to a tone. Pages use `<StatusBadge status={...} />` uniformly.  
**Files likely touched:** `frontend/components/ui/index.tsx`, all pages using status badges.  

---

### P2-02 — Add focus trap to `DetailDrawer`

**Problem:** No focus trap in `DetailDrawer`. Tab key navigates back to the page behind the drawer.  
**Recommended fix:** Implement a focus trap using `useEffect` that captures focusable elements within `.drawer-panel` and cycles Tab/Shift+Tab within them while the drawer is open. No new library needed.  
**Files likely touched:** `frontend/components/ui/index.tsx`  

---

### P2-03 — Standardize `formatDate` / `formatDateTime` usage

**Problem:** `providers/page.tsx` and adaptation pages import `formatDate` from `lib/api.ts`. All other pages use `formatDateTime` from `lib/format.ts`. Two sources for date formatting is a maintenance risk.  
**Recommended fix:** Migrate `providers/page.tsx` and adaptation pages to use `formatDateTime` from `lib/format.ts`. Remove `formatDate` from `lib/api.ts` or alias it.  
**Files likely touched:** `frontend/app/providers/page.tsx`, `frontend/app/adaptation/plans/page.tsx`, `frontend/app/adaptation/runs/page.tsx`, `frontend/lib/api.ts`.  

---

### P2-04 — Compact ID display component: `TruncatedId`

**Problem:** Long UUIDs in tables consume width and create tall rows. `CopyableCode` exists but shows the full value.  
**Recommended fix:** Create a `TruncatedId` component: shows first 8 chars of a UUID in a `CodeChip`, has a title/tooltip with the full value, and includes a `CopyButton` with `aria-label="Copy full ID"`.  
**Files likely touched:** `frontend/components/ui/index.tsx`, then used in Requests, Adapter Profiles, Activity tables.  

---

### P2-05 — DrawerSection component for structured drawer content

**Problem:** All detail drawers are unsectioned `div.stack` — no visual grouping between identity fields, operational fields, timestamps, and JSON.  
**Recommended fix:** Add a lightweight `DrawerSection` component:  
```tsx
function DrawerSection({ title, children }: ...) {
  return (
    <div className="drawer-section">
      {title && <p className="drawer-section-title">{title}</p>}
      {children}
    </div>
  );
}
```
Add `.drawer-section + .drawer-section` border-top in CSS.  
**Files likely touched:** `frontend/components/ui/index.tsx`, `frontend/app/globals.css`.  

---

### P2-06 — Active filter chips / summary row

**Problem:** When filters are applied on Requests/Activity/Adaptation pages, there is no visual summary of what is active. Operators lose context as they scroll down.  
**Recommended fix:** After the filter form, render an `ActiveFilters` component that shows chips for each non-default filter: `status: failed ×`. Clicking `×` clears that filter and re-fetches.  
**Files likely touched:** `frontend/components/ui/index.tsx`, `frontend/app/requests/page.tsx`, `frontend/app/activity/page.tsx`.  

---

### P2-07 — Remove duplicate `ConfirmAction`/`ConfirmButton` components

**Problem:** Both `ConfirmAction` and `ConfirmButton` exist in `components/ui/index.tsx` and do the same thing (one is an alias for the other).  
**Recommended fix:** Keep `ConfirmButton`, remove `ConfirmAction`, or vice versa. Update all call sites.  
**Files likely touched:** `frontend/components/ui/index.tsx`, `frontend/app/providers/page.tsx`, any other users.  

---

## P3 — Nice-to-have

---

### P3-01 — Add visual separator between Adaptation and gateway nav sections

The "Adaptation" section blends visually with gateway sections. A heavier `border-top` or background difference on the Adaptation nav section would clarify the product boundary.  
**Files:** `frontend/app/globals.css`, `frontend/components/bo/Sidebar.tsx`  

---

### P3-02 — Dashboard: per-section error recovery

Instead of one global error banner for partial failures, show per-section inline error notes with retry capability.  
**Files:** `frontend/app/page.tsx`  

---

### P3-03 — Health page: optional auto-refresh interval

Add a "Refresh every 30s" toggle on the Health page for operators who want live monitoring without manual clicks.  
**Files:** `frontend/app/health/page.tsx`  

---

### P3-04 — Usage page: simple ASCII sparkline or bar for timeseries

The timeseries table is functional but text-only. Even a basic percentage bar (`progress-bar` class already exists) per row would improve scannability.  
**Files:** `frontend/app/usage/page.tsx`  

---

### P3-05 — Keyboard shortcut: Escape closes drawer (already implemented)

Already implemented ✓. Document it as a feature.  

---

### P3-06 — Settings page: remove "not available yet" card or replace with issue link

The "Backend safe config endpoint is not available yet" `Alert` will persist indefinitely. Replace with a `<!-- TODO -->` comment or remove the card entirely until the endpoint exists.  
**Files:** `frontend/app/settings/page.tsx`  

---

## Implementation slices

### Slice 1 — Global layout + navigation (P0-01, P0-02, P1-05 option B, P3-01)

**Files:**
- `frontend/lib/navigation.ts`
- `frontend/app/globals.css`
- Optionally `frontend/components/bo/Sidebar.tsx`

**Work:**
- Remove "Smoke Tests" from sidebar nav.
- Add `margin-inline: auto` to `.main`.
- Add visual separator before Adaptation nav section.

**Risk:** Very low.  
**Validation:** `npm test -- --run; npm run build`

---

### Slice 2 — Status badge consolidation (P0-03, P2-01)

**Files:**
- `frontend/components/ui/index.tsx`
- `frontend/app/adapter-profiles/page.tsx`
- `frontend/app/requests/page.tsx`

**Work:**
- Extend `StatusBadge` to cover all statuses in use.
- Replace inline `badgeTone()` in requests page.
- Add badge to adapter profiles status column.

**Risk:** Low. Visual change only.

---

### Slice 3 — Requests table column reduction (P1-01)

**Files:**
- `frontend/app/requests/page.tsx`
- `frontend/components/ui/index.tsx` (if adding `TruncatedId`)

**Work:**
- Reduce table from 14 to ~7 columns.
- Move IDs and secondary fields to drawer.
- Replace request ID cell with compact `CodeChip` + copy.
- Improve drawer layout (sections, no redundant JSON block).

**Risk:** Medium. Most important page — test with real data.

---

### Slice 4 — Requests filter collapse (P1-02, P2-06)

**Files:**
- `frontend/app/requests/page.tsx`
- `frontend/app/globals.css`

**Work:**
- Wrap advanced filters in `<details>`.
- Add active filter chip row.

**Risk:** Medium.

---

### Slice 5 — Adapter Profiles table reduction + drawer improvement (P1-03, P2-05)

**Files:**
- `frontend/app/adapter-profiles/page.tsx`
- `frontend/components/ui/index.tsx`
- `frontend/app/globals.css`

**Work:**
- Reduce table columns to 6.
- Add human-readable headers.
- Add sectioning to drawer.
- Add `DrawerSection` component.

**Risk:** Medium.

---

### Slice 6 — Pagination display + format standardization (P1-06, P2-03)

**Files:**
- `frontend/app/requests/page.tsx`
- `frontend/app/activity/page.tsx`
- `frontend/app/adapter-profiles/page.tsx`
- `frontend/app/providers/page.tsx`
- `frontend/app/adaptation/plans/page.tsx`
- `frontend/app/adaptation/runs/page.tsx`

**Work:**
- Replace "Offset N" with "Showing X–Y of Z".
- Migrate `formatDate` → `formatDateTime`.

**Risk:** Low.

---

### Slice 7 — Small page fixes (P1-07, P1-08, P1-09, P1-10, P1-04, P3-06)

**Files:** Various

**Work:**
- Routing page: narrow warning condition.
- Adaptation Plans: use StatCard/MetricCard for summary.
- Adaptation Plans/Runs: select for status filter.
- Adaptation Runs: collapse 3 timestamp columns to 1.
- Requests drawer: remove redundant JSON block.
- Settings page: clean up "not yet" card.

**Risk:** Low.

---

### Slice 8 — Accessibility: focus trap + aria labels (P2-02)

**Files:**
- `frontend/components/ui/index.tsx`

**Work:**
- Add focus trap to `DetailDrawer`.
- Add `aria-label` to generic "View" and "Copy" buttons throughout.

**Risk:** Low (additive).

---

## Decisions requiring Uri input

1. **Limits page**: full data page (option A) vs. remove from sidebar (option B)?
2. **Smoke Tests**: remove nav entry entirely, or rename Playground to "Playground / Smoke Tests"?
3. **Adaptation section separator**: subtle CSS border, or a prominent visual separator?
4. **Requests table**: which 7 columns to keep as default? (proposed above — confirm with operational priorities)
5. **Requests filter**: should "clear active filter chips" feel instant (no re-fetch) or always re-fetch?
6. **Raw JSON in drawers**: keep as collapsed `details` block, or remove entirely from Requests drawer?
