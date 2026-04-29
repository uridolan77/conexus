"use client";

import { useEffect, useMemo, useState } from "react";

const BACKEND_BASE =
  process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "http://localhost:8000";

type ProjectRow = {
  id: string;
  name: string;
  created_at: string;
  active_key_count: number;
  total_request_count: number;
};

type ApiKeyCreated = {
  id: string;
  project_id: string;
  label: string | null;
  prefix: string;
  created_at: string;
  revoked_at: string | null;
  plaintext: string;
};

type ChatCompletionsResponse = {
  id: string;
  model: string;
  provider: string;
  fallback_used: boolean;
  choices: Array<{
    index: number;
    message: { role: string; content: string };
    finish_reason: string;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
};

type StepResult =
  | { ok: true; data: unknown }
  | { ok: false; status?: number; error: unknown };

async function readJsonSafe(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function runStep(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<StepResult> {
  try {
    const res = await fetch(input, init);
    const data = await readJsonSafe(res);
    if (!res.ok) {
      return { ok: false, status: res.status, error: data };
    }
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : err };
  }
}

export default function SmokeTestsPage() {
  const [health, setHealth] = useState<StepResult | null>(null);
  const [session, setSession] = useState<StepResult | null>(null);
  const [projects, setProjects] = useState<StepResult | null>(null);
  const [projectRows, setProjectRows] = useState<ProjectRow[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [issuedKey, setIssuedKey] = useState<ApiKeyCreated | null>(null);

  const [chatPrompt, setChatPrompt] = useState("Say hello in one sentence.");
  const [chatModel, setChatModel] = useState("conexus-default");
  const [chat, setChat] = useState<
    | (StepResult & { requestId?: string })
    | null
  >(null);

  const sortedProjects = useMemo(
    () => [...projectRows].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [projectRows],
  );

  useEffect(() => {
    setIssuedKey(null);
    setChat(null);
  }, [selectedProjectId]);

  async function checkHealth() {
    setHealth(null);
    const result = await runStep(`${BACKEND_BASE}/health`, { cache: "no-store" });
    setHealth(result);
  }

  async function checkSession() {
    setSession(null);
    const result = await runStep(`${BACKEND_BASE}/admin/auth/session`, {
      credentials: "include",
      cache: "no-store",
    });
    setSession(result);
  }

  async function loadProjects() {
    setProjects(null);
    const result = await runStep(`${BACKEND_BASE}/admin/projects`, {
      credentials: "include",
      cache: "no-store",
    });
    setProjects(result);
    if (result.ok) {
      const rows = (result.data as ProjectRow[]) ?? [];
      setProjectRows(rows);
      if (!selectedProjectId && rows.length > 0) {
        setSelectedProjectId(rows[0].id);
      }
    }
  }

  async function issueProjectKey() {
    if (!selectedProjectId) return;
    setIssuedKey(null);
    const result = await runStep(
      `${BACKEND_BASE}/admin/projects/${selectedProjectId}/keys`,
      {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: "smoke-test" }),
      },
    );
    if (!result.ok) {
      setChat(result);
      return;
    }
    setIssuedKey(result.data as ApiKeyCreated);
  }

  async function runChatCompletion() {
    if (!issuedKey?.plaintext) return;
    setChat(null);
    const res = await fetch(`${BACKEND_BASE}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${issuedKey.plaintext}`,
      },
      body: JSON.stringify({
        model: chatModel,
        messages: [{ role: "user", content: chatPrompt }],
      }),
    });
    const requestId = res.headers.get("X-Conexus-Request-Id") ?? undefined;
    const data = await readJsonSafe(res);
    if (!res.ok) {
      setChat({ ok: false, status: res.status, error: data, requestId });
      return;
    }
    setChat({ ok: true, data, requestId });
  }

  const chatSummary = useMemo(() => {
    if (!chat?.ok) return null;
    const body = chat.data as ChatCompletionsResponse;
    const text = body.choices?.[0]?.message?.content ?? "";
    return {
      request_id: chat.requestId ?? body.id,
      provider: body.provider,
      model: body.model,
      fallback_used: body.fallback_used,
      usage: body.usage,
      text,
    };
  }, [chat]);

  return (
    <>
      <h2>Smoke Tests</h2>
      <p className="muted">
        Run a quick end-to-end check from the BO. Project API keys are shown
        only immediately after issuing and are kept in-memory only.
      </p>

      <div className="card">
        <h3>1) Backend health</h3>
        <div className="inline-actions">
          <button type="button" onClick={checkHealth}>
            Check /health
          </button>
        </div>
        {health && (
          <pre className={health.ok ? "ok" : "error"}>
            {JSON.stringify(health, null, 2)}
          </pre>
        )}
      </div>

      <div className="card">
        <h3>2) Admin session</h3>
        <div className="inline-actions">
          <button type="button" onClick={checkSession}>
            Check /admin/auth/session
          </button>
        </div>
        {session && (
          <pre className={session.ok ? "ok" : "error"}>
            {JSON.stringify(session, null, 2)}
          </pre>
        )}
      </div>

      <div className="card">
        <h3>3) Projects</h3>
        <div className="inline-actions">
          <button type="button" onClick={loadProjects}>
            Load projects
          </button>
        </div>
        {projects && (
          <pre className={projects.ok ? "ok" : "error"}>
            {JSON.stringify(projects, null, 2)}
          </pre>
        )}

        {sortedProjects.length > 0 && (
          <label>
            Select project
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              {sortedProjects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.id.slice(0, 8)})
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="card">
        <h3>4) Issue project API key</h3>
        <div className="inline-actions">
          <button
            type="button"
            onClick={issueProjectKey}
            disabled={!selectedProjectId}
          >
            Issue key
          </button>
        </div>
        {issuedKey ? (
          <div className="stack">
            <p className="muted">
              Copy this key now. It won’t be shown again.
            </p>
            <pre className="ok">{issuedKey.plaintext}</pre>
          </div>
        ) : (
          <p className="muted">No key issued yet.</p>
        )}
      </div>

      <div className="card">
        <h3>5) Test /v1/chat/completions</h3>
        <div className="stack">
          <label>
            Model
            <input value={chatModel} onChange={(e) => setChatModel(e.target.value)} />
          </label>
          <label>
            Prompt
            <textarea
              value={chatPrompt}
              onChange={(e) => setChatPrompt(e.target.value)}
              rows={3}
            />
          </label>
          <div className="inline-actions">
            <button
              type="button"
              onClick={runChatCompletion}
              disabled={!issuedKey?.plaintext}
            >
              Send test request
            </button>
          </div>
        </div>

        {chat && (
          <>
            <h4>Result</h4>
            <pre className={chat.ok ? "ok" : "error"}>
              {JSON.stringify(chat, null, 2)}
            </pre>
          </>
        )}

        {chatSummary && (
          <>
            <h4>Summary</h4>
            <dl className="kv">
              <dt>request_id</dt>
              <dd>{chatSummary.request_id}</dd>
              <dt>provider</dt>
              <dd>{chatSummary.provider}</dd>
              <dt>model</dt>
              <dd>{chatSummary.model}</dd>
              <dt>fallback_used</dt>
              <dd>{String(chatSummary.fallback_used)}</dd>
              <dt>usage</dt>
              <dd>
                <pre className="muted">{JSON.stringify(chatSummary.usage, null, 2)}</pre>
              </dd>
              <dt>text</dt>
              <dd>
                <pre className="muted">{chatSummary.text}</pre>
              </dd>
            </dl>
          </>
        )}
      </div>
    </>
  );
}

