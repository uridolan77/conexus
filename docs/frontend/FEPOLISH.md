# Conexus BO UX Screenshot Review Report

The latest implementation work looks structurally successful. The recent commit closed the important consistency/security items: request detail JSON redaction, `StatusBadge` string support, routing env-fallback warning, and drawer focus/a11y improvements. 

The screenshots show that the BO is now functionally complete enough for use, but the next pass should focus on **readability, density, table behavior, and page-state clarity**.

## Executive verdict

**Current UX state: usable, but not yet polished.**

The visual foundation is good: clean light theme, clear sidebar, good cards, strong page headers, and consistent spacing. The biggest remaining issues are concentrated in:

1. **Wide operational tables** — Requests and Adapter Profiles are the clearest problems.
2. **Overexposed filters** — Requests and Activity show too many fields at once.
3. **Debug JSON prominence** — Health and drawers make raw JSON feel like primary UI.
4. **Misleading unconfigured Adaptation state** — Adaptation Plans still renders filters/tables/count cards even though the service is not configured.
5. **Long IDs and status pills wrapping badly** — especially Adapter Profiles and Requests.

---

# Top UX issues by priority

## P1 — Requests table is too dense and hard to scan

The Requests page is functionally useful, but the table is overloaded. In the screenshot:

* `View details` wraps into multiple lines.
* Request IDs and model names wrap heavily.
* Status badges wrap or become visually cramped.
* Too many columns compete for space.
* The failed row is highlighted, which is good, but the actual error context is still hard to read.

### Recommended fix

Reduce visible columns to:

```text
Created | Status | Request ID | Project | Requested Model | Route | Latency | Cost | Action
```

Move these to the drawer:

```text
API key prefix
served model
tokens
fallback
error code
raw JSON
completed_at
provider/model split details
```

Use compact components:

```text
CompactId
NoWrapStatusBadge
TableActionButton
ModelRouteCell
```

Action button should say simply:

```text
View
```

not `View details`, because the narrow action column causes wrapping.

---

## P1 — Adapter Profiles table is not usable at current width

The Adapter Profiles screenshot shows the worst table issue:

* Horizontal scrolling is required.
* Many columns are implementation details.
* Status badge wraps into tiny fragments: `Regi stere d`.
* Long IDs dominate the row.
* Important data is hidden among hashes and technical fields.

### Recommended fix

Make the table summary-first.

Visible columns:

```text
Gateway Profile | Domain | Status | Score | Created | Action
```

Move to detail drawer:

```text
adapter_profile_id
run_id
plan_id
evidence_hash
semantic_context_hash
slod_model_version
profile_version
metadata
activation history
```

Also enforce:

```css
.badge {
  white-space: nowrap;
}
```

For profile IDs, show compact copyable values:

```text
gw-e4e28c…e504
```

with full value in tooltip/copy action.

---

## P1 — Adaptation Plans page is misleading when service is not configured

The page correctly shows:

```text
Adaptation service is not configured.
```

But below it still shows:

* Visible plans: `0`
* Draft plans: `0`
* Requires approval: `0`
* Filters
* Plan Table
* No plans found

That makes it look like the service is working and just empty. It is not working.

### Recommended fix

When adaptation API returns “not configured” / 503:

* show a single unconfigured-state card
* hide stats cards
* hide filters
* hide plan table
* show a setup instruction

Example:

```text
Adaptation service is not configured

Set ADAPTATION_API_BASE_URL in the Conexus backend environment to enable the Adaptation BO proxy.

Expected local value:
http://localhost:5088
```

Add actions:

```text
Open Settings
Open Health
Retry
```

This pattern should be reused for Adaptation Runs, Queue, and Profiles.

---

## P1 — Filters are too exposed

Requests and Activity show all filters immediately. This makes the page feel heavy and pushes the real table far down.

### Recommended fix

Use a two-tier filter layout.

Default visible filters:

**Requests**

```text
Request ID
Status
Project
Model search
Limit
```

Advanced collapsed filters:

```text
API key ID
provider
served model
fallback used
created from/to
latency min/max
tokens min/max
cost min/max
sort
```

**Activity**

Default visible filters:

```text
Action
Resource type
Resource ID
Limit
```

Advanced collapsed filters:

```text
actor username
actor admin user id
created from/to
```

Add an active-filter summary row:

```text
Active filters: status=failed · project=manual-sanity-project · limit=50
```

---

## P1 — Raw JSON is too visually dominant

In Activity detail, the JSON block is readable, but it dominates the drawer. In Health, raw `/health` JSON is expanded by default and makes the page look like a developer console rather than an operator page.

### Recommended fix

Default raw JSON blocks should usually be collapsed.

Use this convention:

```text
Operational summary visible by default.
Raw JSON collapsed under “Debug JSON”.
```

Recommended defaults:

* Health raw JSON: collapsed
* Readiness raw JSON: collapsed
* Activity metadata: collapsed unless small
* Request raw row JSON: collapsed
* Adapter profile metadata: collapsed

Keep JSON available, just not visually primary.

---

# Page-by-page review

## Dashboard

**Status: good.**

This page is one of the strongest. It has useful metrics, quick start, shortcuts, and a clear smoke-test action.

### Improve later

* Rename `Run Smoke Test` to `Open Playground` unless it actually runs a test immediately.
* Add “Last refreshed” if dashboard data can become stale.
* Quick-start rows could use status icons instead of just “Complete.”

---

## Projects

**Status: good, with minor polish needed.**

The flow is clear: create project, select project, issue key, manage limits.

### Issues

* Project List screenshot shows text selection highlights. That is probably accidental, not UI.
* The page is long.
* Project API Keys and Project Limits could eventually be separated into tabs or anchored sections.

### Recommended fix

Keep as-is for now. Later add mini anchors:

```text
Project list | API keys | Limits | Usage/reservations
```

---

## Providers

**Status: good.**

Provider setup is understandable. The table is readable. Secret masking is clear.

### Issues

* Revoked provider row still has action buttons, which may be okay but should be visually clearer.
* `Last test` pill is wide compared to its content.
* Provider keys show masked values nicely.

### Recommended fix

Use status-based row treatment:

```text
Revoked rows: muted row, disabled Test button, no Revoke button
Active rows: normal
```

Not urgent.

---

## Playground

**Status: good operationally, slightly too tall.**

The page is clear and safe. The API key handling language is good.

### Issues

* Main Send action appears below the fold.
* Optional fields occupy too much vertical space.
* The system message default may make “optional” feel not optional.
* `Clear result` appears even when result may not exist.

### Recommended fix

Make form more compact:

* Put `Model`, `Temperature`, `Max tokens` in one row.
* Keep API key full-width.
* Make system message collapsed/optional by default.
* Keep Send button visible near the form top or immediately after user message.
* Show `Clear result` only when a result exists.

---

## Requests

**Status: functionally strong, visually overloaded.**

This should be the first major UX tightening target.

### Fix first

* Collapse advanced filters.
* Reduce table columns.
* Use compact IDs.
* Change action button to `View`.
* Prevent status/action wrapping.
* Move secondary details into drawer.

---

## Usage

**Status: good metrics, too much zero-data table noise.**

Top metric cards are good. The provider summary is good.

### Issues

* The daily time-series table shows many rows with zeroes.
* It creates lots of scrolling without much value.
* Time labels include exact time, which looks odd for daily buckets.

### Recommended fix

For time-series:

* Hide zero-only rows by default or collapse the table.
* Show only days with activity by default.
* Provide toggle: `Show zero days`.
* Format daily bucket as `Apr 29, 2026`, not `Apr 29, 2026, 7:21 PM`.

---

## Activity

**Status: good, but filter-heavy.**

The table is clean enough. The drawer is good.

### Issues

* Filters take too much vertical space.
* Metadata JSON is too prominent when open.
* `View` buttons are okay.

### Recommended fix

* Collapse advanced filters.
* Default metadata JSON closed.
* Render action/resource type as badges or code chips for easier scanning.

---

## Health

**Status: useful but too developer-console-like.**

The diagnostics card is good. Copy diagnostics is good.

### Issues

* Raw JSON blocks are too prominent.
* Health and Readiness cards are large for simple status values.

### Recommended fix

Add a top compact summary:

```text
Health: OK
Readiness: OK
Backend: localhost:8000
Last checked: ...
```

Keep raw JSON collapsed.

---

## Limits

**Status: acceptable landing page.**

It does its job, but it feels sparse.

### Recommended fix

This can remain simple. Later add:

* current selected project limit summary
* link to Projects with anchor/query
* short explanation of soft vs hard in a more compact card

---

## Routing

**Status: good.**

The env fallback warning is helpful. Provider candidates table is clear.

### Minor improvement

The warning could include action guidance:

```text
Configure provider credentials in Providers, then remove env fallback keys before production if BO-managed runtime config is required.
```

Not urgent.

---

## Adapter Profiles

**Status: functionally useful, table needs redesign.**

This is the second highest-priority table after Requests.

### Fix first

* Reduce columns.
* Add compact IDs.
* Prevent badge wrapping.
* Move hashes/context/model-version to drawer.
* Keep warning banner, but maybe shorten it.

---

# Recommended reusable components

Create these before doing page-specific rewrites:

## `CompactId`

Purpose: show long IDs consistently.

```text
gw-e4e28c…e504 [Copy]
```

Props:

```ts
value: string | null | undefined
prefixLength?: number
suffixLength?: number
label?: string
```

Use in:

* Requests
* Activity
* Adapter Profiles
* Projects
* Adaptation pages

## `TableActionButton`

A small no-wrap button.

```text
View
Copy
Retry
```

Prevents action text wrapping into unusable vertical stacks.

## `FilterPanel`

Supports:

```text
basic filters
advanced filters collapsed
active filter chips
clear all
apply
```

Use in:

* Requests
* Activity
* Adaptation Plans
* Adaptation Runs

## `DebugJsonSection`

Wrapper around `JsonBlock`.

Defaults:

```text
collapsed by default
label: Debug JSON
redaction note optional
```

Use in:

* Health
* Requests detail
* Activity detail
* Adapter Profiles detail

## `UnconfiguredServiceState`

For adaptation pages.

Props:

```ts
serviceName
envVarName
expectedLocalValue
retryAction
```

Use when `ADAPTATION_API_BASE_URL` is missing / 503.

---

# Recommended implementation order

## Slice A — Table readability foundation

Highest value.

Files likely touched:

```text
frontend/components/ui/index.tsx
frontend/app/globals.css
frontend/app/requests/page.tsx
frontend/app/adapter-profiles/page.tsx
```

Deliverables:

* `CompactId`
* no-wrap status badges
* no-wrap table actions
* Requests table reduced
* Adapter Profiles table reduced

## Slice B — Filter compaction

Files:

```text
frontend/components/ui/index.tsx
frontend/app/requests/page.tsx
frontend/app/activity/page.tsx
frontend/app/adaptation/plans/page.tsx
frontend/app/adaptation/runs/page.tsx
```

Deliverables:

* basic/advanced filter layout
* active filter chips
* shorter pages

## Slice C — Debug JSON and drawer polish

Files:

```text
frontend/components/ui/index.tsx
frontend/app/activity/page.tsx
frontend/app/requests/page.tsx
frontend/app/adapter-profiles/page.tsx
frontend/app/health/page.tsx
```

Deliverables:

* raw JSON collapsed by default
* drawers more sectioned
* metadata/debug clearly secondary

## Slice D — Adaptation unconfigured state

Files:

```text
frontend/app/adaptation/plans/page.tsx
frontend/app/adaptation/runs/page.tsx
frontend/app/adaptation/queue/page.tsx
frontend/app/adaptation/profiles/page.tsx
```

Deliverables:

* hide stats/filters/tables when service is unconfigured
* show clear setup card

## Slice E — Usage time-series cleanup

Files:

```text
frontend/app/usage/page.tsx
```

Deliverables:

* hide zero days by default
* better daily date formatting
* optional “show zero days”

---

# Cursor prompt for next pass

```md
You are working in `conexus`.

Goal: implement UX Slice A — table readability foundation.

Use the screenshots as the design evidence:
- Requests table is too dense and action/status cells wrap badly.
- Adapter Profiles table is too wide and status badge wraps into fragments.
- Long IDs dominate operational tables.

Do not redesign the whole app. Do not change backend endpoints. Do not add dependencies.

Scope:
- `frontend/components/ui/index.tsx`
- `frontend/app/globals.css`
- `frontend/app/requests/page.tsx`
- `frontend/app/adapter-profiles/page.tsx`
- tests where practical

Tasks:

1. Add `CompactId`
   - Shows shortened ID like `gw-e4e28c…e504`.
   - Full value remains copyable.
   - Handles null/undefined as `—`.
   - Uses existing copy behavior.
   - Prevents layout-breaking long IDs.

2. Harden status/action wrapping
   - Ensure `StatusBadge` does not wrap.
   - Add a small no-wrap action class or `TableActionButton`.
   - `View details` in Requests should become `View`.
   - Table action buttons must not break into vertical letters.

3. Reduce Requests table visible columns
   - Keep visible:
     - Created
     - Status
     - Request ID
     - Project
     - Requested Model
     - Route/provider summary
     - Latency
     - Cost
     - Action
   - Move or keep only in drawer:
     - API key prefix
     - tokens
     - fallback
     - error code
     - served model detail
     - raw JSON
   - Preserve drawer details and redaction.

4. Reduce Adapter Profiles table visible columns
   - Keep visible:
     - Gateway Profile
     - Domain
     - Status
     - Score
     - Created
     - Action
   - Move hashes, adapter profile ID, semantic context hash, SLOD version, profile version into drawer.
   - Preserve detail drawer and activation history.
   - Keep warning banner.

5. CSS
   - Add no-wrap table action styles.
   - Add compact ID styles.
   - Ensure table horizontal scroll still works when needed, but should be less necessary.

6. Tests
   - Add/adjust tests for:
     - `CompactId` rendering/copy/null state if practical.
     - Requests table still renders rows.
     - Adapter Profiles table still renders row and opens drawer if existing tests allow.
   - Do not over-test layout.

Validation:
- `cd frontend`
- `npm test -- --run`
- `npm run build`

Final response:
1. Files changed.
2. UX issues fixed.
3. Behavior preserved.
4. Tests added/updated.
5. Validation results.
6. Remaining UX slices.
```
