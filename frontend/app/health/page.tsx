"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Card,
  CopyButton,
  ErrorState,
  JsonBlock,
  KeyValueGrid,
  PageHeader,
  RefreshButton,
  SectionHeader,
  StatusBadge,
} from "@/components/ui";
import { BACKEND_BASE, getEnvironmentLabel } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

type HealthResponse = { status: string; service?: string; version?: string } | unknown;
type ReadyzResponse = { status?: string; checks?: Record<string, boolean> } | unknown;

async function fetchJson(url: string): Promise<{ ok: boolean; status: number; body: unknown }> {
  try {
    const res = await fetch(url, { cache: "no-store" });
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    return { ok: res.ok, status: res.status, body };
  } catch (err) {
    return { ok: false, status: 0, body: err instanceof Error ? err.message : err };
  }
}

export default function HealthPage() {
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readyz, setReadyz] = useState<ReadyzResponse | null>(null);
  const [healthStatus, setHealthStatus] = useState<{ ok: boolean; status: number } | null>(null);
  const [readyzStatus, setReadyzStatus] = useState<{ ok: boolean; status: number } | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setPageError(null);
    try {
      const [healthRes, readyRes] = await Promise.all([
        fetchJson(`${BACKEND_BASE}/health`),
        fetchJson(`${BACKEND_BASE}/readyz`),
      ]);
      setHealthStatus({ ok: healthRes.ok, status: healthRes.status });
      setReadyzStatus({ ok: readyRes.ok, status: readyRes.status });
      setHealth(healthRes.body);
      setReadyz(readyRes.body);
      setLastCheckedAt(new Date().toISOString());
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Failed to check health.");
    } finally {
      setLoading(false);
    }
  }

  const diagnostics = useMemo(() => {
    return {
      backend_base: BACKEND_BASE,
      environment: getEnvironmentLabel(),
      last_checked_at: lastCheckedAt,
      health: { status: healthStatus, body: health },
      readyz: { status: readyzStatus, body: readyz },
    };
  }, [health, readyz, healthStatus, readyzStatus, lastCheckedAt]);

  const diagnosticsJson = useMemo(() => JSON.stringify(diagnostics, null, 2), [diagnostics]);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <PageHeader
        eyebrow="Diagnostics"
        title="Health"
        description="Check backend health and readiness without using admin-cookie endpoints."
        actions={<RefreshButton onClick={refresh} loading={loading} />}
      />

      {pageError && <ErrorState message={pageError} />}

      <Card>
        <SectionHeader
          title="Diagnostics"
          description="These values are safe to share with internal operators."
          actions={<CopyButton value={diagnosticsJson} label="Copy diagnostics JSON" />}
        />
        <KeyValueGrid
          items={[
            { label: "backend_base", value: <code className="wrap-anywhere">{BACKEND_BASE}</code> },
            { label: "environment", value: getEnvironmentLabel() },
            { label: "last_checked", value: lastCheckedAt ? formatDateTime(lastCheckedAt) : "—" },
          ]}
        />
      </Card>

      <Card>
        <SectionHeader title="Health" description="Calls GET /health." />
        <KeyValueGrid
          items={[
            {
              label: "http_status",
              value: healthStatus ? String(healthStatus.status) : "—",
            },
            {
              label: "status",
              value: healthStatus ? (
                <StatusBadge status={healthStatus.ok ? "ok" : "failed"} />
              ) : (
                <span className="muted">not checked</span>
              ),
            },
          ]}
        />
        {health != null && <JsonBlock value={health} title="Raw /health JSON" />}
      </Card>

      <Card>
        <SectionHeader title="Readiness" description="Calls GET /readyz." />
        <KeyValueGrid
          items={[
            {
              label: "http_status",
              value: readyzStatus ? String(readyzStatus.status) : "—",
            },
            {
              label: "status",
              value: readyzStatus ? (
                <StatusBadge status={readyzStatus.ok ? "ok" : "failed"} />
              ) : (
                <span className="muted">not checked</span>
              ),
            },
          ]}
        />
        {readyz != null && <JsonBlock value={readyz} title="Raw /readyz JSON" />}
      </Card>

      <Card>
        <SectionHeader title="Tip" description="If readiness fails, check DB connectivity, encryption setup, and model aliases." />
      </Card>
    </>
  );
}

