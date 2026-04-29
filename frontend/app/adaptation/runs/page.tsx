"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  FormRow,
  Input,
  LoadingState,
  PageHeader,
  SectionHeader,
  Table,
} from "@/components/ui";
import { formatDate } from "@/lib/api";
import { adaptationApi, formatAdaptationError } from "@/lib/adaptationApi";

type Filters = {
  domainKey: string;
  status: string;
  planId: string;
  recipeKey: string;
};

const defaultFilters: Filters = { domainKey: "", status: "", planId: "", recipeKey: "" };

function parseFiltersFromLocation(): Filters {
  if (typeof window === "undefined") return defaultFilters;
  const params = new URLSearchParams(window.location.search);
  return {
    domainKey: params.get("domainKey") ?? "",
    status: params.get("status") ?? "",
    planId: params.get("planId") ?? "",
    recipeKey: params.get("recipeKey") ?? "",
  };
}

function buildParams(filters: Filters) {
  const params = new URLSearchParams();
  if (filters.domainKey) params.set("domainKey", filters.domainKey);
  if (filters.status) params.set("status", filters.status);
  if (filters.planId) params.set("planId", filters.planId);
  if (filters.recipeKey) params.set("recipeKey", filters.recipeKey);
  return params;
}

function asArray(value: unknown): any[] {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object" && "items" in value && Array.isArray((value as any).items)) {
    return (value as any).items as any[];
  }
  return [];
}

export default function AdaptationRunsPage() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(next: Filters) {
    setLoading(true);
    setError(null);
    const params = buildParams(next);
    const res = await adaptationApi.listRuns(params);
    if (!res.ok) {
      setItems([]);
      setError(formatAdaptationError(res));
    } else {
      setItems(asArray(res.data));
      const query = params.toString();
      window.history.replaceState(null, "", query ? `/adaptation/runs?${query}` : "/adaptation/runs");
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

  return (
    <>
      <PageHeader
        eyebrow="Adaptation"
        title="Runs"
        description="Inspect adaptation runs, manifests, and produced adapter profiles."
      />

      {error && <ErrorState message={error} />}

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
                placeholder="Running / Completed / Failed / ..."
              />
            </Field>
          </FormRow>
          <FormRow>
            <Field label="Plan ID">
              <Input
                value={filters.planId}
                onChange={(e) => setFilters({ ...filters, planId: e.target.value })}
                placeholder="plan_..."
              />
            </Field>
            <Field label="Recipe key">
              <Input
                value={filters.recipeKey}
                onChange={(e) => setFilters({ ...filters, recipeKey: e.target.value })}
                placeholder="recipe_..."
              />
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
        <SectionHeader title="Run Table" description={`Showing ${items.length} runs.`} />
        {loading ? (
          <LoadingState label="Loading runs..." />
        ) : items.length === 0 ? (
          <EmptyState title="No runs found">No adaptation runs match the current filters.</EmptyState>
        ) : (
          <Table aria-label="Adaptation runs">
            <thead>
              <tr>
                <th>Created</th>
                <th>Domain key</th>
                <th>Plan</th>
                <th>Recipe</th>
                <th>Status</th>
                <th>Step count</th>
                <th>Started</th>
                <th>Completed</th>
                <th>Failed</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((run) => {
                const id = run?.runId ?? run?.id ?? run?.run_id;
                const statusValue = run?.status ?? "—";
                const lower = typeof statusValue === "string" ? statusValue.toLowerCase() : "";
                const tone =
                  lower === "failed" ? "danger" : lower === "completed" ? "success" : lower === "running" ? "info" : "neutral";
                const planId = run?.planId ?? run?.plan_id ?? "—";
                const recipeKey = run?.recipeKey ?? run?.recipe_key ?? "—";
                const domainKey = run?.domainKey ?? run?.domain_key ?? "—";
                const stepCount = run?.stepCount ?? run?.step_count ?? "—";
                return (
                  <tr key={id ?? JSON.stringify(run)} className={lower === "failed" ? "row-warning" : undefined}>
                    <td>{formatDate(run?.createdAt ?? run?.created_at)}</td>
                    <td><code className="wrap-anywhere">{domainKey}</code></td>
                    <td><code className="wrap-anywhere">{planId}</code></td>
                    <td><code className="wrap-anywhere">{recipeKey}</code></td>
                    <td><Badge tone={tone as any}>{statusValue}</Badge></td>
                    <td>{typeof stepCount === "number" ? stepCount.toLocaleString() : stepCount}</td>
                    <td>{formatDate(run?.startedAt ?? run?.started_at)}</td>
                    <td>{formatDate(run?.completedAt ?? run?.completed_at)}</td>
                    <td>{formatDate(run?.failedAt ?? run?.failed_at)}</td>
                    <td>
                      {typeof id === "string" && id ? (
                        <div className="inline-actions">
                          <Link className="button button-secondary" href={`/adaptation/runs/${encodeURIComponent(id)}`}>
                            View
                          </Link>
                          <Link className="button button-ghost" href={`/adaptation/runs/${encodeURIComponent(id)}#manifest`}>
                            Manifest
                          </Link>
                        </div>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card>
    </>
  );
}

