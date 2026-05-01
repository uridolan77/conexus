## Repo review — current non-adaptation BO state

The repo is now in a good testing position. The latest UX commit is substantial: it added `CompactId`, collapsed advanced filters, reduced dense tables, de-emphasized debug JSON, added clearer unconfigured-state handling, and improved usage time-series behavior. 

The core frontend foundation now has the right primitives: `CompactId`, `FilterPanel`, `StatusBadge`, `DetailDrawer`, `UnconfiguredServiceState`, `JsonBlock`, `PageState`, `MetricCard`, and the standard form/table/card components. 

For the non-adaptation BO, I would not do more architecture work. The next pass should be **pre-test polish and consistency**: remove small rough edges, make operational pages calmer, and make sure the user can manually test the full gateway loop without confusion.

---

# Main findings

## Good enough to start testing soon

These are now broadly usable:

* Dashboard
* Projects
* Providers
* Playground
* Requests
* Usage
* Activity
* Health
* Settings
* Limits
* Routing
* Adapter Profiles / gateway registry

The Requests page is much better after table reduction. It now keeps only the useful columns visible and moves secondary details into the drawer. It also redacts raw request detail JSON and collapses it by default. 

Adapter Profiles is also much more readable. The table now shows gateway profile, domain, status, score, created, and action, while the technical hashes/version fields moved into the drawer. 

The CSS now has the necessary foundation for no-wrap badges/actions and compact IDs. 

---

# Remaining non-adaptation polish issues

## P1 — Active filter summaries are incomplete

Requests now has a good `FilterPanel`, but the active summary only includes basic fields: request ID, status, project, model search, and limit. Advanced filters like provider, error code, fallback, dates, token range, latency range, and cost range are omitted from the summary. 

Same issue likely exists in Activity.

**Fix:** summary should include all non-empty filters, using short labels.

---

## P1 — Request datetime filters may be ambiguous

Requests uses `datetime-local` inputs for created/completed filters. Browser `datetime-local` values do not include timezone. If the backend expects ISO/UTC semantics, this can create confusing filters.

**Fix options:**

* simplest: label them clearly as local time and convert to ISO before sending
* safer for operators: keep text ISO inputs with examples like `2026-04-30T00:00:00Z`
* best later: add a small `DateTimeField` helper that normalizes values

For pre-test, I would either restore ISO text inputs or explicitly convert `datetime-local` values to ISO strings before query construction.

---

## P1 — Adapter Profiles still has one stale `StatusBadge` cast

Inside activation history:

```tsx
<StatusBadge status={a.status as Parameters<typeof StatusBadge>[0]["status"]} />
```

`StatusBadge` now accepts `string`, so this should be:

```tsx
<StatusBadge status={a.status} />
```

This is tiny but should be cleaned up. 

---

## P1 — Dashboard action wording is misleading

`Run Smoke Test` sounds like it executes something immediately. In reality it opens the Playground/smoke-test flow.

Use:

```text
Open Playground
```

or:

```text
Test Gateway
```

Same for links from Requests empty state.

---

## P2 — `CompactId` copy buttons may be too visually heavy in tables

`CompactId` is correct, but it includes a full `Copy` button. In dense tables this may still be too much.

Later variant:

```tsx
<CompactId value={id} label="Copy" compact />
```

or a copy icon button. For now this is not blocking.

---

## P2 — Playground is still too tall

The Playground is safe and functional, but before testing it would benefit from a compact layout:

* API key full width
* model / temperature / max tokens in one row
* system message collapsed or optional by default
* Send button visible without scrolling
* show `Clear result` only after a result exists

This is not a correctness issue, but it will make manual testing smoother.

---

## P2 — Projects page is long but acceptable

Projects works as a single vertical workflow. Do not restructure it now. Only polish:

* use `CompactId` for Project ID
* ensure plaintext key display remains once-only
* ensure “Selected” state is visually clear
* avoid unnecessary scroll jumps after issuing a key

---

## P2 — Providers revoked-row behavior should be calmer

Providers is readable. The only polish: revoked rows should be clearly muted, and destructive actions should be disabled/hidden where they no longer apply.

---

# Recommended Cursor prompt — pre-test polish, non-adaptation only

Use this as the next pass.

````md
# Conexus BO pre-test polish pass — non-adaptation features only

You are working in `conexus`.

Goal: polish all non-adaptation BO features so we can manually test the Conexus gateway flow with confidence.

Do not touch `/adaptation/*` pages in this pass. The only exception is shared UI components if needed by non-adaptation pages.

Include these pages:

- `/`
- `/projects`
- `/providers`
- `/playground`
- `/requests`
- `/usage`
- `/activity`
- `/health`
- `/settings`
- `/limits`
- `/routing`
- `/adapter-profiles`

Do not redesign the app. Do not add backend features unless a tiny bug fix is required. Do not add dependencies. Preserve existing behavior and tests.

Validation required:

```bash
cd frontend
npm test -- --run
npm run build
````

If backend files are changed:

```bash
cd backend
python -m pytest
python -m ruff check app tests
```

---

## Phase 0 — inspect current state

First inspect:

```text
frontend/app/page.tsx
frontend/app/projects/page.tsx
frontend/app/providers/page.tsx
frontend/app/playground/page.tsx
frontend/app/requests/page.tsx
frontend/app/usage/page.tsx
frontend/app/activity/page.tsx
frontend/app/health/page.tsx
frontend/app/settings/page.tsx
frontend/app/limits/page.tsx
frontend/app/routing/page.tsx
frontend/app/adapter-profiles/page.tsx
frontend/components/ui/index.tsx
frontend/app/globals.css
frontend/lib/format.ts
frontend/lib/redaction.ts
```

Summarize likely changes before editing.

---

## Phase 1 — cross-cutting cleanup

### 1. Active filter summaries

Fix active filter summaries so they include all non-empty filters.

Requests summary should include, with short labels:

* request_id
* status
* project_id
* api_key_id
* provider
* requested_model
* model
* model_search
* fallback_used
* error_code
* created_from
* created_to
* completed_from
* completed_to
* min_latency_ms
* max_latency_ms
* min_total_tokens
* max_total_tokens
* min_estimated_cost
* max_estimated_cost
* sort_by
* sort_dir
* limit

Activity summary should include:

* actor_username
* actor_admin_user_id
* action
* resource_type
* resource_id
* created_from
* created_to
* limit

Keep summaries readable. Use short labels like:

```text
status=failed · provider=openai · error=provider_timeout · limit=50
```

Do not show “No active filters” when advanced filters are active.

### 2. Remove stale StatusBadge casts

Search for:

```text
Parameters<typeof StatusBadge>
```

Remove stale casts now that `StatusBadge` accepts `string`.

Known file:

```text
frontend/app/adapter-profiles/page.tsx
```

### 3. Standardize debug JSON titles

Use:

```text
Debug JSON
```

for raw/debug blocks, not mixed names like `Metadata JSON`, unless the block is truly business metadata.

Default raw/debug JSON should be collapsed.

Check:

* requests detail
* activity detail
* adapter profile detail
* health
* readiness

### 4. No-wrap operational actions

Ensure table action buttons do not wrap.

Use existing CSS/classes:

```text
.table-action
.badge { white-space: nowrap; }
```

Check:

* Requests
* Activity
* Adapter Profiles
* Providers
* Projects

---

## Phase 2 — Requests polish

File:

```text
frontend/app/requests/page.tsx
```

Tasks:

1. Keep reduced table columns.
2. Keep `CompactId` for request IDs.
3. Ensure detail drawer contains all secondary fields:

   * API key prefix
   * prompt tokens
   * completion tokens
   * total tokens
   * fallback
   * error code/message
   * completed_at
   * raw redacted Debug JSON
4. Replace token display in detail with `formatTokens` where applicable.
5. Review datetime filters:

   * either keep ISO text inputs, or
   * if using `datetime-local`, convert values to ISO strings before sending to backend.
   * Do not silently send ambiguous local datetime values unless clearly labelled.
6. Empty state button should say `Open Playground` or `Test Gateway`, not misleading “Run Smoke Test” unless it runs immediately.

Do not redesign filters again.

---

## Phase 3 — Activity polish

File:

```text
frontend/app/activity/page.tsx
```

Tasks:

1. Active filter summary includes advanced filters.
2. Metadata/debug JSON remains redacted and collapsed.
3. Consider using `CompactId` for resource IDs if currently long.
4. Ensure View action never wraps.
5. Keep drawer readable and sectioned.

Do not add backend audit redaction in this pass unless an obvious bug is found.

---

## Phase 4 — Adapter Profiles polish

File:

```text
frontend/app/adapter-profiles/page.tsx
```

Tasks:

1. Remove stale `StatusBadge` type cast.
2. Keep summary table reduced.
3. Use `CompactId` for gateway profile IDs.
4. Consider `CompactId` for previous gateway profile ID in activation history.
5. Rename drawer JSON block to `Debug JSON` or `Metadata JSON` consistently. Prefer `Debug JSON` if it is raw metadata.
6. Keep server/frontend redaction behavior.

Do not call `/internal/*` from browser.

---

## Phase 5 — Dashboard / smoke-test wording

File:

```text
frontend/app/page.tsx
```

Tasks:

1. Rename `Run Smoke Test` to `Open Playground` or `Test Gateway`.
2. Any link that navigates to `/smoke-tests` can remain, but the visible wording should not imply immediate execution.
3. If dashboard metrics can be stale, add a subtle `Last refreshed` line only if data already exists.
4. Do not add auto-refresh.

---

## Phase 6 — Playground compactness

File:

```text
frontend/app/playground/page.tsx
```

Tasks:

1. Make the form slightly more compact.
2. Put model, temperature, and max tokens in one row if responsive CSS supports it.
3. Keep API key full-width.
4. Consider collapsing system message if low-risk; otherwise leave it.
5. Show `Clear result` only when a result exists.
6. Preserve security:

   * no localStorage/sessionStorage
   * no key in debug output
   * exact key redaction remains
   * API key remains in memory only

Do not implement streaming.

---

## Phase 7 — Projects polish

Files:

```text
frontend/app/projects/page.tsx
frontend/components/projects/*
```

Tasks:

1. Use `CompactId` for project ID where displayed.
2. Ensure selected project state is clear.
3. Ensure switching projects clears latest issued plaintext key.
4. Ensure plaintext key is only visible immediately after issue.
5. Do not restructure into tabs yet.
6. Do not add new project delete action.

---

## Phase 8 — Providers polish

File:

```text
frontend/app/providers/page.tsx
```

Tasks:

1. Revoked providers should be visually muted.
2. Revoke button should be disabled/hidden for revoked providers if currently active.
3. Test button should be disabled for revoked providers if not already.
4. Preserve secret masking.
5. Do not display raw provider keys.

---

## Phase 9 — Usage polish

File:

```text
frontend/app/usage/page.tsx
```

Tasks:

1. Confirm zero-activity time buckets are hidden by default or controlled by toggle.
2. Daily bucket labels should be date-only for day buckets.
3. Metric cards should use `formatPercentRatio`, `formatCost`, `formatTokens`, `formatLatency`.
4. Empty/null values render as `—`.
5. Do not add charts.

---

## Phase 10 — Health / Settings / Limits / Routing polish

Files:

```text
frontend/app/health/page.tsx
frontend/app/settings/page.tsx
frontend/app/limits/page.tsx
frontend/app/routing/page.tsx
```

Health:

* raw JSON collapsed by default
* summary remains easy to scan
* copy diagnostics still works

Settings:

* keep read-only
* do not invent backend config endpoint
* wording should be clear that secrets are not shown

Limits:

* keep as landing page
* make links/actions clear
* no destructive repair action without confirmation

Routing:

* keep env fallback warning
* warning should tell operator what to do:
  “Configure provider credentials in Providers, then remove env fallback keys before production if BO-managed runtime config is required.”
* no routing behavior changes

---

## Phase 11 — tests

Add/update focused tests only where practical:

* active filter summaries include advanced filters
* `StatusBadge` cast removal does not break Adapter Profiles render
* Playground clear result visibility if tested
* Requests table still renders row and drawer
* Usage zero toggle if existing tests cover it

Do not over-test layout.

---

## Phase 12 — validation

Run:

```bash
cd frontend
npm test -- --run
npm run build
```

If backend changed:

```bash
cd backend
python -m pytest
python -m ruff check app tests
```

---

## Final response

Report:

1. Files changed.
2. Non-adaptation pages polished.
3. Behavior preserved.
4. Security constraints preserved.
5. Tests added/updated.
6. Exact validation results.
7. Remaining issues before manual testing.

````

---

# Manual test checklist after this pass

Use this to test with peace of mind:

```text
[ ] Login works.
[ ] Dashboard loads and metrics make sense.
[ ] Providers: create OpenAI/Anthropic provider config.
[ ] Providers: test provider succeeds/fails clearly.
[ ] Projects: create project.
[ ] Projects: issue API key.
[ ] Project API key plaintext is shown once only.
[ ] Playground: paste key and send non-streaming request.
[ ] Playground: key is not persisted after refresh.
[ ] Requests: new request row appears.
[ ] Requests: detail drawer opens and contains no secrets.
[ ] Usage: request count/tokens/cost update or nulls render safely.
[ ] Activity: project/key/provider actions appear.
[ ] Activity detail JSON is redacted.
[ ] Limits: page explains modes and links to Projects.
[ ] Routing: provider candidates are understandable.
[ ] Adapter Profiles: registry row displays cleanly.
[ ] Health: /health and /readyz are OK.
[ ] Settings: safe read-only info only.
[ ] No table has broken vertical buttons.
[ ] No status badge wraps into fragments.
[ ] No full secret appears anywhere.
````

Bottom line: the repo is close. Do this small non-adaptation polish pass, then start manual end-to-end testing.
