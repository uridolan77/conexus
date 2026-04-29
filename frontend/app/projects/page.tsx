"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  CopyButton,
  EmptyState,
  ErrorState,
  Field,
  FormRow,
  Input,
  KeyValueGrid,
  LoadingState,
  PageHeader,
  SectionHeader,
  StatusBadge,
  Table,
} from "@/components/ui";
import { BACKEND_BASE, adminSessionFetch, formatDate } from "@/lib/api";
import type {
  ApiKeyCreated,
  ApiKeyRow,
  ProjectLimits,
  ProjectLimitsReservations,
  ProjectLimitsUsage,
  ProjectRow,
} from "@/lib/types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [projectName, setProjectName] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [keys, setKeys] = useState<ApiKeyRow[]>([]);
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [latestIssuedKey, setLatestIssuedKey] = useState<ApiKeyCreated | null>(null);
  const [limits, setLimits] = useState<ProjectLimits | null>(null);
  const [limitsUsage, setLimitsUsage] = useState<ProjectLimitsUsage | null>(null);
  const [limitsReservations, setLimitsReservations] = useState<ProjectLimitsReservations | null>(
    null,
  );
  const [loadingLimits, setLoadingLimits] = useState(false);
  const [loadingLimitsUsage, setLoadingLimitsUsage] = useState(false);
  const [loadingLimitsReservations, setLoadingLimitsReservations] = useState(false);
  const [savingLimits, setSavingLimits] = useState(false);
  const [limitMode, setLimitMode] = useState<ProjectLimits["limit_mode"]>("disabled");
  const [monthlyCostLimit, setMonthlyCostLimit] = useState("");
  const [dailyRequestLimit, setDailyRequestLimit] = useState("");
  const [dailyTokenLimit, setDailyTokenLimit] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);
  const [issuingKey, setIssuingKey] = useState(false);
  const [revokingKeyId, setRevokingKeyId] = useState<string | null>(null);

  async function fetchProjects() {
    setLoadingProjects(true);
    setError(null);
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/projects`);
      if (!res.ok) {
        setError("Unable to load projects.");
        return;
      }
      const body = (await res.json()) as ProjectRow[];
      setProjects(body);
      if (!selectedProjectId && body.length > 0) {
        setSelectedProjectId(body[0].id);
      }
    } finally {
      setLoadingProjects(false);
    }
  }

  async function fetchKeys(projectId: string) {
    setLoadingKeys(true);
    setError(null);
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/projects/${projectId}/keys`);
      if (!res.ok) {
        setError("Unable to load project keys.");
        return;
      }
      setKeys((await res.json()) as ApiKeyRow[]);
    } finally {
      setLoadingKeys(false);
    }
  }

  async function fetchLimits(projectId: string) {
    setLoadingLimits(true);
    setError(null);
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/projects/${projectId}/limits`);
      if (!res.ok) {
        setError("Unable to load project limits.");
        return;
      }
      const body = (await res.json()) as ProjectLimits;
      setLimits(body);
      setLimitMode(body.limit_mode);
      setMonthlyCostLimit(body.monthly_cost_limit == null ? "" : String(body.monthly_cost_limit));
      setDailyRequestLimit(body.daily_request_limit == null ? "" : String(body.daily_request_limit));
      setDailyTokenLimit(body.daily_token_limit == null ? "" : String(body.daily_token_limit));
    } finally {
      setLoadingLimits(false);
    }
  }

  async function fetchLimitsUsage(projectId: string) {
    setLoadingLimitsUsage(true);
    setError(null);
    try {
      const res = await adminSessionFetch(
        `${BACKEND_BASE}/admin/projects/${projectId}/limits/usage`,
      );
      if (!res.ok) {
        setError("Unable to load project limit usage.");
        return;
      }
      setLimitsUsage((await res.json()) as ProjectLimitsUsage);
    } finally {
      setLoadingLimitsUsage(false);
    }
  }

  async function fetchLimitsReservations(projectId: string) {
    setLoadingLimitsReservations(true);
    setError(null);
    try {
      const res = await adminSessionFetch(
        `${BACKEND_BASE}/admin/projects/${projectId}/limits/reservations`,
      );
      if (!res.ok) {
        setError("Unable to load reservation counters.");
        return;
      }
      setLimitsReservations((await res.json()) as ProjectLimitsReservations);
    } finally {
      setLoadingLimitsReservations(false);
    }
  }

  useEffect(() => {
    void fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      setLatestIssuedKey(null);
      void fetchKeys(selectedProjectId);
      void fetchLimits(selectedProjectId);
      void fetchLimitsUsage(selectedProjectId);
      void fetchLimitsReservations(selectedProjectId);
    } else {
      setKeys([]);
      setLimits(null);
      setLimitsUsage(null);
      setLimitsReservations(null);
    }
  }, [selectedProjectId]);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    const name = projectName.trim();
    if (!name) {
      setError("Project name is required.");
      return;
    }
    setCreatingProject(true);
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) {
        setError("Unable to create project.");
        return;
      }
      const created = (await res.json()) as ProjectRow;
      setProjectName("");
      setSelectedProjectId(created.id);
      setSuccess(`Project "${created.name}" created.`);
      await fetchProjects();
    } finally {
      setCreatingProject(false);
    }
  }

  async function issueKey(event: FormEvent) {
    event.preventDefault();
    if (!selectedProjectId) {
      setError("Select a project first.");
      return;
    }
    setIssuingKey(true);
    setSuccess(null);
    const label = newKeyLabel.trim();
    try {
      const res = await adminSessionFetch(`${BACKEND_BASE}/admin/projects/${selectedProjectId}/keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: label || null }),
      });
      if (!res.ok) {
        setError("Unable to issue project key.");
        return;
      }
      const created = (await res.json()) as ApiKeyCreated;
      setLatestIssuedKey(created);
      setNewKeyLabel("");
      setSuccess("Project API key issued. Copy it now; it cannot be recovered later.");
      await fetchKeys(selectedProjectId);
      await fetchProjects();
    } finally {
      setIssuingKey(false);
    }
  }

  async function revokeKey(keyId: string) {
    if (!selectedProjectId) {
      return;
    }
    setRevokingKeyId(keyId);
    setError(null);
    setSuccess(null);
    try {
      const res = await adminSessionFetch(
        `${BACKEND_BASE}/admin/projects/${selectedProjectId}/keys/${keyId}/revoke`,
        {
          method: "POST",
        },
      );
      if (!res.ok) {
        setError("Unable to revoke project key.");
        return;
      }
      setSuccess("Project API key revoked.");
      await fetchKeys(selectedProjectId);
      await fetchProjects();
    } finally {
      setRevokingKeyId(null);
    }
  }

  function _parseOptionalInt(value: string): number | null {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number.parseInt(trimmed, 10);
    if (!Number.isFinite(parsed) || Number.isNaN(parsed) || parsed < 0) {
      throw new Error("Invalid non-negative integer.");
    }
    return parsed;
  }

  function _parseOptionalFloat(value: string): number | null {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number.parseFloat(trimmed);
    if (!Number.isFinite(parsed) || Number.isNaN(parsed) || parsed < 0) {
      throw new Error("Invalid non-negative number.");
    }
    return parsed;
  }

  async function saveLimits(event: FormEvent) {
    event.preventDefault();
    if (!selectedProjectId) return;
    setError(null);
    setSuccess(null);

    let payload: {
      limit_mode: ProjectLimits["limit_mode"];
      monthly_cost_limit: number | null;
      daily_request_limit: number | null;
      daily_token_limit: number | null;
    };
    try {
      payload = {
        limit_mode: limitMode,
        monthly_cost_limit: _parseOptionalFloat(monthlyCostLimit),
        daily_request_limit: _parseOptionalInt(dailyRequestLimit),
        daily_token_limit: _parseOptionalInt(dailyTokenLimit),
      };
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid limits.");
      return;
    }

    setSavingLimits(true);
    try {
      const res = await adminSessionFetch(
        `${BACKEND_BASE}/admin/projects/${selectedProjectId}/limits`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!res.ok) {
        setError("Unable to save project limits.");
        return;
      }
      const body = (await res.json()) as ProjectLimits;
      setLimits(body);
      setLimitMode(body.limit_mode);
      setMonthlyCostLimit(body.monthly_cost_limit == null ? "" : String(body.monthly_cost_limit));
      setDailyRequestLimit(body.daily_request_limit == null ? "" : String(body.daily_request_limit));
      setDailyTokenLimit(body.daily_token_limit == null ? "" : String(body.daily_token_limit));
      setSuccess("Project limits updated.");
      await fetchProjects();
      await fetchLimitsUsage(selectedProjectId);
      await fetchLimitsReservations(selectedProjectId);
    } finally {
      setSavingLimits(false);
    }
  }

  function _formatNumber(value: number) {
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
  }

  function _formatUsd(value: number) {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 4,
    }).format(value);
  }

  function _percent(current: number, limit: number | null) {
    if (!limit || limit <= 0) return null;
    return Math.min(999, (current / limit) * 100);
  }

  const selectedProject = projects.find((project) => project.id === selectedProjectId);

  return (
    <>
      <PageHeader
        eyebrow="Gateway clients"
        title="Projects"
        description="Projects represent applications or services that call the Conexus gateway. Issue project API keys here and give those keys to gateway clients."
      />

      {error && <ErrorState message={error} />}
      {success && <Alert tone="success">{success}</Alert>}

      <Card>
        <SectionHeader
          title="Create Project"
          description="Use clear names like app, team, or environment. Keys are managed after project creation."
        />
        <form className="stack" onSubmit={createProject}>
          <FormRow>
            <Field label="Project name" hint="Example: payments-prod">
              <Input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="payments"
              />
            </Field>
          </FormRow>
          <div className="inline-actions">
            <Button type="submit" disabled={creatingProject}>
              {creatingProject ? "Creating..." : "Create project"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <SectionHeader
          title="Project List"
          description="Select a project to inspect and manage its gateway API keys."
        />
        {loadingProjects ? (
          <LoadingState label="Loading projects..." />
        ) : projects.length === 0 ? (
          <EmptyState title="No projects yet">
            Create a project to start issuing API keys for gateway clients.
          </EmptyState>
        ) : (
          <Table aria-label="Projects">
            <thead>
              <tr>
                <th>Name</th>
                <th>Active keys</th>
                <th>Total requests</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr
                  key={project.id}
                  className={project.id === selectedProjectId ? "row-muted" : undefined}
                >
                  <td>{project.name}</td>
                  <td>{project.active_key_count}</td>
                  <td>{project.total_request_count}</td>
                  <td>{formatDate(project.created_at)}</td>
                  <td>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => setSelectedProjectId(project.id)}
                    >
                      {project.id === selectedProjectId ? "Selected" : "Manage keys"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card>
        <SectionHeader
          title="Project API Keys"
          description={
            selectedProject
              ? `Keys for ${selectedProject.name}. Plaintext keys are shown once immediately after creation.`
              : "Select a project to manage keys."
          }
        />
        {!selectedProjectId ? (
          <EmptyState title="Select a project">
            Project API keys authenticate gateway clients. Choose a project above to issue or revoke keys.
          </EmptyState>
        ) : (
          <>
            <form className="stack" onSubmit={issueKey}>
              <FormRow>
                <Field label="Key label" hint="Optional. Use labels like prod, staging, or CI.">
                  <Input
                  value={newKeyLabel}
                  onChange={(e) => setNewKeyLabel(e.target.value)}
                  placeholder="prod"
                  />
                </Field>
              </FormRow>
              <div className="inline-actions">
                <Button type="submit" disabled={issuingKey}>
                  {issuingKey ? "Issuing..." : "Issue key"}
                </Button>
              </div>
            </form>
            {latestIssuedKey && (
              <Alert tone="warning" title="New project API key shown once">
                <div className="stack">
                  <p>
                    Copy this key now. Conexus will only show the prefix later and the plaintext value cannot be recovered.
                  </p>
                  <pre>{latestIssuedKey.plaintext}</pre>
                  <div className="inline-actions">
                    <CopyButton value={latestIssuedKey.plaintext} label="Copy key" />
                  </div>
                </div>
              </Alert>
            )}
            {selectedProject && (
              <KeyValueGrid
                items={[
                  { label: "Project ID", value: <code>{selectedProject.id}</code> },
                  { label: "Active keys", value: selectedProject.active_key_count },
                  { label: "Total requests", value: selectedProject.total_request_count },
                ]}
              />
            )}
            <Card className="card-muted">
              <SectionHeader
                title="Project Limits"
                description="Configure protective limits to prevent accidental runaway usage. Hard limits block before provider calls; soft limits are visible-only for now."
              />
              {loadingLimitsUsage ? (
                <LoadingState label="Loading usage..." />
              ) : limitsUsage ? (
                <div className="stack" style={{ marginBottom: 12 }}>
                  <div className="muted">
                    Usage windows use UTC boundaries. Daily reset:{" "}
                    {formatDate(limitsUsage.daily.reset_at)}. Monthly reset:{" "}
                    {formatDate(limitsUsage.monthly.reset_at)}.
                  </div>

                  {loadingLimitsReservations ? (
                    <LoadingState label="Loading reservation counters..." />
                  ) : limitsReservations ? (
                    <div className="stack" style={{ marginBottom: 12 }}>
                      <div className="muted">
                        Admission counters (UTC): reserved slots vs completed for the active
                        windows. Empty until the first hard-limit gateway call creates rows.
                      </div>
                      <KeyValueGrid
                        items={[
                          {
                            label: "Daily requests (reserved / completed)",
                            value:
                              limitsReservations.daily == null
                                ? "—"
                                : `${_formatNumber(limitsReservations.daily.request_count_reserved)} / ${_formatNumber(limitsReservations.daily.request_count_completed)}`,
                          },
                          {
                            label: "Daily tokens (reserved / completed)",
                            value:
                              limitsReservations.daily == null
                                ? "—"
                                : `${_formatNumber(limitsReservations.daily.token_count_reserved)} / ${_formatNumber(limitsReservations.daily.token_count_completed)}`,
                          },
                          {
                            label: "Monthly cost (reserved / completed)",
                            value:
                              limitsReservations.monthly == null
                                ? "—"
                                : `${_formatUsd(limitsReservations.monthly.cost_reserved)} / ${_formatUsd(limitsReservations.monthly.cost_completed)}`,
                          },
                        ]}
                      />
                    </div>
                  ) : null}

                  <div className="stack">
                    {(() => {
                      const current = limitsUsage.daily.request_count;
                      const limit = limits?.daily_request_limit ?? null;
                      const pct = _percent(current, limit);
                      return (
                        <div>
                          <div className="inline-actions" style={{ justifyContent: "space-between" }}>
                            <strong>Daily requests</strong>
                            <span className="muted">
                              {_formatNumber(current)} / {limit == null ? "unlimited" : _formatNumber(limit)}
                              {pct == null ? "" : ` (${pct.toFixed(0)}%)`}
                            </span>
                          </div>
                          {pct != null ? (
                            <div
                              style={{
                                height: 8,
                                background: "var(--color-border)",
                                borderRadius: 999,
                                overflow: "hidden",
                                marginTop: 6,
                              }}
                            >
                              <div
                                style={{
                                  width: `${Math.min(100, pct)}%`,
                                  height: "100%",
                                  background:
                                    pct >= 100 ? "var(--color-danger)" : "var(--color-primary)",
                                }}
                              />
                            </div>
                          ) : null}
                        </div>
                      );
                    })()}

                    {(() => {
                      const current = limitsUsage.daily.total_tokens;
                      const limit = limits?.daily_token_limit ?? null;
                      const pct = _percent(current, limit);
                      return (
                        <div>
                          <div className="inline-actions" style={{ justifyContent: "space-between" }}>
                            <strong>Daily tokens</strong>
                            <span className="muted">
                              {_formatNumber(current)} / {limit == null ? "unlimited" : _formatNumber(limit)}
                              {pct == null ? "" : ` (${pct.toFixed(0)}%)`}
                            </span>
                          </div>
                          {pct != null ? (
                            <div
                              style={{
                                height: 8,
                                background: "var(--color-border)",
                                borderRadius: 999,
                                overflow: "hidden",
                                marginTop: 6,
                              }}
                            >
                              <div
                                style={{
                                  width: `${Math.min(100, pct)}%`,
                                  height: "100%",
                                  background:
                                    pct >= 100 ? "var(--color-danger)" : "var(--color-primary)",
                                }}
                              />
                            </div>
                          ) : null}
                        </div>
                      );
                    })()}

                    {(() => {
                      const current = limitsUsage.monthly.estimated_cost;
                      const limit = limits?.monthly_cost_limit ?? null;
                      const pct = _percent(current, limit);
                      return (
                        <div>
                          <div className="inline-actions" style={{ justifyContent: "space-between" }}>
                            <strong>Monthly cost (USD)</strong>
                            <span className="muted">
                              {_formatUsd(current)} / {limit == null ? "unlimited" : _formatUsd(limit)}
                              {pct == null ? "" : ` (${pct.toFixed(0)}%)`}
                            </span>
                          </div>
                          {pct != null ? (
                            <div
                              style={{
                                height: 8,
                                background: "var(--color-border)",
                                borderRadius: 999,
                                overflow: "hidden",
                                marginTop: 6,
                              }}
                            >
                              <div
                                style={{
                                  width: `${Math.min(100, pct)}%`,
                                  height: "100%",
                                  background:
                                    pct >= 100 ? "var(--color-danger)" : "var(--color-primary)",
                                }}
                              />
                            </div>
                          ) : null}
                        </div>
                      );
                    })()}
                  </div>
                </div>
              ) : null}
              {loadingLimits ? (
                <LoadingState label="Loading limits..." />
              ) : (
                <form className="stack" onSubmit={saveLimits}>
                  <FormRow>
                    <Field
                      label="Limit mode"
                      hint="disabled = no enforcement, soft = visible-only (M8A), hard = blocks before provider call"
                    >
                      <select
                        className="input"
                        value={limitMode}
                        onChange={(e) =>
                          setLimitMode(e.target.value as ProjectLimits["limit_mode"])
                        }
                      >
                        <option value="disabled">disabled</option>
                        <option value="soft">soft</option>
                        <option value="hard">hard</option>
                      </select>
                    </Field>
                  </FormRow>

                  <FormRow>
                    <Field
                      label="Monthly cost limit (USD)"
                      hint="Nullable. Uses UTC calendar month boundaries."
                    >
                      <Input
                        value={monthlyCostLimit}
                        onChange={(e) => setMonthlyCostLimit(e.target.value)}
                        placeholder="e.g. 25"
                      />
                    </Field>
                  </FormRow>

                  <FormRow>
                    <Field
                      label="Daily request limit"
                      hint="Nullable. Counts all gateway requests, including failed. UTC day boundaries."
                    >
                      <Input
                        value={dailyRequestLimit}
                        onChange={(e) => setDailyRequestLimit(e.target.value)}
                        placeholder="e.g. 1000"
                      />
                    </Field>
                  </FormRow>

                  <FormRow>
                    <Field
                      label="Daily token limit"
                      hint="Nullable. Sums total_tokens for the UTC day; null token rows are ignored."
                    >
                      <Input
                        value={dailyTokenLimit}
                        onChange={(e) => setDailyTokenLimit(e.target.value)}
                        placeholder="e.g. 500000"
                      />
                    </Field>
                  </FormRow>

                  <div className="inline-actions">
                    <Button type="submit" disabled={savingLimits || !selectedProjectId}>
                      {savingLimits ? "Saving..." : "Save limits"}
                    </Button>
                    {limits?.updated_at ? (
                      <span className="muted">
                        Last updated: {formatDate(limits.updated_at)}
                      </span>
                    ) : null}
                  </div>
                </form>
              )}
            </Card>
            {loadingKeys ? (
              <LoadingState label="Loading project keys..." />
            ) : keys.length === 0 ? (
              <EmptyState title="No keys for this project">
                Issue a key when a client is ready to call the gateway. Store the plaintext value outside Conexus immediately.
              </EmptyState>
            ) : (
              <Table aria-label="Project API keys">
                <thead>
                  <tr>
                    <th>Prefix</th>
                    <th>Label</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Revoked</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((key) => (
                    <tr key={key.id} className={key.revoked_at ? "row-muted" : undefined}>
                      <td><code>{key.prefix}</code></td>
                      <td>{key.label ?? "-"}</td>
                      <td>
                        <StatusBadge status={key.revoked_at ? "revoked" : "active"} />
                      </td>
                      <td>{formatDate(key.created_at)}</td>
                      <td>{formatDate(key.revoked_at)}</td>
                      <td>
                        <ConfirmAction
                          message={`Revoke key ${key.prefix}? This client will no longer be able to call the gateway with it.`}
                          onConfirm={() => void revokeKey(key.id)}
                          disabled={Boolean(key.revoked_at)}
                        >
                          {revokingKeyId === key.id ? "Revoking..." : "Revoke"}
                        </ConfirmAction>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </>
        )}
      </Card>
    </>
  );
}
