"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type ProviderRow = {
  id: string;
  provider: "openai" | "anthropic";
  label: string | null;
  key_mask: string;
  is_active: boolean;
  revoked_at: string | null;
  last_test_status: string | null;
  last_test_error: string | null;
  last_tested_at: string | null;
  created_at: string;
  updated_at: string;
};

type TestResult = {
  status: string;
  latency_ms: number;
  error: string | null;
};

const BACKEND_BASE =
  process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://localhost:8000";

export default function ProvidersPage() {
  const [rows, setRows] = useState<ProviderRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [provider, setProvider] = useState<"openai" | "anthropic">("openai");
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});

  const sortedRows = useMemo(
    () => [...rows].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [rows],
  );

  async function fetchRows() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BACKEND_BASE}/admin/providers`, {
        credentials: "include",
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
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
    try {
      const res = await fetch(`${BACKEND_BASE}/admin/providers`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider,
          label: label.trim() || null,
          api_key: apiKey,
        }),
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        setError("Failed to save provider config.");
        return;
      }
      setApiKey("");
      setLabel("");
      await fetchRows();
    } finally {
      setSubmitting(false);
    }
  }

  async function revoke(id: string) {
    const res = await fetch(`${BACKEND_BASE}/admin/providers/${id}/revoke`, {
      method: "POST",
      credentials: "include",
    });
    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }
    await fetchRows();
  }

  async function testProvider(id: string, providerName: "openai" | "anthropic") {
    const res = await fetch(`${BACKEND_BASE}/admin/providers/${id}/test`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!res.ok) {
      setTestResults((prev) => ({
        ...prev,
        [id]: { status: "failed", latency_ms: 0, error: "test request failed" },
      }));
      return;
    }
    const result = (await res.json()) as TestResult;
    setTestResults((prev) => ({ ...prev, [id]: result }));
    await fetchRows();
  }

  return (
    <>
      <h2>Providers</h2>
      <p className="muted">
        Add, revoke, and test provider credentials. Secrets are encrypted at
        rest and shown only as masked values.
      </p>

      <div className="card">
        <h3>Add provider key</h3>
        <form className="stack" onSubmit={onSubmit}>
          <label>
            Provider
            <select value={provider} onChange={(e) => setProvider(e.target.value as "openai" | "anthropic") }>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </label>
          <label>
            Label
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Primary"
            />
          </label>
          <label>
            API key
            <input
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              type="password"
              autoComplete="off"
              placeholder="Paste provider API key"
            />
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Save provider"}
          </button>
        </form>
      </div>

      <div className="card">
        <h3>Configured providers</h3>
        {error && <p className="error">{error}</p>}
        {loading ? (
          <p className="muted">Loading...</p>
        ) : sortedRows.length === 0 ? (
          <p className="muted">No providers configured yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Label</th>
                <th>Key</th>
                <th>Status</th>
                <th>Last test</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row) => {
                const test = testResults[row.id];
                return (
                  <tr key={row.id}>
                    <td>{row.provider}</td>
                    <td>{row.label ?? "-"}</td>
                    <td>{row.key_mask}</td>
                    <td>{row.is_active ? "active" : "revoked"}</td>
                    <td>
                      {test
                        ? `${test.status}${
                            test.error ? ` (${test.error})` : ` (${test.latency_ms}ms)`
                          }`
                        : row.last_test_status ?? "never"}
                    </td>
                    <td>
                      <div className="inline-actions">
                        <button
                          type="button"
                          onClick={() => testProvider(row.id, row.provider)}
                          disabled={!row.is_active}
                        >
                          Test
                        </button>
                        <button
                          type="button"
                          onClick={() => revoke(row.id)}
                          disabled={!row.is_active}
                        >
                          Revoke
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
