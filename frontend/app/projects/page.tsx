"use client";

import { FormEvent, useEffect, useState } from "react";

type ProjectRow = {
  id: string;
  name: string;
  created_at: string;
  active_key_count: number;
  total_request_count: number;
};

type KeyRow = {
  id: string;
  project_id: string;
  label: string | null;
  prefix: string;
  created_at: string;
  revoked_at: string | null;
};

type CreatedKey = KeyRow & { plaintext: string };

const BACKEND_BASE =
  process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://localhost:8000";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [projectName, setProjectName] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [keys, setKeys] = useState<KeyRow[]>([]);
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [latestIssuedKey, setLatestIssuedKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function fetchProjects() {
    setError(null);
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
  }

  async function fetchKeys(projectId: string) {
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
    setKeys((await res.json()) as KeyRow[]);
  }

  useEffect(() => {
    void fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      void fetchKeys(selectedProjectId);
    } else {
      setKeys([]);
    }
  }, [selectedProjectId]);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const name = projectName.trim();
    if (!name) {
      setError("Project name is required.");
      return;
    }
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
    setProjectName("");
    await fetchProjects();
  }

  async function issueKey(event: FormEvent) {
    event.preventDefault();
    if (!selectedProjectId) {
      setError("Select a project first.");
      return;
    }
    const res = await fetch(`${BACKEND_BASE}/admin/projects/${selectedProjectId}/keys`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: newKeyLabel.trim() || null }),
    });
    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!res.ok) {
      setError("Unable to issue project key.");
      return;
    }
    const created = (await res.json()) as CreatedKey;
    setLatestIssuedKey(created.plaintext);
    setNewKeyLabel("");
    await fetchKeys(selectedProjectId);
    await fetchProjects();
  }

  async function revokeKey(keyId: string) {
    if (!selectedProjectId) {
      return;
    }
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
    await fetchKeys(selectedProjectId);
    await fetchProjects();
  }

  return (
    <>
      <h2>Projects</h2>
      <p className="muted">
        Create projects, issue project API keys, and revoke keys from BO.
      </p>

      <div className="card">
        <h3>Create project</h3>
        <form className="stack" onSubmit={createProject}>
          <label>
            Project name
            <input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="payments"
            />
          </label>
          <button type="submit">Create project</button>
        </form>
      </div>

      <div className="card">
        <h3>Projects</h3>
        {error && <p className="error">{error}</p>}
        {projects.length === 0 ? (
          <p className="muted">No projects yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Active keys</th>
                <th>Total requests</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr key={project.id}>
                  <td>{project.name}</td>
                  <td>{project.active_key_count}</td>
                  <td>{project.total_request_count}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => setSelectedProjectId(project.id)}
                    >
                      Manage keys
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3>Project keys</h3>
        {!selectedProjectId ? (
          <p className="muted">Select a project to manage keys.</p>
        ) : (
          <>
            <form className="stack" onSubmit={issueKey}>
              <label>
                Key label
                <input
                  value={newKeyLabel}
                  onChange={(e) => setNewKeyLabel(e.target.value)}
                  placeholder="prod"
                />
              </label>
              <button type="submit">Issue key</button>
            </form>
            {latestIssuedKey && (
              <p>
                New key (shown once): <strong>{latestIssuedKey}</strong>
              </p>
            )}
            {keys.length === 0 ? (
              <p className="muted">No keys for this project yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Prefix</th>
                    <th>Label</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((key) => (
                    <tr key={key.id}>
                      <td>{key.prefix}</td>
                      <td>{key.label ?? "-"}</td>
                      <td>{key.revoked_at ? "revoked" : "active"}</td>
                      <td>
                        <button
                          type="button"
                          onClick={() => revokeKey(key.id)}
                          disabled={Boolean(key.revoked_at)}
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </>
  );
}
