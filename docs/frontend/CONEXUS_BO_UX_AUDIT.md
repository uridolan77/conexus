# Conexus BO UX Audit

**Date:** 2026-04-30  
**Method:** Full code inspection of `frontend/` — `app/`, `components/`, `lib/`, `globals.css`.  
No screenshots were available for this pass. Page assessments are code-derived.

---

## 1. Global shell and navigation

### Sidebar structure

```
Overview
  Dashboard
Operations
  Projects
  Providers
  Playground
  Requests
  Usage
  Activity
  Limits
Routing
  Routing
  Smoke Tests        ← redirects to Playground
  Adapter Profiles
System
  Health
  Settings
Adaptation
  Adaptation Plans
  Adaptation Runs
  Adaptation Queue
  Adaptation Profiles
```

### Issues

| # | Issue | Severity |
|---|-------|----------|
| N1 | **"Smoke Tests" in Routing section redirects silently to Playground.** The route `smoke-tests/page.tsx` is `redirect("/playground")`. The operator clicks "Smoke Tests", lands on "Playground", and the URL changes. Confusing and potentially broken-looking. | High |
| N2 | **Adaptation section visually identical to gateway sections.** No divider, no visual cue that Adaptation is a conceptually separate product. Operators unfamiliar with the system may not understand the boundary. | Medium |
| N3 | **"Smoke Tests" and "Playground" are both present.** One is an alias. This clutters the sidebar with a duplicate entry. | Medium |
| N4 | **`.nav-link` is a two-line item** (label + description). 13 nav items × 2 lines = 26 lines of nav text. This pushes the sidebar very tall on small viewports and creates high visual density. Descriptions are helpful on first use but add clutter day-to-day. | Low–Medium |
| N5 | **"Routing" section title collides with "Routing" item label.** The section is called "Routing" and contains an item also called "Routing". The item description is "Policy and aliases". Rename either the section or the item to remove ambiguity. | Low |
| N6 | **No visual separator between Adaptation and gateway sections.** Adaptation is a different product concept. A heavier separator or color treatment would clarify the boundary. | Low |
| N7 | **No sidebar icons.** Not a hard requirement, but the dense two-line layout combined with no icons makes scanning slow. | Low |

### Mobile behavior

- At `≤900px` the sidebar stacks above main, nav-list becomes 2-column grid. The two-column sidebar grid is unusual for a BO; it could work but has not been verified.
- No hamburger/toggle — sidebar is always visible even on mobile. At 768px the full sidebar + content layout may be unusable.

### `isActive` behavior

- `isActive` uses `pathname.startsWith(href)` for non-root routes. This means `/projects` stays active when on `/projects/stale-reservations` (correct). `/routing` would be active while on `/routing` itself, but **not** on `/adapter-profiles` (correct since they differ). No issues found here.

---

## 2. Page layout and shell

### `.main` width handling

```css
.main {
  width: 100%;
  max-width: 1280px;
  padding: var(--space-8);
}
```

**Problem:** `.main` has `max-width: 1280px` but no `margin: 0 auto`. On screens wider than `280px sidebar + 1280px main = 1560px`, the main content aligns left with unused whitespace to the right. This is a visual bug on large monitors (1920px+).

**Fix:** Add `margin-inline: auto` (or equivalent) to `.main`, or apply it at the shell grid level.

---

## 3. Page-by-page review

### `/` — Dashboard

**Rating: Acceptable**

- 3 resources fetched in parallel (projects, providers, usage).
- Partial failure: individual section failures recorded in `summaryError`; no per-section retry.
- `HealthCard` component used from `components/HealthCard.tsx`.
- Checklist (onboarding steps) is a nice touch.
- StatCard grid-4 for summary numbers.

**Issues:**
- Error message aggregates all failing sections into one `summaryError` string. If usage fails but projects succeed, the stat cards show real data while the error banner says "Unable to load dashboard summary for usage." The combination is visually confusing.
- No explicit retry button on the dashboard. User must reload the page.
- Dashboard health card loads its own endpoint separately from the Health page — no deduplication, which is fine but means two health fetches if the operator opens Dashboard and Health.

---

### `/projects` — Projects

**Rating: Acceptable**

- Complex multi-card page: ProjectCreateCard, ProjectListCard, ProjectKeysCard, ProjectLimitsCard, ProjectUsageCard.
- State tracked with 6+ loading flags, which is verbose but correct.
- `success` and `error` are global to the page — a success from create and an error from key revocation could conflict.

**Issues:**
- `setPageError` clears `success` — good, but `success` is never cleared after a delay. A key-issued success banner remains visible indefinitely as the operator continues to interact.
- `latestIssuedKey` is the only time a plaintext API key is shown. This is correct behavior, but the flow (scroll to see the key) may not be obvious.
- `/projects/stale-reservations` is not in the sidebar — discoverable only from the Limits page. This is acceptable but worth confirming.

---

### `/providers` — Providers

**Rating: Acceptable**

- Form + table pattern is clear.
- `adminSessionFetch` called directly from the page component (not via `lib/admin/` module). Minor inconsistency with the rest of the codebase.
- `formatDate` imported from `lib/api.ts` instead of `lib/format.ts`. Same function exists in both places — inconsistency.
- `ConfirmAction` (window.confirm) used for revoke — acceptable but browser-native confirm dialog is inconsistent with BO UI style.

**Issues:**
- Test result per-provider is stored in a `Record<string, ProviderTestResult>` local state. After revoke, old test results are retained. A revoked provider may still show its last test status.
- Error message "Failed to save provider config." and "Failed to load provider configs." are not specific — no HTTP status or message forwarded.

---

### `/playground` — Playground

**Rating: Acceptable**

- Complex form with API key, model, system message, user message, temperature, max tokens.
- Client-side redaction of API key from request/response JSON — good security practice.
- `showKey` toggle for the API key field.

**Issues:**
- **API key is entered as a field** — this is the project API key for the gateway, not an admin credential. The hint should clarify "Project API key (Bearer token), not a provider key."
- Result section contains `JsonBlock` for both raw request payload and raw response — these are `defaultOpen={false}`, which is good. But the response content area shows `KeyValueGrid` + two collapsible JSON blocks. On mobile the drawer-like scroll experience may be awkward.
- "Smoke Tests" in sidebar redirects here. Operator who clicks "Smoke Tests" expecting a structured test flow lands on a free-form chat form. Disconnect between label and experience.
- No "Save to Requests" link or cross-reference — after a test, there is no link to /requests to verify the request was logged.

---

### `/requests` — Requests

**Rating: Needs tightening (HIGH PRIORITY)**

This is the most complex page and has the most UX issues.

#### Filter panel

- **20+ filter fields** fully exposed at all times with no collapsing:
  - Basic: request_id, limit, status, project, api_key_id, error_code
  - Model: provider, model_search, requested_model, served_model, fallback_used
  - Sort: sort_by, sort_dir
  - Time: created_from, created_to, completed_from, completed_to
  - Range: min/max latency, min/max tokens, min/max cost
- **Time inputs are `datetime-local`** — valid, but operators probably want date-only quick shortcuts (Today, Last 7 days).
- **No "active filter" summary** — when filters are applied, there is no visual indicator of what is active except the filter fields themselves.

#### Request table: 14 columns

```
Created | Status | Request ID | Project | API key prefix |
Requested model | Provider | Served model | Latency |
Tokens | Cost | Fallback | Error code | Action
```

- 14 columns almost certainly overflows horizontally at every normal viewport. The `table-wrap` class adds `overflow-x: auto` — functional but not good UX.
- **Request ID cell** uses a two-line `div.stack-tight` layout (full UUID on one line, CopyButton on the next). This makes every row significantly taller.
- **Requested model + Served model** are almost always the same for non-fallback requests. They should be collapsed or shown as a combined field.
- **API key prefix** is diagnostic; it adds width but operators rarely filter by it.
- **Fallback column** is mostly `—` (empty); only shows `fallback` badge when true. Low information density.
- **Error code** is mostly `—`. Could be merged with Status column.

#### Stat cards above table

```
Total visible | Failed visible | Fallback visible | Estimated cost visible
```

- Hints say "Rows on this page" for failed/fallback/cost stats — these stats are computed from the current page only, not the filtered total. This is misleading: "Failed visible: 3" when there may be 30 failed requests across pages.
- Total visible correctly shows `response.total` (the backend total, not just this page).

#### Detail drawer

- `DetailDrawer` opens when `selectedRequestId || detailError || loadingDetail` — this means the drawer opens even when there's an error and no item selected. ✓ Correct.
- **`JsonBlock value={detail} title="Raw row JSON"`** — the `JsonBlock` passes the entire `detail` object including all fields the KV grid already shows. This is redundant and makes the drawer very long.
- No sections in the drawer (no `<hr>` or heading between KV and JSON).
- CopyButton for request_id inside drawer uses `<span className="inline-actions">` — displays correctly but button is a secondary-styled full button next to a code chip, which is disproportionate.
- `fallback_used` is shown as `String(detail.fallback_used)` — renders as "true" or "false" plain text. Inconsistent with the badge in the table.

---

### `/usage` — Usage

**Rating: Acceptable**

- Window selector is simple and works.
- 10 MetricCard items in a `grid-4` = 2.5 rows. The half-row is a bit off — the last card row has only 2 items in 4 columns if 10 items = 2 full rows + 2 orphan cards. Check rendering at 1280px.
- **No chart** — time series data renders as a plain table. Fully functional but misses the obvious visual benefit.
- **All-or-nothing error state** — if any of the 4 API calls fail, an error is set and all sections are empty. There is no partial data display.
- "Summary" card shows a muted note about null metrics — good but feels defensive.

---

### `/activity` — Activity (Audit log)

**Rating: Acceptable**

- 8 filter fields, simpler than Requests.
- **"Actor admin user id"** is a UUID filter — operators almost never know this. Consider removing or making it hidden/advanced.
- Table: 5 columns. Clean.
- **Status column missing** — audit log has no status column. This is correct (audit logs don't have status), but if `action` contains things like `project_api_key.revoke`, understanding success/failure is impossible.
- **Resource ID column** shows full UUID inline code + "View" button in the same cell. This is the widest cell in the table and can wrap.
- **Action and Resource type** use `<code>` tag — these are dot-separated strings (e.g., `project_api_key.issue`). Code styling is appropriate.
- **No retry button** on error state.
- **Pagination** shows "Offset 0" — not user-friendly.

---

### `/health` — Health

**Rating: Good**

- Clear, functional, minimal.
- Auto-loads on mount, Refresh button available.
- `Raw /health JSON` and `Raw /readyz JSON` shown via `JsonBlock defaultOpen={false}` — good.
- "Tip" card at bottom is a bit sparse — could be `HelpText` or inline in the readiness card.
- No auto-refresh interval — operator must manually click Refresh.

---

### `/settings` — Settings

**Rating: Acceptable**

- Fully read-only. 3 cards.
- "Backend safe config endpoint is not available yet" — this is an `Alert tone="info"`. Acceptable, but if this feature is truly planned, it should be tagged or linked to a tracking issue; otherwise it's noise.
- Known assumptions uses a raw `<ul>` with `<code>` in `<li>` — acceptable but not using BO components.

---

### `/routing` — Routing

**Rating: Needs tightening**

- **Warning banner fires too broadly.** It fires when any env candidate exists OR when no candidates exist. The message is the same for both cases: "BO provider configs may not fully drive runtime provider selection yet." This creates a persistent yellow banner that operators learn to ignore.
- 4 cards: Default Policy, Provider Candidates, Alias Routes, Direct Routes. Good structure.
- Provider candidates table: "Key" column shows either `<code>{candidate.key_mask}</code>` or the string "Configured". The inconsistency looks like a bug.
- No refresh button — operator must reload page.
- All data is read-only — clear. But no way to know when this data was last loaded.

---

### `/adapter-profiles` — Adapter Profiles

**Rating: Needs tightening (HIGH PRIORITY)**

#### Main table: 11 columns

```
gateway_profile_id | adapter_profile_id | domain_key | status |
composite_score | profile_version | evidence_hash | semantic_context_hash |
slod_model_version | created_at | View
```

- **`evidence_hash` and `semantic_context_hash`** are long hex strings with `wrap-anywhere`. They make rows very tall and the table very wide.
- **Column names are snake_case engineering identifiers** — no human-readable headers.
- **`status` has no badge** — rendered as plain text. Inconsistent with Requests/Runs pages where status gets a badge.
- **Composite_score column** is typically a decimal or null. Low operational value in the main table.

#### Detail drawer

- KV grid has 14 items including `evidence_hash` and `semantic_context_hash` shown as full code values.
- Activations sub-table inside drawer — good pattern.
- `JsonBlock` at bottom for `detail.metadata` — `defaultOpen={false}`. ✓ Good.
- Drawer has no sections (no visual grouping between identity fields, score fields, lifecycle fields).

#### Warning text

- Warning `Alert tone="warning"` is 2 full sentences of caveats. It renders prominently before the table. It will become noise once operators understand the page.

---

### `/limits` — Limits

**Rating: Confusing**

- This page is essentially a navigation aid with 3 cards but **no actual data**.
- The only useful content: a description of modes (static text), a link to Projects, and a link to stale reservations.
- **Operators who click "Limits" expect to see limit status** — they get a landing page pointing elsewhere.
- Consider: integrate limit overview into the Projects page, and remove the Limits sidebar entry; or turn Limits into an actual data page showing all project limits in one table.

---

### `/adaptation/plans` — Adaptation Plans

**Rating: Acceptable**

- Summary cards use `Card > SectionHeader > KeyValueGrid` with single KV item each. This is 3 cards showing single numbers. Should use `StatCard` or `MetricCard` components.
- Filters: `status` is a free-text `Input`, not a `Select`. Operators don't know valid status values.
- Actions in the table (Approve, Start Run) are inline. Approve/Start Run are side-effectful — no confirmation dialog.
- "Start Run" navigates away on success. Clear, but no visual feedback before redirect.

---

### `/adaptation/runs` — Adaptation Runs

**Rating: Needs tightening**

#### Table: 10 columns

```
Created | Domain key | Plan | Recipe | Status | Step count |
Started | Completed | Failed | Action
```

- **3 timestamp columns** (Started, Completed, Failed) — most will be `—`. This is very wide.
- **Plan ID and Recipe key** rendered as `wrap-anywhere code` — can be very long.
- **`formatDate` from `lib/api.ts`** instead of `formatDateTime` from `lib/format.ts` — inconsistency.
- Status filter is free text (same issue as Plans).
- No total count — "Showing N runs" with no backend pagination noted.

---

### `/adaptation/queue` and `/adaptation/profiles`

Not inspected in this pass. Audit these with screenshots.

---

## 4. Visual density and spacing

### What is consistent and good

- CSS design tokens (`--color-*`, `--space-*`, `--font-*`) are well-defined and used throughout.
- `card`, `page-header`, `section-header`, `eyebrow`, `badge`, `alert` are all consistent.
- `kv-row` has a fixed label width of 180px — works well for most fields.

### Issues

| # | Issue |
|---|-------|
| D1 | Tables have `overflow-x: auto` but no min-width on long-ID columns. Columns with `wrap-anywhere` grow rows vertically rather than clipping. The Requests table with 14 columns and full UUID values will produce very tall rows. |
| D2 | `stat-card` strong font-size is 26px. These cards are not visually grouped from section cards. At `grid-4`, 10 stat cards overflow to a partial 3rd row (Usage page, 10 items = 2 full rows + 2). |
| D3 | `.kv-row` label column is 180px. Some labels are very long (e.g., "semantic_context_hash") and break layout. |
| D4 | No max-width on drawer — `drawer-panel` is `max-width: 480px`. With 14 KV items and long code values, this drawer scrolls a lot. |
| D5 | `filter-bar` uses `repeat(auto-fill, minmax(200px, 1fr))` — auto fills columns. On a 1280px main area this could produce many columns, but most filters use `form-row` (fixed 2-column) instead, making `filter-bar` unused on filter-heavy pages. |
| D6 | `card` has `margin-bottom: var(--space-4)` baked in. Using `page-stack` class (gap-based) would be cleaner and avoid margin-stacking issues. Many pages mix cards with and without explicit margin. |

---

## 5. Tables — detailed assessment

| Table | Columns | Assessment | Recommended action |
|-------|---------|-----------|-------------------|
| Requests | 14 | Too wide. Full UUIDs + stacked cells make rows tall. | Reduce to ~7 core columns. Move detail to drawer. Add compact ID chip with copy. |
| Adapter Profiles | 11 | Hash columns destroy width. snake_case headers. No status badge. | Reduce to 5–6 columns. Hide hashes behind View. Add status badge. |
| Activity | 5 | Acceptable. Resource ID cell is wide. | CopyableCode component on resource ID. |
| Requests detail drawer | 18 KV items + full JSON block | KV is complete. JSON repeats all KV data. | Remove or collapse JSON by default with a "Show raw JSON" button. |
| Usage by project | 7 | Acceptable. | Good as-is. |
| Usage by provider | (not inspected in detail) | — | Inspect with data. |
| Adaptation Runs | 10 | 3 timestamp columns. Long ID values. | Reduce to ~6 columns. Collapse timestamps into drawer. |
| Provider candidates | 5 | Acceptable. "Key" column shows inconsistent values. | Normalize "Key" display. |

---

## 6. Forms

### Requests filter panel

- 20+ fields always visible. Most operators use Status + Project + maybe date range.
- No "active filter" summary.
- No collapsible advanced section.

### Activity filter panel

- 8 fields. "Actor admin user id" is rarely used. Consider hidden/advanced.

### Adaptation Plans/Runs filter

- Status filter is free-text — operators don't know valid values. Use a Select or provide a hint with examples.

### Providers form

- Clean. One field per row in FormRow. Works well.

### Playground form

- Dense but acceptable. Temperature and max tokens have inline validation shown via `FieldError`.

---

## 7. Detail drawers

| Drawer | Width | Issues |
|--------|-------|--------|
| Request detail | 480px max | 18 KV rows + full JSON block. Very tall. JSON repeats KV data. No sections. |
| Activity detail | (not fully inspected) | — |
| Adapter Profile detail | 480px max | 14 KV rows + activations sub-table + JSON. Long code values overflow. |

**Common drawer issues:**
- No focus trap. Keyboard navigation does not stay in drawer. Tab goes back to page content.
- No visible section separators inside drawer body.
- Close button is a ghost button with `✕` text label — no visible border, may look broken.
- Escape key closes drawer ✓ — correctly implemented.

---

## 8. Status and semantic color

### Current status vocabulary (from `StatusBadge` in `components/ui/index.tsx`)

```
active → success (green)
revoked → danger (red)
ok → success (green)
passed → success (green)
failed → danger (red)
never → neutral (grey)
running → info (blue)
not-run → neutral (grey)
```

### Issues

| # | Issue |
|---|-------|
| S1 | **Requests page uses an inline `badgeTone()` function** (completed→success, failed→danger, started→info). This is not in `StatusBadge`. The logic is duplicated. |
| S2 | **Adapter Profiles `status` column renders plain text** — no badge at all. Statuses like "registered", "canary", "promoted", "rolled_back" have no visual treatment. |
| S3 | **Activity table has no status column** — audit log actions have no pass/fail indicator. |
| S4 | **Adaptation status values** ("Draft", "Approved", "Running", "Completed", "Failed") use inline tone mapping in Runs page. Not in `StatusBadge`. |
| S5 | **Warning banners on Routing and Adapter Profiles pages** are persistent — shown on every load regardless of actual operational state. These will become noise. |
| S6 | **`StatusBadge` does not cover all statuses in use.** The component is used for providers/keys/health but not for requests or adaptation. |

### Recommended vocabulary consolidation

All statuses across the app:

```
Request:   completed (success) | failed (danger) | started (info)
Provider:  active (success) | revoked (danger)
API key:   active (success) | revoked (danger)
Health:    ok (success) | failed (danger)
Adapter:   registered | canary | promoted | rolled_back | unknown
Adaptation: draft | approved | running | completed | failed
```

These should all route through one extensible `StatusBadge` component.

---

## 9. Operational clarity

| Page | Clear purpose? | Safe vs dangerous actions clear? | What indicates success? |
|------|---------------|----------------------------------|------------------------|
| Dashboard | ✓ | ✓ (read-only) | Checklist items done |
| Projects | ✓ | Partial — Revoke key is danger, but sits inline with no color treatment in some sub-components | Alert tone=success |
| Providers | ✓ | Revoke is danger ✓ | Alert tone=success |
| Playground | ✓ | ✓ (no destructive actions) | Response card appears |
| Requests | Partial — what does "View details" do? Not obvious it opens a drawer | ✓ (read-only) | Drawer opens |
| Activity | ✓ | ✓ (read-only) | — |
| Usage | ✓ | ✓ (read-only) | — |
| Health | ✓ | ✓ (read-only) | Badge turns green |
| Settings | ✓ | ✓ (read-only) | — |
| Routing | Partial — caveat banner undermines clarity | ✓ (read-only) | — |
| Adapter Profiles | Confusing — column headers are engineering identifiers | ✓ (read-only) | — |
| Limits | Confusing — page has no data, just redirects | — | — |
| Adaptation Plans | Partial — "approve" and "start run" are side-effectful with no confirmation | Approve/Start Run are not labeled as risky | Redirect on success |
| Adaptation Runs | ✓ | Partial — cancel/rollback if they exist | — |

---

## 10. Accessibility and keyboard UX

| Issue | Severity |
|-------|----------|
| No focus trap in `DetailDrawer` — Tab navigates back to page content behind the drawer | Medium |
| `CopyButton` and generic "View" buttons have no `aria-label` — screen readers read "View" without context of which row | Medium |
| `Table` component wraps `<table>` in a `<div>` but the `aria-label` is on the inner `<table>` ✓ | — |
| `DetailDrawer` uses `role="dialog" aria-modal="true"` ✓ | — |
| `Alert` uses `role="alert"` for danger, `role="status"` otherwise ✓ | — |
| `EmptyState` has no `role` — screen reader may not distinguish it from regular content | Low |
| `LoadingState` renders a `<p>` with no `aria-live` — screen readers may not announce load state changes | Low |
| `ConfirmAction` uses `window.confirm` — not accessible in all AT environments | Medium |
| Color contrast not verified (requires browser inspection) | Unknown |
| Focus visibility: `focus-visible` outline defined ✓, but ghost buttons have no visible border, so focus ring is the only indicator | Low |

---

## 11. Responsive behavior

| Breakpoint | Issue |
|------------|-------|
| `≤900px` | Sidebar stacks above main. Nav-list becomes 2-column — unusual for nav. Grid and form-row collapse to 1 column ✓. |
| `≤560px` | Nav becomes 1 column. kv-row label/value stack ✓. |
| `1024px–1280px` | Requests table 14 columns will scroll. Adapter Profiles 11 columns will scroll. No min-width set on tables. |
| `1920px+` | `.main` without `margin: auto` causes left-flush layout with wide right whitespace. |
| Tablet (768px) | Sidebar always visible — this is the break range. After `≤900px` triggers, the sidebar is full width stacked on top, which may be very long. |

---

## 12. Code-level inconsistencies worth noting

| File | Issue |
|------|-------|
| `app/providers/page.tsx` | Uses `adminSessionFetch` directly; other pages use `lib/admin/*` modules |
| `app/providers/page.tsx` | Imports `formatDate` from `lib/api`; should use `lib/format` |
| `app/adaptation/plans/page.tsx` | Uses `formatDate` from `lib/api` instead of `formatDateTime` from `lib/format` |
| `app/adaptation/runs/page.tsx` | Same `formatDate` inconsistency |
| `app/requests/page.tsx` | Defines `badgeTone()` locally instead of extending `StatusBadge` |
| `app/adapter-profiles/page.tsx` | Status rendered as plain text; no badge |
| `app/adaptation/plans/page.tsx` | Uses `Card + SectionHeader + KeyValueGrid` for single-number stats; should use `StatCard`/`MetricCard` |
| `components/ui/index.tsx` | Both `ConfirmAction` and `ConfirmButton` exist and do the same thing |
| Pagination throughout | Shows "Offset 0" — not user-friendly |

---

## 13. Pages needing screenshots from Uri

These pages have complex data-dependent rendering that cannot be fully assessed from code alone:

1. **Dashboard** — HealthCard, checklist state, StatCard grid with partial data
2. **Projects** — Project list with at least one project; key table; limits section; stale reservations
3. **Providers** — Table with both active and revoked providers; test result state
4. **Playground** — After a successful request and after a failed request
5. **Requests** — Table with 10+ rows; drawer open; with filters applied
6. **Request detail drawer** — Full scroll to see JSON block
7. **Usage** — All 10 MetricCards; timeseries table; by-project table
8. **Activity** — Table with rows; detail drawer open
9. **Adapter Profiles** — Table with profiles; drawer open with long hashes
10. **Routing** — With both BO and env candidates; warning banner visible
11. **Adaptation Plans** — With draft and approved plans; approve/start run buttons
12. **Adaptation Runs** — With failed runs (row-warning class)
13. **Limits** — See if it looks like an empty landing page or something useful

For each screenshot, provide comments in this format:

```
Page:
What feels wrong:
What I expected:
What confused me:
What feels ugly:
What is too dense:
What is missing:
```

---

## Summary: Top 10 UX issues (code-derived)

| # | Issue | Affected page(s) | Impact |
|---|-------|-----------------|--------|
| 1 | **Requests table has 14 columns** — overflows, tall rows, hard to scan | Requests | High |
| 2 | **Requests filter panel has 20+ fields, always fully visible** | Requests | High |
| 3 | **Adapter Profiles table has 11 columns with raw hash values** | Adapter Profiles | High |
| 4 | **"Smoke Tests" in sidebar redirects silently to Playground** | Sidebar | High |
| 5 | **`.main` has no `margin: 0 auto`** — content left-aligns on wide screens | All pages | Medium–High |
| 6 | **Request detail drawer shows full JSON block that duplicates KV data** | Requests drawer | Medium |
| 7 | **Limits page has no data** — it's a navigation stub masquerading as a page | Limits | Medium |
| 8 | **Status badge vocabulary is fragmented** — plain text, inline functions, `StatusBadge` used inconsistently | Requests, Adapter Profiles, Adaptation | Medium |
| 9 | **No focus trap in DetailDrawer** — keyboard navigation escapes drawer | All drawers | Medium |
| 10 | **Pagination shows "Offset 0"** — not user-friendly; no page number or "1–50 of N" | Requests, Activity, Adapter Profiles | Low–Medium |
