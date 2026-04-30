# BO Frontend Conventions

Practical handbook for every new BO page added to Conexus.

---

## Page structure

Every BO page follows this pattern:

```tsx
export default function MyPage() {
  // ... state & handlers

  return (
    <>
      <PageHeader
        eyebrow="Section name"
        title="Page Title"
        description="Optional one-liner describing the page."
        actions={<Button onClick={...}>Action</Button>}
      />

      {error && <ErrorState message={error} />}
      {success && <Alert tone="success">{success}</Alert>}

      <Card>
        <SectionHeader title="Section" />
        <PageState loading={loading} error={sectionError} empty={rows.length === 0}>
          {/* content */}
        </PageState>
      </Card>
    </>
  );
}
```

---

## Data fetching

Pages must not build URLs by hand where a domain API module exists.

**Preferred pattern (manual fetch):**
```ts
const result = await listProjects();
if (!result.ok) {
  setError(result.error.message);
  return;
}
setProjects(result.data);
```

**Preferred pattern (hook, for new pages):**
```ts
const { data, loading, error, reload } = useAdminResource(
  () => listProjects(),
  [],
);
```

Use `useAdminResource` for new pages. It handles loading/error/data consistently, prevents state updates after unmount, and guards against stale responses.

---

## Error handling

- Use `AdminResult<T>` everywhere. Never call `fetch` directly in pages.
- Use `parseApiError` to normalize errors.
- Do not render raw `unknown` objects directly. Use `<JsonBlock>` only for explicit debug sections.
- Do not render secrets from errors.
- When setting an error, clear any stale success message: call `setSuccess(null)` alongside `setError(msg)`.

---

## Formatting

Use these and only these from `lib/format.ts`:

| Function | Use for |
|---|---|
| `formatDateTime` | Any ISO date/time string |
| `formatCost` | USD cost values |
| `formatPercentRatio` | Fraction 0–1 → "12.3%" |
| `formatPercentValue` | Already-percent value → "12.3%" |
| `formatTokens` | Token counts |
| `formatLatency` | Millisecond durations |
| `formatNullable` | Null-safe fallback rendering |
| `formatDurationSeconds` | Second-based durations |

**Never create local page-level formatters** unless the format is genuinely page-specific and cannot be expressed by the above.

---

## Tables

- Use `<Table>` (JSX) for complex tables with custom cell rendering.
- Use `<DataTable>` only for simple read-only tabular data with uniform column rendering.
- `DataTable` accepts `emptyMessage` for inline empty rows.
- Wrap tables in `<div className="table-wrap">` for overflow; `DataTable` does this automatically.

---

## Detail drawers

Use `<DetailDrawer>` for row detail panels:
- Closes on Escape key (built-in).
- Closes on backdrop click (built-in).
- Close button has accessible `aria-label="Close"`.
- Uses `aria-labelledby` pointing to the drawer title (built-in).
- Must not display secrets.
- **No focus trap yet** — keyboard navigation stays in page. Add focus trap when accessibility is hardened.

---

## Secrets policy

| Value | Display rule |
|---|---|
| Provider API key | Never display |
| Project API key plaintext | Show once, immediately after issuance only |
| Internal gateway API key | Never display |
| Auth / encryption secrets | Never display |
| Copied values | Only on explicit user action (CopyButton) |

---

## UI primitives

Available in `components/ui/index.tsx`:

**Layout:** `PageHeader`, `SectionHeader`, `Card`, `FormRow`, `SectionGap`, `Toolbar`, `FilterBar`

**Forms:** `Field`, `Input`, `Select`, `Textarea`, `FieldError`, `HelpText`

**Actions:** `Button`, `LinkButton`, `CopyButton`, `CopyableCode`, `ConfirmButton`, `RefreshButton`

**Status:** `Badge`, `StatusBadge`, `StatusPill`, `Alert`, `EmptyState`, `ErrorState`, `LoadingState`, `PageState`

**Data display:** `Table`, `DataTable`, `KeyValueGrid`, `StatCard`, `MetricCard`, `JsonBlock`, `SecretValue`, `InlineCode`, `CodeChip`, `DetailDrawer`

**Do not add a new primitive** unless it will be used by 2+ pages.

---

## Testing requirements for every new BO page

1. **Utility tests** — any pure functions introduced by the page.
2. **Component tests** — empty/error/loaded states rendered correctly.
3. **User-flow test** — at least one test where a form mutates data.

Use `vi.mock("@/lib/admin/...")` with all data defined **inside the factory** to avoid hoisting issues.

---

## Query params

Use `buildQuery` from `lib/api.ts` instead of `URLSearchParams` directly:

```ts
import { buildQuery } from "@/lib/api";

getAdminJson(`/admin/requests${buildQuery({ limit: 50, project_id: id })}`);
```

`buildQuery` skips `null`, `undefined`, and `""` values automatically.

---

## Remaining known gaps

- **ESLint not configured** — add before extracting as reusable package.
- **DetailDrawer no focus trap** — keyboard users can tab outside the drawer.
- **`window.confirm` still used** in `ConfirmAction` — replace before accessibility audit.
- **No React Query / SWR** — `useAdminResource` covers immediate needs; evaluate caching when request volume grows.
- **No design-token extraction into package** — planned post-MVP.
