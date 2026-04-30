"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  ErrorState,
  Field,
  FormRow,
  Input,
  LoadingState,
  PageHeader,
  SectionHeader,
  SecretValue,
  Select,
  StatusBadge,
  Table,
} from "@/components/ui";
import { BACKEND_BASE, adminSessionFetch } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { ProviderRow, ProviderTestResult } from "@/lib/types";

export default function ProvidersPage() {
  const [rows, setRows] = useState<ProviderRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [provider, setProvider] = useState<"openai" | "anthropic">("openai");
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ProviderTestResult>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const sortedRows = useMemo(
    () => [...rows].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [rows],
  );

  async function fetchRows() {
    setLoading(true);
    setError(null);
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/providers`);
      if (!res.ok) {
        setError("Failed to load provider configs.");
        return;
      }
      setRows((await res.json()) as ProviderRow[]);
    } catch {
      setError("Backend not reachable.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchRows();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!apiKey.trim()) {
      setError("API key is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/providers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider,
          label: label.trim() || null,
          api_key: apiKey,
        }),
      });
      if (!res.ok) {
        setError("Failed to save provider config.");
        return;
      }
      setApiKey("");
      setLabel("");
      setSuccess("Provider credential saved. Test it before sending gateway traffic.");
      await fetchRows();
    } finally {
      setSubmitting(false);
    }
  }

  async function revoke(id: string) {
    setRevokingId(id);
    setError(null);
    setSuccess(null);
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/providers/${id}/revoke`, {
        method: "POST",
      });
      if (!res.ok) {
        setError("Failed to revoke provider config.");
        return;
      }
      setSuccess("Provider credential revoked.");
      await fetchRows();
    } finally {
      setRevokingId(null);
    }
  }

  async function testProvider(id: string) {
    setTestingId(id);
    setError(null);
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/providers/${id}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        setTestResults((prev) => ({
          ...prev,
          [id]: { status: "failed", latency_ms: 0, error: "test request failed" },
        }));
        return;
      }
      const result = (await res.json()) as ProviderTestResult;
      setTestResults((prev) => ({ ...prev, [id]: result }));
      await fetchRows();
    } finally {
      setTestingId(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Upstream credentials"
        title="Providers"
        description="Provider credentials let Conexus route gateway requests to upstream OpenAI or Anthropic APIs. Plaintext provider keys are never shown after save."
      />

      {error && <ErrorState message={error} />}
      {success && <Alert tone="success">{success}</Alert>}

      <Card>
        <SectionHeader
          title="Add Provider Key"
          description="Store one upstream credential at a time. Use labels to distinguish primary, backup, or environment-specific keys."
        />
        <form className="stack" onSubmit={onSubmit}>
          <FormRow>
            <Field label="Provider">
              <Select
                value={provider}
                onChange={(e) => setProvider(e.target.value as "openai" | "anthropic")}
              >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              </Select>
            </Field>
            <Field label="Label" hint="Optional. Example: Primary or Anthropic backup.">
              <Input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Primary"
              />
            </Field>
          </FormRow>
          <Field label="API key" hint="Saved securely by the backend; the BO only displays a masked value later.">
            <Input
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              type="password"
              autoComplete="off"
              placeholder="Paste provider API key"
            />
          </Field>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Save provider"}
          </Button>
        </form>
      </Card>

      <Card>
        <SectionHeader
          title="Configured Providers"
          description="Test active credentials before relying on them for gateway traffic. Revoked providers remain visible for audit context."
        />
        {loading ? (
          <LoadingState label="Loading providers..." />
        ) : sortedRows.length === 0 ? (
          <EmptyState title="No provider credentials configured">
            Add a provider key first, then run a smoke test after creating a project API key.
          </EmptyState>
        ) : (
          <Table aria-label="Configured providers">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Label</th>
                <th>Key</th>
                <th>Status</th>
                <th>Last test</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row) => {
                const test = testResults[row.id];
                const status = test?.status ?? row.last_test_status ?? "never";
                const testError = test?.error ?? row.last_test_error;
                const latency = test?.latency_ms;
                return (
                  <tr key={row.id} className={!row.is_active ? "row-muted" : undefined}>
                    <td><strong>{row.provider}</strong></td>
                    <td>{row.label ?? "-"}</td>
                    <td><SecretValue value={row.key_mask} /></td>
                    <td>
                      <StatusBadge status={row.is_active ? "active" : "revoked"} />
                    </td>
                    <td>
                      <div className="stack">
                        <StatusBadge
                          status={
                            status === "ok"
                              ? "ok"
                              : status === "failed"
                                ? "failed"
                                : "never"
                          }
                        />
                        {latency !== undefined && !testError && (
                          <span className="muted">{latency}ms</span>
                        )}
                        {testError && <span className="muted">{testError}</span>}
                      </div>
                    </td>
                    <td>{formatDateTime(row.updated_at)}</td>
                    <td>
                      <div className="inline-actions">
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => testProvider(row.id)}
                          disabled={!row.is_active || testingId === row.id}
                        >
                          {testingId === row.id ? "Testing..." : "Test"}
                        </Button>
                        <ConfirmAction
                          message={`Revoke ${row.provider} provider ${row.label ?? row.key_mask}? Gateway traffic will no longer use this credential.`}
                          onConfirm={() => void revoke(row.id)}
                          disabled={!row.is_active || revokingId === row.id}
                        >
                          {revokingId === row.id ? "Revoking..." : "Revoke"}
                        </ConfirmAction>
                      </div>
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
