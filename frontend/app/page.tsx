"use client";

import { HealthCard } from "../components/HealthCard";
import {
  Card,
  EmptyState,
  LinkButton,
  PageHeader,
  SectionHeader,
  StatCard,
} from "@/components/ui";
import { BACKEND_BASE } from "@/lib/api";
import type { ProjectRow, ProviderRow } from "@/lib/types";
import { useEffect, useMemo, useState } from "react";

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [providers, setProviders] = useState<ProviderRow[]>([]);

  useEffect(() => {
    async function loadSummary() {
      const [projectRes, providerRes] = await Promise.all([
        fetch(`${BACKEND_BASE}/admin/projects`, { credentials: "include" }),
        fetch(`${BACKEND_BASE}/admin/providers`, { credentials: "include" }),
      ]);
      if (projectRes.status === 401 || providerRes.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (projectRes.ok) setProjects((await projectRes.json()) as ProjectRow[]);
      if (providerRes.ok) setProviders((await providerRes.json()) as ProviderRow[]);
    }
    void loadSummary();
  }, []);

  const activeProviders = providers.filter((provider) => provider.is_active).length;
  const activeKeys = projects.reduce(
    (total, project) => total + project.active_key_count,
    0,
  );
  const totalRequests = projects.reduce(
    (total, project) => total + project.total_request_count,
    0,
  );
  const checklist = useMemo(
    () => [
      {
        label: "Add provider key",
        done: activeProviders > 0,
        href: "/providers",
      },
      {
        label: "Create project",
        done: projects.length > 0,
        href: "/projects",
      },
      {
        label: "Issue project API key",
        done: activeKeys > 0,
        href: "/projects",
      },
      {
        label: "Run smoke test",
        done: totalRequests > 0,
        href: "/smoke-tests",
      },
      {
        label: "Inspect requests",
        done: false,
        href: "/requests",
      },
    ],
    [activeKeys, activeProviders, projects.length, totalRequests],
  );

  return (
    <>
      <PageHeader
        eyebrow="Back office"
        title="Dashboard"
        description="Set up Conexus, verify the gateway path, and keep the current operational state easy to read."
        actions={<LinkButton href="/smoke-tests" variant="primary">Run Smoke Test</LinkButton>}
      />

      <div className="grid grid-3">
        <StatCard label="Projects" value={projects.length} hint="Gateway clients" />
        <StatCard label="Active Provider Keys" value={activeProviders} hint="Upstream credentials" />
        <StatCard label="Logged Requests" value={totalRequests} hint="Persisted by the gateway" />
      </div>

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
            <LinkButton href="/requests">View request monitoring plan</LinkButton>
          </div>
        </Card>
      </div>

      {projects.length === 0 && providers.length === 0 && (
        <EmptyState title="Start with an upstream provider">
          Add an OpenAI or Anthropic key, create a project, issue a project API key,
          then run the smoke test to confirm the gateway path.
        </EmptyState>
      )}
    </>
  );
}
