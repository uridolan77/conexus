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
  Select,
  Table,
} from "@/components/ui";
import { formatDate } from "@/lib/api";
import { adaptationApi, formatAdaptationError } from "@/lib/adaptationApi";

type Filters = {
  domainKey: string;
  status: string;
  approvedForRuntime: string;
  planId: string;
  runId: string;
};

const defaultFilters: Filters = {
  domainKey: "",
  status: "",
  approvedForRuntime: "",
  planId: "",
  runId: "",
};

function parseFiltersFromLocation(): Filters {
  if (typeof window === "undefined") return defaultFilters;
  const params = new URLSearchParams(window.location.search);
  return {
    domainKey: params.get("domainKey") ?? "",
    status: params.get("status") ?? "",
    approvedForRuntime: params.get("approvedForRuntime") ?? "",
    planId: params.get("planId") ?? "",
    runId: params.get("runId") ?? "",
  };
}

function buildParams(filters: Filters) {
  const params = new URLSearchParams();
  if (filters.domainKey) params.set("domainKey", filters.domainKey);
  if (filters.status) params.set("status", filters.status);
  if (filters.approvedForRuntime) params.set("approvedForRuntime", filters.approvedForRuntime);
  if (filters.planId) params.set("planId", filters.planId);
  if (filters.runId) params.set("runId", filters.runId);
  return params;
}

function asArray(value: unknown): any[] {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object" && "items" in value && Array.isArray((value as any).items)) {
    return (value as any).items as any[];
  }
  return [];
}

export default function AdapterProfilesPage() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(next: Filters) {
    setLoading(true);
    setError(null);
    const params = buildParams(next);
    const res = await adaptationApi.listProfiles(params);
    if (!res.ok) {
      setItems([]);
      setError(formatAdaptationError(res));
    } else {
      setItems(asArray(res.data));
      const query = params.toString();
      window.history.replaceState(null, "", query ? `/adaptation/profiles?${query}` : "/adaptation/profiles");
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
        title="Profiles"
        description="Review adapter profiles produced by adaptation runs, including composite score and gate outcomes."
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
                placeholder="Approved / Rejected / ..."
              />
            </Field>
          </FormRow>
          <FormRow>
            <Field label="Approved for runtime">
              <Select
                value={filters.approvedForRuntime}
                onChange={(e) => setFilters({ ...filters, approvedForRuntime: e.target.value })}
              >
                <option value="">Any</option>
                <option value="true">True</option>
                <option value="false">False</option>
              </Select>
            </Field>
            <Field label="Plan ID">
              <Input
                value={filters.planId}
                onChange={(e) => setFilters({ ...filters, planId: e.target.value })}
                placeholder="plan_..."
              />
            </Field>
          </FormRow>
          <FormRow>
            <Field label="Run ID">
              <Input
                value={filters.runId}
                onChange={(e) => setFilters({ ...filters, runId: e.target.value })}
                placeholder="run_..."
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
        <SectionHeader title="Profile Table" description={`Showing ${items.length} profiles.`} />
        {loading ? (
          <LoadingState label="Loading profiles..." />
        ) : items.length === 0 ? (
          <EmptyState title="No profiles found">No adapter profiles match the current filters.</EmptyState>
        ) : (
          <Table aria-label="Adapter profiles">
            <thead>
              <tr>
                <th>Created</th>
                <th>Domain key</th>
                <th>Status</th>
                <th>Approved for runtime</th>
                <th>Composite score</th>
                <th>Model</th>
                <th>Prompt</th>
                <th>Retrieval</th>
                <th>Safety</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((profile) => {
                const id = profile?.profileId ?? profile?.id ?? profile?.profile_id;
                const domainKey = profile?.domainKey ?? profile?.domain_key ?? "—";
                const statusValue = profile?.status ?? "—";
                const statusLower = typeof statusValue === "string" ? statusValue.toLowerCase() : "";
                const approved = profile?.approvedForRuntime ?? profile?.approved_for_runtime ?? false;
                const composite = profile?.compositeScore ?? profile?.composite_score ?? "—";
                const tone = approved ? "success" : statusLower === "rejected" ? "danger" : "neutral";
                return (
                  <tr key={id ?? JSON.stringify(profile)}>
                    <td>{formatDate(profile?.createdAt ?? profile?.created_at)}</td>
                    <td><code className="wrap-anywhere">{domainKey}</code></td>
                    <td><Badge tone={statusLower === "rejected" ? "danger" : "neutral"}>{statusValue}</Badge></td>
                    <td>{approved ? <Badge tone="success">true</Badge> : "—"}</td>
                    <td>{typeof composite === "number" ? composite.toFixed(4) : composite}</td>
                    <td><code className="wrap-anywhere">{profile?.modelProfile ?? profile?.model_profile ?? "—"}</code></td>
                    <td><code className="wrap-anywhere">{profile?.promptProfile ?? profile?.prompt_profile ?? "—"}</code></td>
                    <td><code className="wrap-anywhere">{profile?.retrievalProfile ?? profile?.retrieval_profile ?? "—"}</code></td>
                    <td><code className="wrap-anywhere">{profile?.safetyProfile ?? profile?.safety_profile ?? "—"}</code></td>
                    <td>
                      {typeof id === "string" && id ? (
                        <div className="inline-actions">
                          <Link className="button button-secondary" href={`/adaptation/profiles/${encodeURIComponent(id)}`}>
                            View
                          </Link>
                          {profile?.runId && (
                            <Link className="button button-ghost" href={`/adaptation/runs/${encodeURIComponent(profile.runId)}`}>
                              Run
                            </Link>
                          )}
                          {profile?.planId && (
                            <Link className="button button-ghost" href={`/adaptation/plans/${encodeURIComponent(profile.planId)}`}>
                              Plan
                            </Link>
                          )}
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

