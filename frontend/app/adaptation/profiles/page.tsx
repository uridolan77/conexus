"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  FormRow,
  Input,
  LoadingState,
  PageHeader,
  SectionHeader,
  Select,
  Table,
  UnconfiguredServiceState,
} from "@/components/ui";
import { AdaptationErrorBanner } from "@/components/adaptation/AdaptationErrorBanner";
import { ScoreBadge } from "@/components/adaptation/ScoreBadge";
import { formatDate } from "@/lib/api";
import { adaptationApi, isAdaptationServiceUnconfigured, type AdapterProfileListItem, type AdaptationResult } from "@/lib/adaptationApi";

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

const FILTER_KEYS = ["domainKey", "status", "approvedForRuntime", "planId", "runId"] as const satisfies readonly (
  keyof Filters
)[];

function blockingFailedGate(profile: AdapterProfileListItem): boolean {
  const gates = profile.gateResults;
  if (!gates?.length) return false;
  return gates.some((g) => g.blocking === true && g.passed === false);
}

export default function AdapterProfilesPage() {
  const { parseFromSearch, toQuery, replaceUrl } = useUrlFilters<Filters>({
    pathname: "/adaptation/profiles",
    defaults: defaultFilters,
    keys: FILTER_KEYS,
  });
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [items, setItems] = useState<AdapterProfileListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastError, setLastError] = useState<AdaptationResult<unknown> | null>(null);
  const unconfigured = lastError ? isAdaptationServiceUnconfigured(lastError) : false;

  async function load(next: Filters) {
    setLoading(true);
    setLastError(null);
    const params = new URLSearchParams(toQuery(next));
    const res = await adaptationApi.listProfiles(params);
    if (!res.ok) {
      setItems([]);
      setLastError(res);
    } else {
      setItems(res.data);
      replaceUrl(next);
    }
    setLoading(false);
  }

  useEffect(() => {
    const initial = typeof window === "undefined" ? defaultFilters : parseFromSearch(window.location.search);
    setFilters(initial);
    void load(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

      {unconfigured ? (
        <UnconfiguredServiceState
          serviceName="Adaptation service"
          envVarName="ADAPTATION_API_BASE_URL"
          expectedLocalValue="http://localhost:5000"
          onRetry={() => void load(filters)}
        />
      ) : (
        <>
          {lastError && <AdaptationErrorBanner result={lastError} />}

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
                    <th>Gateway profile</th>
                    <th>Canary %</th>
                    <th>Published</th>
                    <th>Activated</th>
                    <th>Model</th>
                    <th>Prompt</th>
                    <th>Retrieval</th>
                    <th>Safety</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((profile) => {
                    const id = profile.profileId ?? profile.id ?? "";
                    const domainKey = profile.domainKey ?? "—";
                    const statusValue = profile.status ?? "—";
                    const statusLower = typeof statusValue === "string" ? statusValue.toLowerCase() : "";
                    const approved = profile.approvedForRuntime ?? false;
                    const composite = profile.compositeScore;
                    const gateIssue = blockingFailedGate(profile);
                    return (
                      <tr key={id || JSON.stringify(profile)} className={gateIssue ? "row-warning" : undefined}>
                        <td>{formatDate(profile.createdAt)}</td>
                        <td>
                          <code className="wrap-anywhere">{domainKey}</code>
                        </td>
                        <td>
                          <Badge tone={statusLower === "rejected" ? "danger" : "neutral"}>{statusValue}</Badge>
                        </td>
                        <td>{approved ? <Badge tone="success">true</Badge> : "—"}</td>
                        <td>
                          <ScoreBadge score={composite ?? null} />
                        </td>
                        <td>
                          <code className="wrap-anywhere">{profile.gatewayProfileId ?? "—"}</code>
                        </td>
                        <td>{profile.canaryPercent != null ? String(profile.canaryPercent) : "—"}</td>
                        <td>{formatDate(profile.publishedAt ?? undefined)}</td>
                        <td>{formatDate(profile.activatedAt ?? undefined)}</td>
                        <td>
                          <code className="wrap-anywhere">{profile.modelProfile ?? "—"}</code>
                        </td>
                        <td>
                          <code className="wrap-anywhere">{profile.promptProfile ?? "—"}</code>
                        </td>
                        <td>
                          <code className="wrap-anywhere">{profile.retrievalProfile ?? "—"}</code>
                        </td>
                        <td>
                          <code className="wrap-anywhere">{profile.safetyProfile ?? "—"}</code>
                        </td>
                        <td>
                          {id ? (
                            <div className="inline-actions">
                              <Link className="button button-secondary" href={`/adaptation/profiles/${encodeURIComponent(id)}`}>
                                View
                              </Link>
                              {profile.runId && (
                                <Link className="button button-ghost" href={`/adaptation/runs/${encodeURIComponent(profile.runId)}`}>
                                  Run
                                </Link>
                              )}
                              {profile.planId && (
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
      )}
    </>
  );
}
