"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CopyButton,
  EmptyState,
  ErrorState,
  Field,
  FormRow,
  Input,
  JsonBlock,
  KeyValueGrid,
  LinkButton,
  PageHeader,
  SectionHeader,
  Select,
  Stepper,
  Textarea,
} from "@/components/ui";
import { BACKEND_BASE, formatApiError, readJsonSafe } from "@/lib/api";
import type {
  ApiKeyCreated,
  ChatCompletionsResponse,
  ProjectRow,
  StepResult,
  StepStatus,
} from "@/lib/types";

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
  const [runningStep, setRunningStep] = useState<string | null>(null);
  // Project API key plaintext is intentionally kept in-memory only (React state)
  // and never persisted or logged. It is displayed once immediately after issuance.
  const [issuedKey, setIssuedKey] = useState<ApiKeyCreated | null>(null);
  const [keyError, setKeyError] = useState<StepResult | null>(null);

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
    setKeyError(null);
    setChat(null);
  }, [selectedProjectId]);

  function statusFor(result: StepResult | null, stepId: string): StepStatus {
    if (runningStep === stepId) return "running";
    if (!result) return "not-run";
    return result.ok ? "passed" : "failed";
  }

  async function checkHealth() {
    setRunningStep("health");
    setHealth(null);
    const result = await runStep(`${BACKEND_BASE}/health`, { cache: "no-store" });
    setHealth(result);
    setRunningStep(null);
  }

  async function checkSession() {
    setRunningStep("session");
    setSession(null);
    const result = await runStep(`${BACKEND_BASE}/admin/auth/session`, {
      credentials: "include",
      cache: "no-store",
    });
    setSession(result);
    setRunningStep(null);
  }

  async function loadProjects() {
    setRunningStep("projects");
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
    setRunningStep(null);
  }

  async function issueProjectKey() {
    if (!selectedProjectId) return;
    setRunningStep("key");
    setIssuedKey(null);
    setKeyError(null);
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
      setKeyError(result);
      setRunningStep(null);
      return;
    }
    setIssuedKey(result.data as ApiKeyCreated);
    setRunningStep(null);
  }

  async function runChatCompletion() {
    if (!issuedKey?.plaintext) return;
    setRunningStep("chat");
    setChat(null);
    try {
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
    } finally {
      setRunningStep(null);
    }
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

  const steps = [
    {
      label: "Backend health",
      status: statusFor(health, "health"),
      detail: "Confirms FastAPI is reachable.",
    },
    {
      label: "Admin session",
      status: statusFor(session, "session"),
      detail: "Confirms the BO auth cookie is valid.",
    },
    {
      label: "Load projects",
      status: statusFor(projects, "projects"),
      detail: "Finds a gateway client project.",
    },
    {
      label: "Select project",
      status: selectedProjectId ? "passed" : "not-run",
      detail: selectedProjectId || "Required before issuing a key.",
    },
    {
      label: "Issue temporary project API key",
      status: runningStep === "key" ? "running" : issuedKey ? "passed" : keyError ? "failed" : "not-run",
      detail: "Key remains only in memory in this page.",
    },
    {
      label: "Send chat completion",
      status: statusFor(chat, "chat"),
      detail: "Calls /v1/chat/completions with the issued key.",
    },
    {
      label: "View response summary",
      status: chatSummary ? "passed" : chat?.ok === false ? "failed" : "not-run",
      detail: "Shows request, provider, model, tokens, and text.",
    },
  ] satisfies Array<{ label: string; status: StepStatus; detail: string }>;

  return (
    <>
      <PageHeader
        eyebrow="Diagnostics"
        title="Smoke Tests"
        description="Run a guided end-to-end check from backend health through a real chat completion. Temporary project API keys are shown once and kept in memory only."
      />

      <Card>
        <SectionHeader
          title="Diagnostic Checklist"
          description="Run the steps in order. Later steps stay disabled until their dependencies are ready."
        />
        <Stepper steps={steps} />
      </Card>

      <Card>
        <SectionHeader title="1. Backend Health" description="Checks the public health endpoint." />
        <Button type="button" onClick={checkHealth} disabled={runningStep === "health"}>
          {runningStep === "health" ? "Checking..." : "Check backend health"}
        </Button>
        {health?.ok === false && <ErrorState message={formatApiError(health.error)} />}
        {health && <JsonBlock value={health} />}
      </Card>

      <Card>
        <SectionHeader title="2. Admin Session" description="Verifies the current admin session cookie." />
        <Button type="button" onClick={checkSession} disabled={runningStep === "session"}>
          {runningStep === "session" ? "Checking..." : "Check admin session"}
        </Button>
        {session?.ok === false && <ErrorState message={formatApiError(session.error)} />}
        {session && <JsonBlock value={session} />}
      </Card>

      <Card>
        <SectionHeader title="3. Projects" description="Loads existing projects so the smoke test can issue a project API key." />
        <Button type="button" onClick={loadProjects} disabled={runningStep === "projects"}>
          {runningStep === "projects" ? "Loading..." : "Load projects"}
        </Button>
        {projects?.ok === false && <ErrorState message={formatApiError(projects.error)} />}
        {projects && <JsonBlock value={projects} />}

        {sortedProjects.length > 0 ? (
          <Field label="Select project" hint="A temporary key will be issued for this project.">
            <Select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              {sortedProjects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.id.slice(0, 8)})
                </option>
              ))}
            </Select>
          </Field>
        ) : (
          projects?.ok && (
            <EmptyState title="No projects found">
              Create a project before running the gateway chat completion smoke test.
            </EmptyState>
          )
        )}
      </Card>

      <Card>
        <SectionHeader
          title="4. Issue Temporary Project API Key"
          description="The key is intentionally short-lived operationally: copy it for this test, then revoke it from Projects if needed."
        />
        <Button
          type="button"
          onClick={issueProjectKey}
          disabled={!selectedProjectId || runningStep === "key"}
        >
          {runningStep === "key" ? "Issuing..." : "Issue temporary key"}
        </Button>
        {keyError?.ok === false && <ErrorState message={formatApiError(keyError.error)} />}
        {issuedKey ? (
          <Alert tone="warning" title="Project API key shown once">
            <div className="stack">
              <p>Copy this key now. It is only stored in React state on this page and will not be shown again.</p>
              <pre>{issuedKey.plaintext}</pre>
              <div className="inline-actions">
                <CopyButton value={issuedKey.plaintext} label="Copy key" />
              </div>
            </div>
          </Alert>
        ) : (
          <p className="muted">No temporary key issued yet.</p>
        )}
      </Card>

      <Card>
        <SectionHeader
          title="5. Send Chat Completion"
          description="Calls the gateway using the temporary project API key."
        />
        <div className="stack">
          <FormRow>
            <Field label="Model">
              <Input value={chatModel} onChange={(e) => setChatModel(e.target.value)} />
            </Field>
          </FormRow>
          <Field label="Prompt">
            <Textarea
              value={chatPrompt}
              onChange={(e) => setChatPrompt(e.target.value)}
              rows={3}
            />
          </Field>
          <div className="inline-actions">
            <Button
              type="button"
              onClick={runChatCompletion}
              disabled={!issuedKey?.plaintext || runningStep === "chat"}
            >
              {runningStep === "chat" ? "Sending..." : "Send test request"}
            </Button>
          </div>
        </div>

        {!issuedKey && (
          <Alert tone="info">Issue a temporary project API key before sending a chat completion.</Alert>
        )}
        {chat?.ok === false && <ErrorState message={formatApiError(chat.error)} />}
        {chatSummary && (
          <Card className="card-muted">
            <SectionHeader title="Response Summary" />
            <KeyValueGrid
              items={[
                {
                  label: "request_id",
                  value: (
                    <span className="inline-actions">
                      <code className="wrap-anywhere">{chatSummary.request_id}</code>
                      <CopyButton value={chatSummary.request_id} />
                      <LinkButton
                        href={`/requests?request_id=${encodeURIComponent(chatSummary.request_id)}`}
                      >
                        View request
                      </LinkButton>
                    </span>
                  ),
                },
                { label: "provider", value: chatSummary.provider },
                { label: "model", value: chatSummary.model },
                { label: "fallback_used", value: String(chatSummary.fallback_used) },
                { label: "prompt_tokens", value: chatSummary.usage.prompt_tokens },
                { label: "completion_tokens", value: chatSummary.usage.completion_tokens },
                { label: "total_tokens", value: chatSummary.usage.total_tokens },
                { label: "response text", value: <pre>{chatSummary.text}</pre> },
              ]}
            />
          </Card>
        )}
        {chat && <JsonBlock value={chat} title="Raw chat result" />}
      </Card>
    </>
  );
}

