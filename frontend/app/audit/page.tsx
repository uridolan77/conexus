"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  FormRow,
  Input,
  JsonBlock,
  LoadingState,
  PageHeader,
  Table,
} from "@/components/ui";
import { BACKEND_BASE, adminSessionFetch, formatApiError, formatDate, readJsonSafe } from "@/lib/api";
import type { AuditListResponse, AuditLogItem } from "@/lib/types";

type Filters = {
  actor_admin_user_id: string;
  actor_username: string;
  action: string;
  resource_type: string;
  resource_id: string;
  created_from: string;
  created_to: string;
};

const DEFAULT_LIMIT = 50;

function buildQuery(filters: Filters, limit: number, offset: number) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  for (const [k, v] of Object.entries(filters)) {
    const value = v.trim();
    if (value) params.set(k, value);
  }

  return params.toString();
}

export default function AuditPage() {
  const [filters, setFilters] = useState<Filters>({
    actor_admin_user_id: "",
    actor_username: "",
    action: "",
    resource_type: "",
    resource_id: "",
    created_from: "",
    created_to: "",
  });
  const [appliedFilters, setAppliedFilters] = useState<Filters>(filters);
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AuditListResponse | null>(null);
  const [selected, setSelected] = useState<AuditLogItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const query = useMemo(
    () => buildQuery(appliedFilters, limit, offset),
    [appliedFilters, limit, offset],
  );

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError(null);
      try {
        const res = await adminSessionFetch(`${BACKEND_BASE}/admin/audit?${query}`, {
          method: "GET",
        });
        const body = (await readJsonSafe(res)) as unknown;
        if (!res.ok) {
          setError(body);
          setData(null);
          return;
        }
        if (cancelled) return;
        setData(body as AuditListResponse);
      } catch (e) {
        if (cancelled) return;
        setError(e);
        setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [query]);

  const canPrev = offset > 0;
  const canNext = data ? offset + limit < data.total : false;

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Admin"
        title="Audit"
        description="Sensitive back-office actions (provider credentials, project keys, and limits)."
      />

      <Card>
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            setOffset(0);
            setAppliedFilters(filters);
          }}
        >
          <FormRow>
            <Field label="Actor username">
              <Input
                value={filters.actor_username}
                placeholder="admin"
                onChange={(e) =>
                  setFilters((s) => ({ ...s, actor_username: e.target.value }))
                }
              />
            </Field>
            <Field label="Actor admin user id">
              <Input
                value={filters.actor_admin_user_id}
                placeholder="(uuid hex)"
                onChange={(e) =>
                  setFilters((s) => ({ ...s, actor_admin_user_id: e.target.value }))
                }
              />
            </Field>
          </FormRow>

          <FormRow>
            <Field label="Action">
              <Input
                value={filters.action}
                placeholder="project_api_key.issue"
                onChange={(e) => setFilters((s) => ({ ...s, action: e.target.value }))}
              />
            </Field>
            <Field label="Resource type">
              <Input
                value={filters.resource_type}
                placeholder="project_api_key"
                onChange={(e) =>
                  setFilters((s) => ({ ...s, resource_type: e.target.value }))
                }
              />
            </Field>
            <Field label="Resource id">
              <Input
                value={filters.resource_id}
                placeholder="(id)"
                onChange={(e) =>
                  setFilters((s) => ({ ...s, resource_id: e.target.value }))
                }
              />
            </Field>
          </FormRow>

          <FormRow>
            <Field label="Created from (ISO)">
              <Input
                value={filters.created_from}
                placeholder="2026-01-01T00:00:00Z"
                onChange={(e) =>
                  setFilters((s) => ({ ...s, created_from: e.target.value }))
                }
              />
            </Field>
            <Field label="Created to (ISO)">
              <Input
                value={filters.created_to}
                placeholder="2026-01-31T23:59:59Z"
                onChange={(e) => setFilters((s) => ({ ...s, created_to: e.target.value }))}
              />
            </Field>
          </FormRow>

          <div className="inline-actions">
            <Button type="submit" variant="primary">
              Apply filters
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const cleared: Filters = {
                  actor_admin_user_id: "",
                  actor_username: "",
                  action: "",
                  resource_type: "",
                  resource_id: "",
                  created_from: "",
                  created_to: "",
                };
                setFilters(cleared);
                setAppliedFilters(cleared);
                setOffset(0);
                setSelected(null);
              }}
            >
              Clear
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <div className="inline-actions" style={{ justifyContent: "space-between" }}>
          <div className="muted">
            {data ? (
              <>
                Showing <strong>{Math.min(data.total, offset + 1)}</strong>–
                <strong>{Math.min(data.total, offset + data.items.length)}</strong> of{" "}
                <strong>{data.total}</strong>
              </>
            ) : (
              "—"
            )}
          </div>
          <div className="inline-actions">
            <Button
              type="button"
              variant="secondary"
              disabled={!canPrev || loading}
              onClick={() => setOffset((o) => Math.max(0, o - limit))}
            >
              Prev
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={!canNext || loading}
              onClick={() => setOffset((o) => o + limit)}
            >
              Next
            </Button>
          </div>
        </div>

        {loading && !data && <LoadingState label="Loading audit logs..." />}
        {Boolean(error) && <ErrorState message={formatApiError(error)} />}
        {!loading && !error && data && data.items.length === 0 && (
          <EmptyState title="No audit logs found">
            Try clearing filters or widening the time range.
          </EmptyState>
        )}

        {!error && data && data.items.length > 0 && (
          <Table aria-label="Audit logs">
            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Resource</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => setSelected(item)}
                  style={{ cursor: "pointer" }}
                >
                  <td>{formatDate(item.created_at)}</td>
                  <td>{item.actor_username ?? "-"}</td>
                  <td>
                    <code>{item.action}</code>
                  </td>
                  <td>
                    <code>
                      {item.resource_type}
                      {item.resource_id ? `:${item.resource_id}` : ""}
                    </code>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {selected && (
        <Card>
          <PageHeader
            title="Audit detail"
            description={
              <>
                <code>{selected.id}</code>
              </>
            }
            actions={
              <Button type="button" variant="ghost" onClick={() => setSelected(null)}>
                Close
              </Button>
            }
          />
          <JsonBlock
            title="Metadata"
            value={{
              actor_admin_user_id: selected.actor_admin_user_id,
              actor_username: selected.actor_username,
              action: selected.action,
              resource_type: selected.resource_type,
              resource_id: selected.resource_id,
              created_at: selected.created_at,
              metadata: selected.metadata,
            }}
            defaultOpen
          />
        </Card>
      )}
    </div>
  );
}

