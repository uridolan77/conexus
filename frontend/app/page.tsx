"use client";

import { HealthCard } from "../components/HealthCard";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  LinkButton,
  LoadingState,
  PageHeader,
  SectionHeader,
  StatCard,
  StatusBadge,
  Table,
} from "@/components/ui";
import { getDashboardSummary } from "@/lib/admin/dashboard";
import { listProjects } from "@/lib/admin/projects";
import { listProviders } from "@/lib/admin/providers";
import { formatDateTime, formatLatency } from "@/lib/format";
import type { DashboardSummary, ProjectRow, ProviderRow } from "@/lib/types";
import { useEffect, useMemo, useState } from "react";

function formatCost(value: number | null | undefined) {
  if (value === null || value === undefined) return "Unavailable";
  if (value === 0) return "$0";
  if (value < 0.0001) return "<$0.0001";
  return `$${value.toFixed(4)}`;
}

function formatRate(value: number | null | undefined) {
  if (value === null || value === undefined) return "Unavailable";
  return `${(value * 100).toFixed(1)}%`;
}

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectRow[] | null>(null);
  const [providers, setProviders] = useState<ProviderRow[] | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSummary() {
      setSummaryLoading(true);
      setSummaryError(null);
      try {
        const [projectRes, providerRes, dashboardRes] = await Promise.all([
          listProjects(),
          listProviders(),
          getDashboardSummary(),
        ]);

        const failures: string[] = [];
        if (projectRes.ok) {
          setProjects(projectRes.data);
        } else {
          setProjects(null);
          failures.push("projects");
        }

        if (providerRes.ok) {
          setProviders(providerRes.data);
        } else {
          setProviders(null);
          failures.push("providers");
        }

        if (dashboardRes.ok) {
          setSummary(dashboardRes.data);
        } else {
          setSummary(null);
          failures.push("dashboard");
        }

        if (failures.length > 0) {
          setSummaryError(`Unable to load dashboard summary for ${failures.join(" and ")}.`);
        }
      } catch {
        setProjects(null);
        setProviders(null);
        setSummary(null);
        setSummaryError("Unable to load dashboard summary. Check that the backend is reachable.");
      } finally {
        setSummaryLoading(false);
      }
    }
    void loadSummary();
  }, []);

  const projectRows = projects ?? [];
  const providerRows = providers ?? [];
  const activeProviders = providers
    ? providers.filter((provider) => provider.is_active).length
    : null;
  const activeKeys = projectRows.reduce(
    (total, project) => total + project.active_key_count,
    0,
  );
  const projectRequestCount = projectRows.reduce(
    (total, project) => total + project.total_request_count,
    0,
  );
  const checklist = useMemo(
    () => [
      {
        label: "Add provider key",
        done: (activeProviders ?? 0) > 0,
        href: "/providers",
      },
      {
        label: "Create project",
        done: projectRows.length > 0,
        href: "/projects",
      },
      {
        label: "Issue project API key",
        done: activeKeys > 0,
        href: "/projects",
      },
      {
        label: "Test gateway",
        done: projectRequestCount > 0,
        href: "/smoke-tests",
      },
      {
        label: "Inspect requests",
        done: false,
        href: "/requests",
      },
    ],
    [activeKeys, activeProviders, projectRequestCount, projectRows.length],
  );

  return (
    <>
      <PageHeader
        eyebrow="Back office"
        title="Dashboard"
        description="Set up Conexus, verify the gateway path, and keep the current operational state easy to read."
        actions={<LinkButton href="/smoke-tests" variant="primary">Test Gateway</LinkButton>}
      />

      {summaryError && <Alert tone="warning">{summaryError}</Alert>}

      {summaryLoading ? (
        <Card>
          <LoadingState label="Loading dashboard summary..." />
        </Card>
      ) : (
        <div className="grid grid-4">
          <StatCard
            label="Projects"
            value={projects ? projects.length : "Unavailable"}
            hint="Gateway clients"
          />
          <StatCard
            label="Active Provider Keys"
            value={activeProviders ?? "Unavailable"}
            hint="Upstream credentials"
          />
          <StatCard
            label="Requests today"
            value={summary ? summary.requests_today.toLocaleString() : "Unavailable"}
            hint="From request logs"
          />
          <StatCard
            label="Estimated Cost Today"
            value={formatCost(summary?.estimated_cost_today)}
            hint="USD from logged requests"
          />
          <StatCard
            label="Success Rate Today"
            value={formatRate(summary?.success_rate)}
            hint={summary ? `${summary.failed_requests} failed` : "From request logs"}
          />
          <StatCard
            label="Average Latency Today"
            value={
              summary?.average_latency_ms === null || summary?.average_latency_ms === undefined
                ? "Unavailable"
                : formatLatency(summary.average_latency_ms)
            }
            hint="Completed and failed calls"
          />
        </div>
      )}

      <HealthCard />

      <div className="grid grid-2">
        <Card>
          <SectionHeader
            title="Quick-Start Checklist"
            description="A first-time setup path from provider credentials to a verified gateway request."
          />
          <div className="stack">
            {checklist.map((item, index) => (
              <div className="step" key={item.label}>
                <div>
                  <span>
                    {index + 1}. {item.label}
                  </span>
                  <small>{item.done ? "Complete" : "Recommended next action"}</small>
                </div>
                <LinkButton href={item.href} variant={item.done ? "ghost" : "secondary"}>
                  {item.done ? "Review" : "Open"}
                </LinkButton>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <SectionHeader
            title="Operational Shortcuts"
            description="Jump to the workflows that keep the gateway usable."
          />
          <div className="stack">
            <LinkButton href="/providers">Configure providers</LinkButton>
            <LinkButton href="/projects">Manage projects and API keys</LinkButton>
            <LinkButton href="/smoke-tests">Test chat completions</LinkButton>
            <LinkButton href="/usage">Review usage and costs</LinkButton>
            <LinkButton href="/routing">Review routing policy</LinkButton>
            <LinkButton href="/requests">View request monitoring plan</LinkButton>
          </div>
        </Card>
      </div>

      <Card>
        <SectionHeader
          title="Latest Errors"
          description="Most recent failed gateway requests across projects."
        />
        {summaryLoading ? (
          <LoadingState label="Loading latest errors..." />
        ) : !summary || summary.latest_errors.length === 0 ? (
          <EmptyState title="No recent gateway errors">
            Failed requests will appear here as soon as the gateway logs them.
          </EmptyState>
        ) : (
          <Table aria-label="Latest gateway errors">
            <thead>
              <tr>
                <th>Created</th>
                <th>Request ID</th>
                <th>Project</th>
                <th>Requested model</th>
                <th>Route</th>
                <th>Error</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              {summary.latest_errors.map((item) => (
                <tr key={item.request_id} className="row-warning">
                  <td>{formatDateTime(item.created_at)}</td>
                  <td><code>{item.request_id}</code></td>
                  <td>{item.project_name ?? item.project_id ?? "-"}</td>
                  <td><code>{item.requested_model}</code></td>
                  <td>
                    <div className="stack-tight">
                      <strong>{item.provider ?? "-"}</strong>
                      <code>{item.model ?? "-"}</code>
                    </div>
                  </td>
                  <td>
                    <div className="stack-tight">
                      <StatusBadge status="failed" />
                      {item.error_code && <Badge tone="warning">{item.error_code}</Badge>}
                    </div>
                  </td>
                  <td>
                    <LinkButton href={`/requests?request_id=${encodeURIComponent(item.request_id)}`}>
                      View
                    </LinkButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {!summaryLoading && !summaryError && projectRows.length === 0 && providerRows.length === 0 && (
        <EmptyState title="Start with an upstream provider">
          Add an OpenAI or Anthropic key, create a project, issue a project API key,
          then run the smoke test to confirm the gateway path.
        </EmptyState>
      )}
    </>
  );
}
