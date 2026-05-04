"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  CompactId,
  CopyButton,
  DetailDrawer,
  EmptyState,
  ErrorState,
  Field,
  FilterPanel,
  FormRow,
  Input,
  JsonBlock,
  KeyValueGrid,
  LinkButton,
  LoadingState,
  PageHeader,
  SectionHeader,
  Select,
  StatCard,
  StatusBadge,
  Table,
} from "@/components/ui";
import { formatCost, formatDateTime, formatLatency, formatTokens } from "@/lib/format";
import { getRequest, listRequests } from "@/lib/admin/requests";
import { listProjects } from "@/lib/admin/projects";
import { redactSensitiveObject } from "@/lib/redaction";
import type { ProjectRow, RequestDetail, RequestListResponse, RequestRow } from "@/lib/types";

const DEFAULT_LIMIT = "50";

type Filters = {
  limit: string;
  request_id: string;
  status: string;
  project_id: string;
  api_key_id: string;
  provider: string;
  requested_model: string;
  model: string;
  model_search: string;
  fallback_used: string;
  error_code: string;
  created_from: string;
  created_to: string;
  completed_from: string;
  completed_to: string;
  min_latency_ms: string;
  max_latency_ms: string;
  min_total_tokens: string;
  max_total_tokens: string;
  min_estimated_cost: string;
  max_estimated_cost: string;
  sort_by: string;
  sort_dir: string;
};

const defaultFilters: Filters = {
  limit: DEFAULT_LIMIT,
  request_id: "",
  status: "",
  project_id: "",
  api_key_id: "",
  provider: "",
  requested_model: "",
  model: "",
  model_search: "",
  fallback_used: "",
  error_code: "",
  created_from: "",
  created_to: "",
  completed_from: "",
  completed_to: "",
  min_latency_ms: "",
  max_latency_ms: "",
  min_total_tokens: "",
  max_total_tokens: "",
  min_estimated_cost: "",
  max_estimated_cost: "",
  sort_by: "created_at",
  sort_dir: "desc",
};

function empty(value: string | number | null | undefined) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function activeFiltersSummary(filters: Filters) {
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

  function addBool(label: string, value: string) {
    const v = clean(value);
    if (!v) return;
    parts.push(`${label}=${v === "true" ? "yes" : v === "false" ? "no" : short(v)}`);
  }

  function addRange(label: string, min: string, max: string, unit?: string) {
    const a = clean(min);
    const b = clean(max);
    if (!a && !b) return;
    const u = unit ?? "";
    if (a && b) parts.push(`${label}=${short(a)}–${short(b)}${u}`);
    else if (a) parts.push(`${label}>=${short(a)}${u}`);
    else parts.push(`${label}<=${short(b)}${u}`);
  }

  const parts: string[] = [];

  add("req", filters.request_id);
  add("st", filters.status);
  add("proj", filters.project_id);
  add("key", filters.api_key_id);
  add("prov", filters.provider);
  add("reqModel", filters.requested_model);
  add("model", filters.model);
  add("search", filters.model_search);
  addBool("fb", filters.fallback_used);
  add("err", filters.error_code);
  add("from", filters.created_from);
  add("to", filters.created_to);
  add("doneFrom", filters.completed_from);
  add("doneTo", filters.completed_to);
  addRange("lat", filters.min_latency_ms, filters.max_latency_ms, "ms");
  addRange("tok", filters.min_total_tokens, filters.max_total_tokens);
  addRange("$", filters.min_estimated_cost, filters.max_estimated_cost);
  if (filters.sort_by !== "created_at" || filters.sort_dir !== "desc") {
    parts.push(`sort=${short(filters.sort_by || "created_at")}.${short(filters.sort_dir || "desc", 6)}`);
  }
  if (filters.limit && filters.limit !== DEFAULT_LIMIT) {
    add("limit", filters.limit);
  }

  return parts.length ? `Active filters: ${parts.join(" · ")}` : "No active filters.";
}

function asSortBy(value: string): "created_at" | "completed_at" | "latency_ms" | "total_tokens" | "estimated_cost" {
  return value === "completed_at" ||
    value === "latency_ms" ||
    value === "total_tokens" ||
    value === "estimated_cost"
    ? value
    : "created_at";
}

function asSortDir(value: string): "asc" | "desc" {
  return value === "asc" ? "asc" : "desc";
}


function filtersFromLocation(): Filters {
  if (typeof window === "undefined") return defaultFilters;
  const params = new URLSearchParams(window.location.search);
  return {
    limit: params.get("limit") ?? DEFAULT_LIMIT,
    request_id: params.get("request_id") ?? "",
    status: params.get("status") ?? "",
    project_id: params.get("project_id") ?? "",
    api_key_id: params.get("api_key_id") ?? "",
    provider: params.get("provider") ?? "",
    requested_model: params.get("requested_model") ?? "",
    model: params.get("model") ?? "",
    model_search: params.get("model_search") ?? "",
    fallback_used: params.get("fallback_used") ?? "",
    error_code: params.get("error_code") ?? "",
    created_from: params.get("created_from") ?? "",
    created_to: params.get("created_to") ?? "",
    completed_from: params.get("completed_from") ?? "",
    completed_to: params.get("completed_to") ?? "",
    min_latency_ms: params.get("min_latency_ms") ?? "",
    max_latency_ms: params.get("max_latency_ms") ?? "",
    min_total_tokens: params.get("min_total_tokens") ?? "",
    max_total_tokens: params.get("max_total_tokens") ?? "",
    min_estimated_cost: params.get("min_estimated_cost") ?? "",
    max_estimated_cost: params.get("max_estimated_cost") ?? "",
    sort_by: params.get("sort_by") ?? "created_at",
    sort_dir: params.get("sort_dir") ?? "desc",
  };
}

function toQuery(filters: Filters, offset: number) {
  const params = new URLSearchParams();
  params.set("limit", filters.limit || DEFAULT_LIMIT);
  params.set("offset", String(offset));
  for (const [key, value] of Object.entries(filters)) {
    if (key !== "limit" && value) params.set(key, value);
  }
  return params;
}

export default function RequestsPage() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [response, setResponse] = useState<RequestListResponse | null>(null);
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [selectedRequestId, setSelectedRequestId] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const limit = Number(filters.limit || DEFAULT_LIMIT);

  async function loadProjects() {
    const result = await listProjects();
    if (result.ok) {
      setProjects(result.data);
    }
  }

  async function loadRequests(nextFilters: Filters, nextOffset: number) {
    setLoading(true);
    setError(null);
    try {
      const result = await listRequests({
        limit: Number(nextFilters.limit || DEFAULT_LIMIT),
        offset: nextOffset,
        request_id: nextFilters.request_id || undefined,
        status: nextFilters.status || undefined,
        project_id: nextFilters.project_id || undefined,
        api_key_id: nextFilters.api_key_id || undefined,
        provider: nextFilters.provider || undefined,
        requested_model: nextFilters.requested_model || undefined,
        model: nextFilters.model || undefined,
        model_search: nextFilters.model_search || undefined,
        fallback_used:
          nextFilters.fallback_used === ""
            ? undefined
            : nextFilters.fallback_used === "true",
        error_code: nextFilters.error_code || undefined,
        created_from: nextFilters.created_from || undefined,
        created_to: nextFilters.created_to || undefined,
        completed_from: nextFilters.completed_from || undefined,
        completed_to: nextFilters.completed_to || undefined,
        min_latency_ms: nextFilters.min_latency_ms ? Number(nextFilters.min_latency_ms) : undefined,
        max_latency_ms: nextFilters.max_latency_ms ? Number(nextFilters.max_latency_ms) : undefined,
        min_total_tokens: nextFilters.min_total_tokens ? Number(nextFilters.min_total_tokens) : undefined,
        max_total_tokens: nextFilters.max_total_tokens ? Number(nextFilters.max_total_tokens) : undefined,
        min_estimated_cost: nextFilters.min_estimated_cost ? Number(nextFilters.min_estimated_cost) : undefined,
        max_estimated_cost: nextFilters.max_estimated_cost ? Number(nextFilters.max_estimated_cost) : undefined,
        sort_by: asSortBy(nextFilters.sort_by),
        sort_dir: asSortDir(nextFilters.sort_dir),
      });
      if (!result.ok) {
        setError(result.error.message);
        return;
      }
      setResponse(result.data as RequestListResponse);
      setOffset(nextOffset);

      const visibleParams = toQuery(nextFilters, nextOffset);
      visibleParams.delete("offset");
      const query = visibleParams.toString();
      window.history.replaceState(null, "", query ? `/requests?${query}` : "/requests");
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(requestId: string) {
    if (!requestId) return;
    setLoadingDetail(true);
    setDetailError(null);
    setSelectedRequestId(requestId);
    try {
      const result = await getRequest(requestId);
      if (!result.ok) {
        setDetail(null);
        setDetailError(result.error.message);
        return;
      }
      setDetail(result.data as RequestDetail);
    } finally {
      setLoadingDetail(false);
    }
  }

  useEffect(() => {
    const initialFilters = filtersFromLocation();
    setFilters(initialFilters);
    setSelectedRequestId(initialFilters.request_id);
    void loadProjects();
    void loadRequests(initialFilters, 0);
    if (initialFilters.request_id) {
      void loadDetail(initialFilters.request_id);
    }
  }, []);

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    const nextFilters = { ...filters };
    setFilters(nextFilters);
    setSelectedRequestId(nextFilters.request_id);
    if (nextFilters.request_id) {
      void loadDetail(nextFilters.request_id);
    } else {
      setDetail(null);
      setDetailError(null);
    }
    void loadRequests(nextFilters, 0);
  }

  function clearFilters() {
    setFilters(defaultFilters);
    setSelectedRequestId("");
    setDetail(null);
    setDetailError(null);
    void loadRequests(defaultFilters, 0);
  }

  function selectRequest(row: RequestRow) {
    const nextFilters = { ...filters, request_id: row.request_id };
    setFilters(nextFilters);
    setSelectedRequestId(row.request_id);
    void loadDetail(row.request_id);
    const params = toQuery(nextFilters, offset);
    params.delete("offset");
    window.history.replaceState(null, "", `/requests?${params.toString()}`);
  }

  function closeDetail() {
    setSelectedRequestId("");
    setDetail(null);
    setDetailError(null);
    // Preserve current filters but clear request_id from URL for shareable state.
    const nextFilters = { ...filters, request_id: "" };
    setFilters(nextFilters);
    const params = toQuery(nextFilters, offset);
    params.delete("offset");
    const q = params.toString();
    window.history.replaceState(null, "", q ? `/requests?${q}` : "/requests");
  }

  const items = response?.items ?? [];
  const canPrev = offset > 0;
  const canNext = response ? offset + limit < response.total : false;
  const rangeLabel = useMemo(() => {
    if (!response) return "—";
    if (response.total === 0) return "0";
    const start = Math.min(response.total, offset + 1);
    const end = Math.min(response.total, offset + items.length);
    return `${start}–${end} of ${response.total}`;
  }, [response, offset, items.length]);
  const summary = useMemo(() => {
    const failed = items.filter((item) => item.status === "failed").length;
    const fallback = items.filter((item) => item.fallback_used).length;
    const cost = items.reduce((sum, item) => sum + (item.estimated_cost ?? 0), 0);
    return { failed, fallback, cost };
  }, [items]);

  return (
    <>
      <PageHeader
        eyebrow="Gateway activity"
        title="Requests"
        description="Inspect real gateway request metadata for operational debugging. Prompt and response body content is not stored or shown here."
        actions={<LinkButton href="/smoke-tests" variant="primary">Test Gateway</LinkButton>}
      />

      {error && <ErrorState message={error} />}

      <div className="grid grid-4">
        <StatCard label="Total visible" value={response?.total ?? "—"} hint="After active filters" />
        <StatCard label="Failed visible" value={summary.failed} hint="Rows on this page" />
        <StatCard label="Fallback visible" value={summary.fallback} hint="Rows on this page" />
        <StatCard label="Estimated cost visible" value={formatCost(summary.cost)} hint="Rows on this page" />
      </div>

      <Card>
        <SectionHeader
          title="Filters"
          description="Filter persisted metadata only. Provider and served model describe the actual route; requested model is what the client sent."
        />
        <form className="stack" onSubmit={applyFilters}>
          <FilterPanel
            summary={<p className="muted">{activeFiltersSummary(filters)}</p>}
            basic={
              <>
                <FormRow>
                  <Field label="Request ID">
                    <Input
                      value={filters.request_id}
                      onChange={(e) => setFilters({ ...filters, request_id: e.target.value })}
                      placeholder="req_..."
                    />
                  </Field>
                  <Field label="Limit">
                    <Select
                      value={filters.limit}
                      onChange={(e) => setFilters({ ...filters, limit: e.target.value })}
                    >
                      <option value="25">25</option>
                      <option value="50">50</option>
                      <option value="100">100</option>
                      <option value="200">200</option>
                    </Select>
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Status">
                    <Select
                      value={filters.status}
                      onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                    >
                      <option value="">Any status</option>
                      <option value="completed">Completed</option>
                      <option value="failed">Failed</option>
                      <option value="started">Started</option>
                    </Select>
                  </Field>
                  <Field label="Project">
                    <Select
                      value={filters.project_id}
                      onChange={(e) => setFilters({ ...filters, project_id: e.target.value })}
                    >
                      <option value="">Any project</option>
                      {projects.map((project) => (
                        <option key={project.id} value={project.id}>
                          {project.name}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Model search">
                    <Input
                      value={filters.model_search}
                      onChange={(e) => setFilters({ ...filters, model_search: e.target.value })}
                      placeholder="Matches client requested or actual model"
                    />
                  </Field>
                  <Field label="Client requested model">
                    <Input
                      value={filters.requested_model}
                      onChange={(e) => setFilters({ ...filters, requested_model: e.target.value })}
                      placeholder="conexus-default"
                    />
                  </Field>
                </FormRow>
              </>
            }
            advanced={
              <>
                <FormRow>
                  <Field label="API key ID">
                    <Input
                      value={filters.api_key_id}
                      onChange={(e) => setFilters({ ...filters, api_key_id: e.target.value })}
                      placeholder="Project API key row ID"
                    />
                  </Field>
                  <Field label="Error code">
                    <Input
                      value={filters.error_code}
                      onChange={(e) => setFilters({ ...filters, error_code: e.target.value })}
                      placeholder="provider_timeout"
                    />
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Actual served provider">
                    <Input
                      value={filters.provider}
                      onChange={(e) => setFilters({ ...filters, provider: e.target.value })}
                      placeholder="openai"
                    />
                  </Field>
                  <Field label="Actual served model">
                    <Input
                      value={filters.model}
                      onChange={(e) => setFilters({ ...filters, model: e.target.value })}
                      placeholder="gpt-4o-mini"
                    />
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Fallback used">
                    <Select
                      value={filters.fallback_used}
                      onChange={(e) => setFilters({ ...filters, fallback_used: e.target.value })}
                    >
                      <option value="">Any</option>
                      <option value="true">Fallback only</option>
                      <option value="false">No fallback</option>
                    </Select>
                  </Field>
                  <Field label="Sort">
                    <div className="split-row">
                      <Select
                        value={filters.sort_by}
                        onChange={(e) => setFilters({ ...filters, sort_by: e.target.value })}
                      >
                        <option value="created_at">Created</option>
                        <option value="completed_at">Completed</option>
                        <option value="latency_ms">Latency</option>
                        <option value="total_tokens">Total tokens</option>
                        <option value="estimated_cost">Estimated cost</option>
                      </Select>
                      <Select
                        value={filters.sort_dir}
                        onChange={(e) => setFilters({ ...filters, sort_dir: e.target.value })}
                      >
                        <option value="desc">Desc</option>
                        <option value="asc">Asc</option>
                      </Select>
                    </div>
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Created from" hint="ISO format, e.g. 2026-04-30T00:00:00Z">
                    <Input
                      type="text"
                      placeholder="2026-04-30T00:00:00Z"
                      value={filters.created_from}
                      onChange={(e) => setFilters({ ...filters, created_from: e.target.value })}
                    />
                  </Field>
                  <Field label="Created to" hint="ISO format, e.g. 2026-04-30T23:59:59Z">
                    <Input
                      type="text"
                      placeholder="2026-04-30T23:59:59Z"
                      value={filters.created_to}
                      onChange={(e) => setFilters({ ...filters, created_to: e.target.value })}
                    />
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Completed from" hint="ISO format, e.g. 2026-04-30T00:00:00Z">
                    <Input
                      type="text"
                      placeholder="2026-04-30T00:00:00Z"
                      value={filters.completed_from}
                      onChange={(e) => setFilters({ ...filters, completed_from: e.target.value })}
                    />
                  </Field>
                  <Field label="Completed to" hint="ISO format, e.g. 2026-04-30T23:59:59Z">
                    <Input
                      type="text"
                      placeholder="2026-04-30T23:59:59Z"
                      value={filters.completed_to}
                      onChange={(e) => setFilters({ ...filters, completed_to: e.target.value })}
                    />
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Min latency ms">
                    <Input
                      type="number"
                      min="0"
                      value={filters.min_latency_ms}
                      onChange={(e) => setFilters({ ...filters, min_latency_ms: e.target.value })}
                    />
                  </Field>
                  <Field label="Max latency ms">
                    <Input
                      type="number"
                      min="0"
                      value={filters.max_latency_ms}
                      onChange={(e) => setFilters({ ...filters, max_latency_ms: e.target.value })}
                    />
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Min total tokens">
                    <Input
                      type="number"
                      min="0"
                      value={filters.min_total_tokens}
                      onChange={(e) => setFilters({ ...filters, min_total_tokens: e.target.value })}
                    />
                  </Field>
                  <Field label="Max total tokens">
                    <Input
                      type="number"
                      min="0"
                      value={filters.max_total_tokens}
                      onChange={(e) => setFilters({ ...filters, max_total_tokens: e.target.value })}
                    />
                  </Field>
                </FormRow>
                <FormRow>
                  <Field label="Min estimated cost">
                    <Input
                      type="number"
                      min="0"
                      step="0.0001"
                      value={filters.min_estimated_cost}
                      onChange={(e) => setFilters({ ...filters, min_estimated_cost: e.target.value })}
                    />
                  </Field>
                  <Field label="Max estimated cost">
                    <Input
                      type="number"
                      min="0"
                      step="0.0001"
                      value={filters.max_estimated_cost}
                      onChange={(e) => setFilters({ ...filters, max_estimated_cost: e.target.value })}
                    />
                  </Field>
                </FormRow>
              </>
            }
            advancedLabel="Advanced filters"
          />
          <div className="inline-actions">
            <Button type="submit">Apply filters</Button>
            <Button type="button" variant="secondary" onClick={clearFilters}>
              Clear filters
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <SectionHeader
          title="Request Table"
          description={`Showing ${rangeLabel}`}
        />
        {loading ? (
          <LoadingState label="Loading requests..." />
        ) : items.length === 0 ? (
          <EmptyState
            title="No requests found"
            action={<LinkButton href="/smoke-tests">Test the gateway</LinkButton>}
          >
            No real gateway request metadata matches the current filters.
          </EmptyState>
        ) : (
          <>
            <Table aria-label="Gateway requests">
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Status</th>
                  <th>Request ID</th>
                  <th>Project</th>
                  <th>Requested model</th>
                  <th>Route</th>
                  <th>Latency</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                  <th>Fallback</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.request_id}
                    className={item.status === "failed" ? "row-warning" : undefined}
                  >
                    <td>{formatDateTime(item.created_at)}</td>
                    <td><StatusBadge status={item.status} /></td>
                    <td>
                      <CompactId value={item.request_id} />
                    </td>
                    <td>{item.project_name ?? item.project_id ?? "—"}</td>
                    <td><code>{item.requested_model}</code></td>
                    <td>
                      <div className="stack-tight">
                        <strong>{empty(item.provider)}</strong>
                        <code>{empty(item.model)}</code>
                      </div>
                    </td>
                    <td>{formatLatency(item.latency_ms)}</td>
                    <td>{formatTokens(item.total_tokens)}</td>
                    <td>{formatCost(item.estimated_cost)}</td>
                    <td>{item.fallback_used ? <Badge tone="warning">Yes</Badge> : "No"}</td>
                    <td className="table-action">
                      <Button type="button" variant="secondary" onClick={() => selectRequest(item)}>
                        {selectedRequestId === item.request_id ? "Viewing" : "View"}
                      </Button>
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
                onClick={() =>
                  void loadRequests(filters, Math.max(0, offset - limit))
                }
              >
                Previous
              </Button>
              <span className="muted">{rangeLabel}</span>
              <Button
                type="button"
                variant="secondary"
                disabled={!canNext || loading}
                onClick={() => void loadRequests(filters, offset + limit)}
              >
                Next
              </Button>
            </div>
          </>
        )}
      </Card>

      <DetailDrawer
        open={Boolean(selectedRequestId) || Boolean(detailError) || loadingDetail}
        onClose={closeDetail}
        title="Request details"
      >
        {loadingDetail ? (
          <LoadingState label="Loading request details..." />
        ) : detailError ? (
          <ErrorState message={detailError} />
        ) : detail ? (
          <div className="stack">
            <KeyValueGrid
              items={[
                {
                  label: "request_id",
                  value: (
                    <span className="inline-actions">
                      <code className="wrap-anywhere">{detail.request_id}</code>
                      <CopyButton value={detail.request_id} />
                    </span>
                  ),
                },
                { label: "project_id", value: detail.project_id ?? "—" },
                { label: "project_name", value: detail.project_name ?? "—" },
                { label: "api_key_prefix", value: detail.api_key_prefix ?? "—" },
                { label: "requested_model", value: detail.requested_model },
                { label: "served_provider", value: detail.provider ?? "—" },
                { label: "served_model", value: detail.model ?? "—" },
                { label: "status", value: <StatusBadge status={detail.status} /> },
                { label: "latency", value: formatLatency(detail.latency_ms) },
                { label: "prompt_tokens", value: empty(detail.prompt_tokens) },
                { label: "completion_tokens", value: empty(detail.completion_tokens) },
                { label: "total_tokens", value: empty(detail.total_tokens) },
                { label: "estimated_cost", value: formatCost(detail.estimated_cost) },
                { label: "fallback_used", value: String(detail.fallback_used) },
                { label: "error_code", value: detail.error_code ?? "—" },
                { label: "error_message", value: detail.error_message ?? "—" },
                { label: "created_at", value: formatDateTime(detail.created_at) },
                { label: "completed_at", value: detail.completed_at ? formatDateTime(detail.completed_at) : "—" },
              ]}
            />
            <JsonBlock value={redactSensitiveObject(detail)} title="Debug JSON" defaultOpen={false} />
          </div>
        ) : null}
      </DetailDrawer>
    </>
  );
}
