"use client";

import { useEffect, useState } from "react";
import {
  Card,
  EmptyState,
  ErrorState,
  Field,
  FormRow,
  LoadingState,
  PageHeader,
  SectionHeader,
  Select,
  StatCard,
  Table,
} from "@/components/ui";
import { BACKEND_BASE, formatApiError, formatDate, readJsonSafe } from "@/lib/api";
import type {
  UsageBreakdownResponse,
  UsageProjectRow,
  UsageProviderRow,
  UsageSummary,
} from "@/lib/types";

type UsageWindow = "24h" | "7d" | "30d";

function formatCost(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  if (value === 0) return "$0";
  if (value < 0.0001) return "<$0.0001";
  return `$${value.toFixed(4)}`;
}

function formatRate(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function formatNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : value.toLocaleString();
}

function formatMs(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value).toLocaleString()} ms`;
}

export default function UsagePage() {
  const [windowValue, setWindowValue] = useState<UsageWindow>("30d");
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [byProject, setByProject] = useState<UsageProjectRow[]>([]);
  const [byProvider, setByProvider] = useState<UsageProviderRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUsage() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ window: windowValue });
        const [summaryRes, projectRes, providerRes] = await Promise.all([
          fetch(`${BACKEND_BASE}/admin/usage/summary?${params.toString()}`, {
            credentials: "include",
            cache: "no-store",
          }),
          fetch(`${BACKEND_BASE}/admin/usage/by-project?${params.toString()}`, {
            credentials: "include",
            cache: "no-store",
          }),
          fetch(`${BACKEND_BASE}/admin/usage/by-provider?${params.toString()}`, {
            credentials: "include",
            cache: "no-store",
          }),
        ]);

        if (
          summaryRes.status === 401 ||
          projectRes.status === 401 ||
          providerRes.status === 401
        ) {
          window.location.href = "/login";
          return;
        }

        const [summaryBody, projectBody, providerBody] = await Promise.all([
          readJsonSafe(summaryRes),
          readJsonSafe(projectRes),
          readJsonSafe(providerRes),
        ]);

        if (!summaryRes.ok) {
          setError(formatApiError(summaryBody));
          return;
        }
        if (!projectRes.ok) {
          setError(formatApiError(projectBody));
          return;
        }
        if (!providerRes.ok) {
          setError(formatApiError(providerBody));
          return;
        }

        setSummary(summaryBody as UsageSummary);
        setByProject(
          (projectBody as UsageBreakdownResponse<UsageProjectRow>).items,
        );
        setByProvider(
          (providerBody as UsageBreakdownResponse<UsageProviderRow>).items,
        );
      } catch {
        setError("Unable to load usage analytics. Check that the backend is reachable.");
      } finally {
        setLoading(false);
      }
    }

    void loadUsage();
  }, [windowValue]);

  return (
    <>
      <PageHeader
        eyebrow="Usage analytics"
        title="Usage"
        description="Review real gateway request metadata by project and provider. Prompt and response body content is not stored or shown here."
      />

      {error && <ErrorState message={error} />}

      <Card>
        <SectionHeader
          title="Window"
          description="All usage metrics are computed from persisted gateway request rows."
        />
        <FormRow>
          <Field label="Time window">
            <Select
              value={windowValue}
              onChange={(event) => setWindowValue(event.target.value as UsageWindow)}
            >
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
            </Select>
          </Field>
        </FormRow>
      </Card>

      {loading ? (
        <Card>
          <LoadingState label="Loading usage analytics..." />
        </Card>
      ) : summary ? (
        <>
          <div className="grid grid-4">
            <StatCard
              label="Requests"
              value={summary.total_requests.toLocaleString()}
              hint={`${summary.completed_requests} completed`}
            />
            <StatCard
              label="Estimated Cost"
              value={formatCost(summary.estimated_cost)}
              hint={summary.currency}
            />
            <StatCard
              label="Success Rate"
              value={formatRate(summary.success_rate)}
              hint={`${summary.failed_requests} failed`}
            />
            <StatCard
              label="Fallback Rate"
              value={formatRate(summary.fallback_rate)}
              hint={`${summary.fallback_count} fallbacks`}
            />
          </div>

          <Card>
            <SectionHeader
              title="Summary"
              description={`From ${formatDate(summary.created_from)} to ${formatDate(summary.created_to)}.`}
            />
            <div className="grid grid-4">
              <StatCard label="Prompt Tokens" value={formatNumber(summary.total_prompt_tokens)} />
              <StatCard
                label="Completion Tokens"
                value={formatNumber(summary.total_completion_tokens)}
              />
              <StatCard label="Total Tokens" value={formatNumber(summary.total_tokens)} />
              <StatCard label="Average Latency" value={formatMs(summary.avg_latency_ms)} />
            </div>
          </Card>

          <Card>
            <SectionHeader
              title="Usage By Project"
              description="Project rollups help identify which gateway clients are driving traffic and cost."
            />
            {byProject.length === 0 ? (
              <EmptyState title="No project usage">
                No gateway request metadata exists for this time window.
              </EmptyState>
            ) : (
              <Table aria-label="Usage by project">
                <thead>
                  <tr>
                    <th>Project</th>
                    <th>Requests</th>
                    <th>Success</th>
                    <th>Fallback</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                    <th>Avg latency</th>
                  </tr>
                </thead>
                <tbody>
                  {byProject.map((row) => (
                    <tr key={row.project_id ?? "unknown-project"}>
                      <td>{row.project_name ?? row.project_id ?? "Unassigned"}</td>
                      <td>{formatNumber(row.total_requests)}</td>
                      <td>{formatRate(row.success_rate)}</td>
                      <td>{formatRate(row.fallback_rate)}</td>
                      <td>{formatNumber(row.total_tokens)}</td>
                      <td>{formatCost(row.estimated_cost)}</td>
                      <td>{formatMs(row.avg_latency_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <SectionHeader
              title="Usage By Provider"
              description="Provider rollups show served-provider distribution, including unserved started or blocked rows."
            />
            {byProvider.length === 0 ? (
              <EmptyState title="No provider usage">
                No gateway request metadata exists for this time window.
              </EmptyState>
            ) : (
              <Table aria-label="Usage by provider">
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Requests</th>
                    <th>Success</th>
                    <th>Fallback</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                    <th>Avg latency</th>
                  </tr>
                </thead>
                <tbody>
                  {byProvider.map((row) => (
                    <tr key={row.provider ?? "unserved"}>
                      <td>{row.provider ?? "Unserved"}</td>
                      <td>{formatNumber(row.total_requests)}</td>
                      <td>{formatRate(row.success_rate)}</td>
                      <td>{formatRate(row.fallback_rate)}</td>
                      <td>{formatNumber(row.total_tokens)}</td>
                      <td>{formatCost(row.estimated_cost)}</td>
                      <td>{formatMs(row.avg_latency_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </>
      ) : null}
    </>
  );
}
