"use client";

import { HealthCard } from "../components/HealthCard";
import {
  Alert,
  Card,
  EmptyState,
  LinkButton,
  LoadingState,
  PageHeader,
  SectionHeader,
  StatCard,
} from "@/components/ui";
import { BACKEND_BASE, adminSessionFetch } from "@/lib/api";
import type { ProjectRow, ProviderRow, UsageSummary } from "@/lib/types";
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
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSummary() {
      setSummaryLoading(true);
      setSummaryError(null);
      try {
        const [projectRes, providerRes, usageRes] = await Promise.all([
          adminSessionFetch(`${BACKEND_BASE}/admin/projects`),
          adminSessionFetch(`${BACKEND_BASE}/admin/providers`),
          adminSessionFetch(`${BACKEND_BASE}/admin/usage/summary?window=30d`, {
            cache: "no-store",
          }),
        ]);

        const failures: string[] = [];
        if (projectRes.ok) {
          setProjects((await projectRes.json()) as ProjectRow[]);
        } else {
          setProjects(null);
          failures.push("projects");
        }

        if (providerRes.ok) {
          setProviders((await providerRes.json()) as ProviderRow[]);
        } else {
          setProviders(null);
          failures.push("providers");
        }

        if (usageRes.ok) {
          setUsage((await usageRes.json()) as UsageSummary);
        } else {
          setUsage(null);
          failures.push("usage");
        }

        if (failures.length > 0) {
          setSummaryError(`Unable to load dashboard summary for ${failures.join(" and ")}.`);
        }
      } catch {
        setProjects(null);
        setProviders(null);
        setUsage(null);
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
        label: "Run smoke test",
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
            label="Requests (30d)"
            value={usage ? usage.total_requests.toLocaleString() : "Unavailable"}
            hint="From request logs"
          />
          <StatCard
            label="Estimated Cost (30d)"
            value={formatCost(usage?.estimated_cost)}
            hint="USD from logged usage"
          />
          <StatCard
            label="Success Rate (30d)"
            value={formatRate(usage?.success_rate)}
            hint={usage ? `${usage.completed_requests} completed` : "From request logs"}
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

      {!summaryLoading && !summaryError && projectRows.length === 0 && providerRows.length === 0 && (
        <EmptyState title="Start with an upstream provider">
          Add an OpenAI or Anthropic key, create a project, issue a project API key,
          then run the smoke test to confirm the gateway path.
        </EmptyState>
      )}
    </>
  );
}
