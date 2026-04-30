"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  FormRow,
  Input,
  KeyValueGrid,
  LoadingState,
  PageHeader,
  SectionHeader,
  Select,
  Table,
  UnconfiguredServiceState,
} from "@/components/ui";
import { AdaptationErrorBanner } from "@/components/adaptation/AdaptationErrorBanner";
import { formatDateTime } from "@/lib/format";
import {
  adaptationApi,
  isAdaptationServiceUnconfigured,
  type AdaptationPlanListItem,
  type AdaptationResult,
} from "@/lib/adaptationApi";

type Filters = {
  domainKey: string;
  status: string;
  strategy: string;
  requiresHumanApproval: string;
};

const defaultFilters: Filters = {
  domainKey: "",
  status: "",
  strategy: "",
  requiresHumanApproval: "",
};

function parseFiltersFromLocation(): Filters {
  if (typeof window === "undefined") return defaultFilters;
  const params = new URLSearchParams(window.location.search);
  return {
    domainKey: params.get("domainKey") ?? "",
    status: params.get("status") ?? "",
    strategy: params.get("strategy") ?? "",
    requiresHumanApproval: params.get("requiresHumanApproval") ?? "",
  };
}

function buildParams(filters: Filters) {
  const params = new URLSearchParams();
  if (filters.domainKey) params.set("domainKey", filters.domainKey);
  if (filters.status) params.set("status", filters.status);
  if (filters.strategy) params.set("strategy", filters.strategy);
  if (filters.requiresHumanApproval) params.set("requiresHumanApproval", filters.requiresHumanApproval);
  return params;
}

function planIdOf(plan: AdaptationPlanListItem) {
  return plan.id ?? plan.planId ?? "";
}

function planStatusOf(plan: AdaptationPlanListItem) {
  return plan.status ?? "—";
}

function createdAtOf(plan: AdaptationPlanListItem) {
  return plan.createdAt ?? null;
}

function requiresHumanApprovalOf(plan: AdaptationPlanListItem) {
  return plan.requiresHumanApproval ?? false;
}

export default function AdaptationPlansPage() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [items, setItems] = useState<AdaptationPlanListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionBusyId, setActionBusyId] = useState<string | null>(null);
  const [lastError, setLastError] = useState<AdaptationResult<unknown> | null>(null);
  const unconfigured = lastError ? isAdaptationServiceUnconfigured(lastError) : false;

  async function load(next: Filters) {
    setLoading(true);
    setLastError(null);
    const params = buildParams(next);
    const res = await adaptationApi.listPlans(params);
    if (!res.ok) {
      setItems([]);
      setLastError(res);
    } else {
      setItems(res.data);
      const query = params.toString();
      window.history.replaceState(null, "", query ? `/adaptation/plans?${query}` : "/adaptation/plans");
    }
    setLoading(false);
  }

  useEffect(() => {
    const initial = parseFiltersFromLocation();
    setFilters(initial);
    void load(initial);
  }, []);

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    void load(filters);
  }

  function clearFilters() {
    setFilters(defaultFilters);
    void load(defaultFilters);
  }

  async function approve(planId: string) {
    setActionBusyId(planId);
    setLastError(null);
    const res = await adaptationApi.approvePlan(planId);
    if (!res.ok) setLastError(res);
    await load(filters);
    setActionBusyId(null);
  }

  async function startRun(planId: string) {
    setActionBusyId(planId);
    setLastError(null);
    const res = await adaptationApi.startRun(planId);
    if (!res.ok) {
      setLastError(res);
      setActionBusyId(null);
      return;
    }
    const runId = res.data.runId;
    if (typeof runId === "string" && runId) {
      window.location.href = `/adaptation/runs/${encodeURIComponent(runId)}`;
      return;
    }
    await load(filters);
    setActionBusyId(null);
  }

  const summary = useMemo(() => {
    const drafts = items.filter((p) => planStatusOf(p).toLowerCase() === "draft").length;
    const requires = items.filter((p) => requiresHumanApprovalOf(p)).length;
    return { drafts, requires };
  }, [items]);

  return (
    <>
      <PageHeader
        eyebrow="Adaptation"
        title="Plans"
        description="Browse adaptation plans, approve drafts, and start runs. This console is read-only except for approve/run actions."
      />

      {unconfigured ? (
        <UnconfiguredServiceState
          serviceName="Adaptation service"
          envVarName="ADAPTATION_API_BASE_URL"
          expectedLocalValue="http://localhost:5088"
          onRetry={() => void load(filters)}
        />
      ) : (
        <>
          {lastError && <AdaptationErrorBanner result={lastError} />}

          <div className="grid grid-3">
            <Card className="card-muted">
              <SectionHeader title="Visible plans" />
              <KeyValueGrid items={[{ label: "count", value: items.length.toLocaleString() }]} />
            </Card>
            <Card className="card-muted">
              <SectionHeader title="Draft plans" />
              <KeyValueGrid items={[{ label: "draft", value: summary.drafts.toLocaleString() }]} />
            </Card>
            <Card className="card-muted">
              <SectionHeader title="Requires approval" />
              <KeyValueGrid items={[{ label: "requiresHumanApproval", value: summary.requires.toLocaleString() }]} />
            </Card>
          </div>

          <Card>
            <SectionHeader title="Filters" description="Filters are passed through to the adaptation service." />
            <form className="stack" onSubmit={applyFilters}>
              <FormRow>
                <Field label="Domain key">
                  <Input
                    value={filters.domainKey}
                    onChange={(e) => setFilters({ ...filters, domainKey: e.target.value })}
                    placeholder="finance-support"
                  />
                </Field>
                <Field label="Status">
                  <Input
                    value={filters.status}
                    onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                    placeholder="Draft / Approved / ..."
                  />
                </Field>
              </FormRow>
              <FormRow>
                <Field label="Strategy">
                  <Input
                    value={filters.strategy}
                    onChange={(e) => setFilters({ ...filters, strategy: e.target.value })}
                    placeholder="fewshot-rag"
                  />
                </Field>
                <Field label="Requires human approval">
                  <Select
                    value={filters.requiresHumanApproval}
                    onChange={(e) => setFilters({ ...filters, requiresHumanApproval: e.target.value })}
                  >
                    <option value="">Any</option>
                    <option value="true">True</option>
                    <option value="false">False</option>
                  </Select>
                </Field>
              </FormRow>
              <div className="inline-actions">
                <Button type="submit">Apply filters</Button>
                <Button type="button" variant="secondary" onClick={clearFilters}>
                  Clear
                </Button>
              </div>
            </form>
          </Card>

          <Card>
            <SectionHeader title="Plan Table" description={`Showing ${items.length} plans.`} />
            {loading ? (
              <LoadingState label="Loading plans..." />
            ) : items.length === 0 ? (
              <EmptyState title="No plans found">No adaptation plans match the current filters.</EmptyState>
            ) : (
              <Table aria-label="Adaptation plans">
                <thead>
                  <tr>
                    <th>Created</th>
                    <th>Domain key</th>
                    <th>Task</th>
                    <th>Strategy</th>
                    <th>Recipe</th>
                    <th>Status</th>
                    <th>Requires approval</th>
                    <th>Created by</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((plan) => {
                    const id = planIdOf(plan);
                    const statusValue = planStatusOf(plan);
                    const busy = actionBusyId === id;
                    const createdBy = plan.createdByUserId ?? "—";
                    const task = plan.taskDescription ?? "—";
                    const domainKey = plan.domainKey ?? "—";
                    const strategy = plan.recommendedStrategy ?? "—";
                    const recipe = plan.recipeKey ?? "—";
                    const requiresApproval = requiresHumanApprovalOf(plan);
                    return (
                      <tr key={id || JSON.stringify(plan)}>
                        <td>{formatDateTime(createdAtOf(plan))}</td>
                        <td>
                          <code className="wrap-anywhere">{domainKey}</code>
                        </td>
                        <td className="truncate">{task}</td>
                        <td>{strategy}</td>
                        <td>
                          <code className="wrap-anywhere">{recipe}</code>
                        </td>
                        <td>
                          <Badge tone={statusValue.toLowerCase() === "draft" ? "warning" : "neutral"}>
                            {statusValue}
                          </Badge>
                        </td>
                        <td>{requiresApproval ? <Badge tone="warning">required</Badge> : "—"}</td>
                        <td>
                          <code className="wrap-anywhere">{createdBy}</code>
                        </td>
                        <td>
                          <div className="inline-actions">
                            <Link className="button button-secondary" href={`/adaptation/plans/${encodeURIComponent(id)}`}>
                              View
                            </Link>
                            <Button
                              type="button"
                              variant="secondary"
                              disabled={busy || statusValue.toLowerCase() !== "draft" || !id}
                              onClick={() => void approve(id)}
                            >
                              Approve
                            </Button>
                            <Button
                              type="button"
                              variant="primary"
                              disabled={busy || statusValue.toLowerCase() !== "approved" || !id}
                              onClick={() => void startRun(id)}
                            >
                              Start run
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            )}
          </Card>
        </>
      )}
    </>
  );
}
