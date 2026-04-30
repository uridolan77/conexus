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
  MetricCard,
  Table,
} from "@/components/ui";
import { formatCost, formatDateTime, formatLatency, formatPercentRatio, formatTokens } from "@/lib/format";
import {
  getUsageByProject,
  getUsageByProvider,
  getUsageSummary,
  getUsageTimeseries,
  type UsageWindow,
} from "@/lib/admin/usage";
import type {
  UsageBreakdownResponse,
  UsageProjectRow,
  UsageProviderRow,
  UsageSummary,
  UsageTimeseriesPoint,
  UsageTimeseriesResponse,
} from "@/lib/types";

export default function UsagePage() {
  const [windowValue, setWindowValue] = useState<UsageWindow>("30d");
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [byProject, setByProject] = useState<UsageProjectRow[]>([]);
  const [byProvider, setByProvider] = useState<UsageProviderRow[]>([]);
  const [timeseries, setTimeseries] = useState<UsageTimeseriesPoint[]>([]);
  const [showZeroDays, setShowZeroDays] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function formatBucketStart(value: string) {
    if (windowValue === "24h") return formatDateTime(value);
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "2-digit" }).format(dt);
  }

  function isZeroBucket(row: UsageTimeseriesPoint) {
    const cost = row.estimated_cost ?? 0;
    return row.total_requests === 0 && row.total_tokens === 0 && cost === 0;
  }

  const visibleTimeseries = showZeroDays ? timeseries : timeseries.filter((row) => !isZeroBucket(row));

  useEffect(() => {
    async function loadUsage() {
      setLoading(true);
      setError(null);
      try {
        const [summaryRes, projectRes, providerRes, timeseriesRes] = await Promise.all([
          getUsageSummary(windowValue),
          getUsageByProject(windowValue),
          getUsageByProvider(windowValue),
          getUsageTimeseries(windowValue),
        ]);

        if (!summaryRes.ok) {
          setError(summaryRes.error.message);
          return;
        }
        if (!projectRes.ok) {
          setError(projectRes.error.message);
          return;
        }
        if (!providerRes.ok) {
          setError(providerRes.error.message);
          return;
        }
        if (!timeseriesRes.ok) {
          setError(timeseriesRes.error.message);
          return;
        }

        setSummary(summaryRes.data as UsageSummary);
        setByProject((projectRes.data as UsageBreakdownResponse<UsageProjectRow>).items);
        setByProvider((providerRes.data as UsageBreakdownResponse<UsageProviderRow>).items);
        setTimeseries((timeseriesRes.data as UsageTimeseriesResponse).items);
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
            <MetricCard label="Total requests" value={summary.total_requests.toLocaleString()} />
            <MetricCard label="Completed requests" value={summary.completed_requests.toLocaleString()} />
            <MetricCard label="Failed requests" value={summary.failed_requests.toLocaleString()} />
            <MetricCard label="Success rate" value={formatPercentRatio(summary.success_rate)} />

            <MetricCard label="Fallback rate" value={formatPercentRatio(summary.fallback_rate)} />
            <MetricCard label="Prompt tokens" value={formatTokens(summary.total_prompt_tokens)} />
            <MetricCard label="Completion tokens" value={formatTokens(summary.total_completion_tokens)} />
            <MetricCard label="Total tokens" value={formatTokens(summary.total_tokens)} />

            <MetricCard label="Estimated cost" value={formatCost(summary.estimated_cost)} hint={summary.currency} />
            <MetricCard label="Average latency" value={formatLatency(summary.avg_latency_ms)} />
          </div>

          <Card>
            <SectionHeader
              title="Summary"
              description={`From ${formatDateTime(summary.created_from)} to ${formatDateTime(summary.created_to)}.`}
            />
            <p className="muted">
              Empty databases, streaming rows, or incomplete request rows may result in missing latency and token/cost
              fields. This page renders null metrics as “—”.
            </p>
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
                      <td>{row.total_requests.toLocaleString()}</td>
                      <td>{formatPercentRatio(row.success_rate)}</td>
                      <td>{formatPercentRatio(row.fallback_rate)}</td>
                      <td>{formatTokens(row.total_tokens)}</td>
                      <td>{formatCost(row.estimated_cost)}</td>
                      <td>{formatLatency(row.avg_latency_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <SectionHeader
              title="Usage Over Time"
          description={showZeroDays
            ? "Bucketed request metadata for the selected window, including zero-activity buckets."
            : "Bucketed request metadata for the selected window, hiding zero-activity buckets by default."}
          actions={
            <button
              type="button"
              className="button button-secondary"
              onClick={() => setShowZeroDays((s) => !s)}
            >
              {showZeroDays ? "Hide zero days" : "Show zero days"}
            </button>
          }
            />
        {visibleTimeseries.length === 0 ? (
              <EmptyState title="No usage buckets">
                No gateway request metadata exists for this time window.
              </EmptyState>
            ) : (
              <Table aria-label="Usage over time">
                <thead>
                  <tr>
                    <th>Bucket start</th>
                    <th>Requests</th>
                    <th>Success</th>
                    <th>Fallback</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                    <th>Avg latency</th>
                  </tr>
                </thead>
                <tbody>
              {visibleTimeseries.map((row) => (
                    <tr key={row.bucket_start}>
                  <td>{formatBucketStart(row.bucket_start)}</td>
                      <td>{row.total_requests.toLocaleString()}</td>
                      <td>{formatPercentRatio(row.success_rate)}</td>
                      <td>{formatPercentRatio(row.fallback_rate)}</td>
                      <td>{formatTokens(row.total_tokens)}</td>
                      <td>{formatCost(row.estimated_cost)}</td>
                      <td>{formatLatency(row.avg_latency_ms)}</td>
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
                      <td>{row.total_requests.toLocaleString()}</td>
                      <td>{formatPercentRatio(row.success_rate)}</td>
                      <td>{formatPercentRatio(row.fallback_rate)}</td>
                      <td>{formatTokens(row.total_tokens)}</td>
                      <td>{formatCost(row.estimated_cost)}</td>
                      <td>{formatLatency(row.avg_latency_ms)}</td>
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
