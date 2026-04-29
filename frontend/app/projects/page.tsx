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
import { BACKEND_BASE, formatDate } from "@/lib/api";
import type { ApiKeyCreated, ApiKeyRow, ProjectRow } from "@/lib/types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [projectName, setProjectName] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [keys, setKeys] = useState<ApiKeyRow[]>([]);
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [latestIssuedKey, setLatestIssuedKey] = useState<ApiKeyCreated | null>(null);
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
      const res = await fetch(`${BACKEND_BASE}/admin/projects`, {
        credentials: "include",
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
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
      const res = await fetch(`${BACKEND_BASE}/admin/projects/${projectId}/keys`, {
        credentials: "include",
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        setError("Unable to load project keys.");
        return;
      }
      setKeys((await res.json()) as ApiKeyRow[]);
    } finally {
      setLoadingKeys(false);
    }
  }

  useEffect(() => {
    void fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      setLatestIssuedKey(null);
      void fetchKeys(selectedProjectId);
    } else {
      setKeys([]);
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
      const res = await fetch(`${BACKEND_BASE}/admin/projects`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
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
      const res = await fetch(`${BACKEND_BASE}/admin/projects/${selectedProjectId}/keys`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: label || null }),
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
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
      const res = await fetch(
        `${BACKEND_BASE}/admin/projects/${selectedProjectId}/keys/${keyId}/revoke`,
        {
          method: "POST",
          credentials: "include",
        },
      );
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
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
