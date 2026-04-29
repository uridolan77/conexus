"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  CopyButton,
  EmptyState,
  ErrorState,
  Field,
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
  Table,
} from "@/components/ui";
import { BACKEND_BASE, formatApiError, formatDate, readJsonSafe } from "@/lib/api";
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

function formatMs(value: number | null) {
  return value === null ? "—" : `${value.toLocaleString()} ms`;
}

function formatTokens(value: number | null) {
  return value === null ? "—" : value.toLocaleString();
}

function formatCost(value: number | null) {
  if (value === null) return "—";
  if (value === 0) return "$0";
  if (value < 0.0001) return "<$0.0001";
  return `$${value.toFixed(4)}`;
}

function formatOptionalDate(value: string | null | undefined) {
  return value ? formatDate(value) : "—";
}

function badgeTone(status: string): "neutral" | "success" | "danger" | "info" {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "started") return "info";
  return "neutral";
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

  async function loadProjects() {
    const res = await fetch(`${BACKEND_BASE}/admin/projects`, {
      credentials: "include",
      cache: "no-store",
    });
    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (res.ok) {
      setProjects((await res.json()) as ProjectRow[]);
    }
  }

  async function loadRequests(nextFilters: Filters, nextOffset: number) {
    setLoading(true);
    setError(null);
    try {
      const params = toQuery(nextFilters, nextOffset);
      const res = await fetch(`${BACKEND_BASE}/admin/requests?${params.toString()}`, {
        credentials: "include",
        cache: "no-store",
      });
      const body = await readJsonSafe(res);
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        setError(formatApiError(body));
        return;
      }
      setResponse(body as RequestListResponse);
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
      const res = await fetch(`${BACKEND_BASE}/admin/requests/${encodeURIComponent(requestId)}`, {
        credentials: "include",
        cache: "no-store",
      });
      const body = await readJsonSafe(res);
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        setDetail(null);
        setDetailError(formatApiError(body));
        return;
      }
      setDetail(body as RequestDetail);
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

  const items = response?.items ?? [];
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
        actions={<LinkButton href="/smoke-tests" variant="primary">Run Smoke Test</LinkButton>}
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
            <Field label="Model search">
              <Input
                value={filters.model_search}
                onChange={(e) => setFilters({ ...filters, model_search: e.target.value })}
                placeholder="Matches client requested or actual model"
              />
            </Field>
          </FormRow>
          <FormRow>
            <Field label="Client requested model">
              <Input
                value={filters.requested_model}
                onChange={(e) => setFilters({ ...filters, requested_model: e.target.value })}
                placeholder="conexus-default"
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
            <Field label="Created from">
              <Input
                type="datetime-local"
                value={filters.created_from}
                onChange={(e) => setFilters({ ...filters, created_from: e.target.value })}
              />
            </Field>
            <Field label="Created to">
              <Input
                type="datetime-local"
                value={filters.created_to}
                onChange={(e) => setFilters({ ...filters, created_to: e.target.value })}
              />
            </Field>
          </FormRow>
          <FormRow>
            <Field label="Completed from">
              <Input
                type="datetime-local"
                value={filters.completed_from}
                onChange={(e) => setFilters({ ...filters, completed_from: e.target.value })}
              />
            </Field>
            <Field label="Completed to">
              <Input
                type="datetime-local"
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
          description={`Showing ${items.length} of ${response?.total ?? 0} matching requests.`}
        />
        {loading ? (
          <LoadingState label="Loading requests..." />
        ) : items.length === 0 ? (
          <EmptyState
            title="No requests found"
            action={<LinkButton href="/smoke-tests">Run a gateway smoke test</LinkButton>}
          >
            No real gateway request metadata matches the current filters.
          </EmptyState>
        ) : (
          <>
            <Table aria-label="Gateway requests">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Project</th>
                  <th>API key</th>
                  <th>Status</th>
                  <th>Client requested model</th>
                  <th>Actual served provider/model</th>
                  <th>Latency</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                  <th>Fallback</th>
                  <th>Created</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.request_id}
                    className={item.status === "failed" ? "row-warning" : undefined}
                  >
                    <td>
                      <div className="stack-tight">
                        <code className="wrap-anywhere">{item.request_id}</code>
                        <CopyButton value={item.request_id} />
                      </div>
                    </td>
                    <td>{item.project_name ?? item.project_id ?? "—"}</td>
                    <td>
                      <div className="stack-tight">
                        <code>{item.api_key_prefix ?? "—"}</code>
                        <span className="muted wrap-anywhere">{item.api_key_id ?? ""}</span>
                      </div>
                    </td>
                    <td><Badge tone={badgeTone(item.status)}>{item.status}</Badge></td>
                    <td>{item.requested_model}</td>
                    <td>
                      <span>{empty(item.provider)}</span>
                      <br />
                      <code>{empty(item.model)}</code>
                    </td>
                    <td>{formatMs(item.latency_ms)}</td>
                    <td>{formatTokens(item.total_tokens)}</td>
                    <td>{formatCost(item.estimated_cost)}</td>
                    <td>{item.fallback_used ? <Badge tone="warning">fallback</Badge> : "—"}</td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>
                      <Button type="button" variant="secondary" onClick={() => selectRequest(item)}>
                        {selectedRequestId === item.request_id ? "Viewing" : "View details"}
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
                disabled={offset === 0}
                onClick={() =>
                  void loadRequests(filters, Math.max(0, offset - Number(filters.limit || DEFAULT_LIMIT)))
                }
              >
                Previous
              </Button>
              <span className="muted">
                Offset {offset}
              </span>
              <Button
                type="button"
                variant="secondary"
                disabled={!response || offset + Number(filters.limit || DEFAULT_LIMIT) >= response.total}
                onClick={() => void loadRequests(filters, offset + Number(filters.limit || DEFAULT_LIMIT))}
              >
                Next
              </Button>
            </div>
          </>
        )}
      </Card>

      {(selectedRequestId || detailError || loadingDetail) && (
        <Card>
          <SectionHeader
            title="Request Details"
            description="Structured metadata for the selected gateway request."
          />
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
                  { label: "project", value: detail.project_name ?? detail.project_id ?? "—" },
                  { label: "api_key_prefix", value: detail.api_key_prefix ?? "—" },
                  { label: "status", value: <Badge tone={badgeTone(detail.status)}>{detail.status}</Badge> },
                  { label: "status_group", value: detail.normalized_status_group },
                  { label: "created_at", value: formatDate(detail.created_at) },
                  { label: "completed_at", value: formatOptionalDate(detail.completed_at) },
                  { label: "latency_ms", value: empty(detail.latency_ms) },
                  { label: "request_age_seconds", value: empty(detail.request_age_seconds) },
                  { label: "completed_age_seconds", value: empty(detail.completed_age_seconds) },
                ]}
              />
              <div className="grid grid-3">
                <Card className="card-muted">
                  <SectionHeader title="Routing Summary" />
                  <KeyValueGrid
                    items={[
                      { label: "client requested model", value: detail.routing_summary.requested_model },
                      { label: "actual served provider", value: detail.routing_summary.served_provider ?? "—" },
                      { label: "actual served model", value: detail.routing_summary.served_model ?? "—" },
                      { label: "fallback_used", value: String(detail.routing_summary.fallback_used) },
                    ]}
                  />
                </Card>
                <Card className="card-muted">
                  <SectionHeader title="Token Summary" />
                  <KeyValueGrid
                    items={[
                      { label: "prompt_tokens", value: empty(detail.token_summary.prompt_tokens) },
                      { label: "completion_tokens", value: empty(detail.token_summary.completion_tokens) },
                      { label: "total_tokens", value: empty(detail.token_summary.total_tokens) },
                    ]}
                  />
                </Card>
                <Card className="card-muted">
                  <SectionHeader title="Cost Summary" />
                  <KeyValueGrid
                    items={[
                      { label: "estimated_cost", value: formatCost(detail.cost_summary.estimated_cost) },
                      { label: "currency", value: detail.cost_summary.currency },
                    ]}
                  />
                </Card>
              </div>
              {detail.normalized_status_group === "failure" && (
                <Card className="card-muted">
                  <SectionHeader title="Error Summary" />
                  <KeyValueGrid
                    items={[
                      { label: "code", value: detail.error_summary.code ?? "—" },
                      { label: "message", value: detail.error_summary.message ?? "—" },
                    ]}
                  />
                </Card>
              )}
              <JsonBlock value={detail} title="Raw Metadata JSON" />
            </div>
          ) : null}
        </Card>
      )}
    </>
  );
}
