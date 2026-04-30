"use client";

import { Card, Alert, KeyValueGrid, PageHeader, SectionHeader } from "@/components/ui";
import { BACKEND_BASE, getEnvironmentLabel } from "@/lib/api";

const FRONTEND_VERSION = process.env.NEXT_PUBLIC_FRONTEND_VERSION ?? "unknown";

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Operations"
        title="Settings"
        description="Read-only frontend-known operational settings and assumptions."
      />

      <Card>
        <SectionHeader title="Frontend settings" description="Safe values known to the frontend bundle." />
        <KeyValueGrid
          items={[
            { label: "BACKEND_BASE", value: <code className="wrap-anywhere">{BACKEND_BASE}</code> },
            { label: "environment", value: getEnvironmentLabel() },
            { label: "frontend_version", value: FRONTEND_VERSION },
            {
              label: "auth/session_model",
              value: "Admin cookie session; admin API calls include credentials and redirect to /login on 401.",
            },
          ]}
        />
      </Card>

      <Card>
        <SectionHeader title="Backend safe config" description="Optional backend endpoint (not implemented yet)." />
        <Alert tone="info">Backend safe config endpoint is not available yet.</Alert>
      </Card>

      <Card>
        <SectionHeader title="Known assumptions" description="Frontend expectations about backend behavior." />
        <ul>
          <li>Admin endpoints live under <code>/admin/*</code> and require an authenticated session cookie.</li>
          <li>Gateway endpoints live under <code>/v1/*</code> and use <code>Authorization: Bearer &lt;project_api_key&gt;</code>.</li>
          <li>Request metadata is safe to show; prompt/response bodies are not stored or rendered in BO pages.</li>
        </ul>
      </Card>
    </>
  );
}

