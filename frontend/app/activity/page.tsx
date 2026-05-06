"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { useUrlFilters } from "@/hooks/useUrlFilters";
import {
  Button,
  Card,
  DetailDrawer,
  EmptyState,
  ErrorState,
  Field,
  FilterPanel,
  FormRow,
  Input,
  JsonBlock,
  KeyValueGrid,
  LoadingState,
  PageHeader,
  SectionHeader,
  Table,
} from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { listAuditLogs } from "@/lib/admin/audit";
import { redactSensitiveObject } from "@/lib/redaction";
import type { AuditListResponse, AuditLogItem } from "@/lib/types";

const DEFAULT_LIMIT = 50;

type Filters = {
  actor_username: string;
  actor_admin_user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  created_from: string;
  created_to: string;
  limit: string;
};

const defaultFilters: Filters = {
  actor_username: "",
  actor_admin_user_id: "",
  action: "",
  resource_type: "",
  resource_id: "",
  created_from: "",
  created_to: "",
  limit: String(DEFAULT_LIMIT),
};

const ACTIVITY_FILTER_KEYS = [
  "actor_username",
  "actor_admin_user_id",
  "action",
  "resource_type",
  "resource_id",
  "created_from",
  "created_to",
  "limit",
] as const satisfies readonly (keyof Filters)[];

function activeFiltersSummary(filters: Filters) {
  const parts: string[] = [];

  function clean(value: string) {
    return value.trim();
  }

  function short(value: string, max = 28) {
    const v = clean(value);
    if (!v) return "";
    return v.length <= max ? v : `${v.slice(0, max - 1)}…`;
  }

  function add(label: string, value: string) {
    const v = clean(value);
    if (!v) return;
    parts.push(`${label}=${short(v)}`);
  }

  add("act", filters.action);
  add("type", filters.resource_type);
  add("rid", filters.resource_id);
  add("user", filters.actor_username);
  add("admin", filters.actor_admin_user_id);
  add("from", filters.created_from);
  add("to", filters.created_to);
  add("limit", filters.limit);

  return parts.length ? `Active filters: ${parts.join(" · ")}` : "No active filters.";
}

export default function ActivityPage() {
  const { parseFromSearch, replaceUrl } = useUrlFilters<Filters>({
    pathname: "/activity",
    defaults: defaultFilters,
    keys: ACTIVITY_FILTER_KEYS,
  });
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AuditListResponse | null>(null);
  const [selected, setSelected] = useState<AuditLogItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const limit = Number(filters.limit || DEFAULT_LIMIT);

  async function load(nextFilters: Filters, nextOffset: number) {
    setLoading(true);
    setError(null);
    try {
      const result = await listAuditLogs({
        limit,
        offset: nextOffset,
        actor_username: nextFilters.actor_username || undefined,
        actor_admin_user_id: nextFilters.actor_admin_user_id || undefined,
        action: nextFilters.action || undefined,
        resource_type: nextFilters.resource_type || undefined,
        resource_id: nextFilters.resource_id || undefined,
        created_from: nextFilters.created_from || undefined,
        created_to: nextFilters.created_to || undefined,
      });
      if (!result.ok) {
        setData(null);
        setError(result.error.message);
        return;
      }
      setData(result.data);
      setOffset(nextOffset);

      replaceUrl({ ...nextFilters, limit: String(limit) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const initial =
      typeof window === "undefined" ? defaultFilters : parseFromSearch(window.location.search);
    setFilters(initial);
    void load(initial, 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyFilters(e: FormEvent) {
    e.preventDefault();
    setSelected(null);
    void load(filters, 0);
  }

  function clearFilters() {
    setFilters(defaultFilters);
    setOffset(0);
    setSelected(null);
    void load(defaultFilters, 0);
  }

  function closeDetail() {
    setSelected(null);
  }

  const items = data?.items ?? [];
  const canPrev = offset > 0;
  const canNext = data ? offset + limit < data.total : false;

  const rangeLabel = useMemo(() => {
    if (!data) return "—";
    if (data.total === 0) return "0";
    const start = Math.min(data.total, offset + 1);
    const end = Math.min(data.total, offset + items.length);
    return `${start}–${end} of ${data.total}`;
  }, [data, offset, items.length]);

  return (
    <>
      <PageHeader
        eyebrow="Admin"
        title="Activity"
        description="Operator actions in the back-office (audit log)."
      />

      <Card>
        <SectionHeader title="Filters" description="Filter audit logs by actor, action, and resource." />
        <form className="stack" onSubmit={applyFilters}>
          <FilterPanel
            summary={<p className="muted">{activeFiltersSummary(filters)}</p>}
            basic={
              <>
                <FormRow>
                  <Field label="Action">
                    <Input
                      value={filters.action}
                      onChange={(e) => setFilters((s) => ({ ...s, action: e.target.value }))}
                      placeholder="project_api_key.issue"
                    />
                  </Field>
                  <Field label="Resource type">
                    <Input
                      value={filters.resource_type}
                      onChange={(e) => setFilters((s) => ({ ...s, resource_type: e.target.value }))}
                      placeholder="project_api_key"
                    />
                  </Field>
                  <Field label="Resource id">
                    <Input
                      value={filters.resource_id}
                      onChange={(e) => setFilters((s) => ({ ...s, resource_id: e.target.value }))}
                      placeholder="(id)"
                    />
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Limit">
                    <Input
                      value={filters.limit}
                      onChange={(e) => setFilters((s) => ({ ...s, limit: e.target.value }))}
                      inputMode="numeric"
                      placeholder="50"
                    />
                  </Field>
                </FormRow>
              </>
            }
            advanced={
              <>
                <FormRow>
                  <Field label="Actor username">
                    <Input
                      value={filters.actor_username}
                      onChange={(e) => setFilters((s) => ({ ...s, actor_username: e.target.value }))}
                      placeholder="admin"
                    />
                  </Field>
                  <Field label="Actor admin user id">
                    <Input
                      value={filters.actor_admin_user_id}
                      onChange={(e) => setFilters((s) => ({ ...s, actor_admin_user_id: e.target.value }))}
                      placeholder="(uuid)"
                    />
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Created from (ISO)">
                    <Input
                      value={filters.created_from}
                      onChange={(e) => setFilters((s) => ({ ...s, created_from: e.target.value }))}
                      placeholder="2026-01-01T00:00:00Z"
                    />
                  </Field>
                  <Field label="Created to (ISO)">
                    <Input
                      value={filters.created_to}
                      onChange={(e) => setFilters((s) => ({ ...s, created_to: e.target.value }))}
                      placeholder="2026-01-31T23:59:59Z"
                    />
                  </Field>
                </FormRow>
              </>
            }
            advancedLabel="Advanced filters"
          />

          <div className="inline-actions">
            <Button type="submit">Apply</Button>
            <Button type="button" variant="secondary" onClick={clearFilters}>
              Clear
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <SectionHeader title="Audit log" description={`Showing ${rangeLabel}`} />

        {error && <ErrorState message={error} />}

        {loading ? (
          <LoadingState label="Loading audit logs..." />
        ) : items.length === 0 ? (
          <EmptyState title="No audit logs found">Try clearing filters or widening the time range.</EmptyState>
        ) : (
          <>
            <Table aria-label="Audit logs">
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Resource type</th>
                  <th>Resource id</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{formatDateTime(item.created_at)}</td>
                    <td>{item.actor_username ?? "—"}</td>
                    <td>
                      <code>{item.action}</code>
                    </td>
                    <td>
                      <code>{item.resource_type}</code>
                    </td>
                    <td>
                      <span className="inline-actions">
                        <code className="wrap-anywhere">{item.resource_id ?? "—"}</code>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => setSelected(item)}
                          aria-label="View"
                        >
                          View
                        </Button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>

            <div className="inline-actions pagination-actions">
              <Button
                type="button"
                variant="secondary"
                disabled={!canPrev || loading}
                onClick={() => void load(filters, Math.max(0, offset - limit))}
              >
                Previous
              </Button>
              <span className="muted">{rangeLabel}</span>
              <Button
                type="button"
                variant="secondary"
                disabled={!canNext || loading}
                onClick={() => void load(filters, offset + limit)}
              >
                Next
              </Button>
            </div>
          </>
        )}
      </Card>

      <DetailDrawer open={Boolean(selected)} onClose={closeDetail} title="Audit detail">
        {selected ? (
          <div className="stack">
            <KeyValueGrid
              items={[
                { label: "event_id", value: <code className="wrap-anywhere">{selected.id}</code> },
                { label: "actor_username", value: selected.actor_username ?? "—" },
                { label: "actor_admin_user_id", value: selected.actor_admin_user_id ?? "—" },
                { label: "action", value: <code>{selected.action}</code> },
                { label: "resource_type", value: <code>{selected.resource_type}</code> },
                { label: "resource_id", value: selected.resource_id ?? "—" },
                { label: "created_at", value: formatDateTime(selected.created_at) },
              ]}
            />
            <JsonBlock value={redactSensitiveObject(selected.metadata)} title="Debug JSON" defaultOpen={false} />
          </div>
        ) : null}
      </DetailDrawer>
    </>
  );
}

