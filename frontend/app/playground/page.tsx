"use client";

import { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CopyButton,
  ErrorState,
  Field,
  FieldError,
  FormRow,
  HelpText,
  InlineCode,
  JsonBlock,
  KeyValueGrid,
  PageHeader,
  SectionHeader,
  Textarea,
  Input,
} from "@/components/ui";
import { formatApiError } from "@/lib/api";
import { formatTokens } from "@/lib/format";
import {
  buildChatCompletionPayload,
  sendPlaygroundChatCompletion,
  type PlaygroundResult,
} from "@/lib/admin/playground";
import type { ChatCompletionsResponse } from "@/lib/types";
import type { ReactNode } from "react";

function safeString(value: unknown): string | null {
  if (typeof value === "string") return value;
  if (value instanceof Error) return value.message;
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const detail = obj.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      const d = detail as Record<string, unknown>;
      if (typeof d.message === "string") return d.message;
    }
  }
  return null;
}

function redactApiKey(text: string, apiKey: string) {
  if (!apiKey) return text;
  return text.split(apiKey).join("[REDACTED]");
}

function redactSecretsDeep(value: unknown, secrets: string[]): unknown {
  const activeSecrets = secrets.map((s) => s.trim()).filter(Boolean);
  if (activeSecrets.length === 0) return value;

  const seen = new WeakMap<object, unknown>();

  function redactString(text: string) {
    return activeSecrets.reduce(
      (acc, secret) => acc.split(secret).join("[REDACTED]"),
      text,
    );
  }

  function visit(v: unknown): unknown {
    if (typeof v === "string") return redactString(v);
    if (v == null) return v;
    if (typeof v !== "object") return v;

    const obj = v as object;
    const cached = seen.get(obj);
    if (cached !== undefined) return cached;

    if (Array.isArray(v)) {
      const out: unknown[] = [];
      seen.set(obj, out);
      for (const item of v) out.push(visit(item));
      return out;
    }

    const rec = v as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    seen.set(obj, out);
    for (const [k, val] of Object.entries(rec)) {
      out[k] = visit(val);
    }
    return out;
  }

  try {
    return visit(value);
  } catch {
    return value;
  }
}

type UsageTokens = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
};

function isUsageTokens(value: unknown): value is UsageTokens {
  if (!value || typeof value !== "object") return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.prompt_tokens === "number" &&
    typeof obj.completion_tokens === "number" &&
    typeof obj.total_tokens === "number"
  );
}

function renderTokens(value: number | null): ReactNode {
  if (value == null) return <span className="muted">—</span>;
  return formatTokens(value);
}

function parseTemperature(value: string): { ok: true; value?: number } | { ok: false } {
  const trimmed = value.trim();
  if (!trimmed) return { ok: true };
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return { ok: false };
  return { ok: true, value: n };
}

function parseMaxTokens(value: string): { ok: true; value?: number } | { ok: false } {
  const trimmed = value.trim();
  if (!trimmed) return { ok: true };
  if (!/^\d+$/.test(trimmed)) return { ok: false };
  const n = Number(trimmed);
  if (!Number.isInteger(n) || n <= 0) return { ok: false };
  return { ok: true, value: n };
}

export default function PlaygroundPage() {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState("conexus-fast");
  const [systemMessage, setSystemMessage] = useState("");
  const [userMessage, setUserMessage] = useState("Say hello in one sentence.");
  const [temperature, setTemperature] = useState("");
  const [maxTokens, setMaxTokens] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<PlaygroundResult | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const payload = useMemo(
    () =>
      buildChatCompletionPayload({
        model,
        systemMessage,
        userMessage,
        temperature,
        maxTokens,
      }),
    [model, systemMessage, userMessage, temperature, maxTokens],
  );

  const keyIsEmpty = apiKey.trim().length === 0;
  const modelIsEmpty = model.trim().length === 0;
  const userIsEmpty = userMessage.trim().length === 0;

  const temperatureParsed = useMemo(() => parseTemperature(temperature), [temperature]);
  const maxTokensParsed = useMemo(() => parseMaxTokens(maxTokens), [maxTokens]);
  const temperatureInvalid = !temperatureParsed.ok;
  const maxTokensInvalid = !maxTokensParsed.ok;

  const canSend =
    !submitting &&
    !keyIsEmpty &&
    !modelIsEmpty &&
    !userIsEmpty &&
    !temperatureInvalid &&
    !maxTokensInvalid;

  const summary = useMemo(() => {
    if (!result?.ok) return null;
    const body = result.data as Partial<ChatCompletionsResponse> | null;
    const id = typeof body?.id === "string" ? body.id : null;
    const provider = typeof body?.provider === "string" ? body.provider : null;
    const servedModel = typeof body?.model === "string" ? body.model : null;
    const fallbackUsed =
      typeof body?.fallback_used === "boolean" ? body.fallback_used : null;
    const usage = body?.usage ?? null;
    const assistantText =
      body?.choices?.[0]?.message?.content &&
      typeof body.choices[0].message.content === "string"
        ? body.choices[0].message.content
        : "";
    return {
      status: result.status,
      requestId: result.requestId,
      id,
      provider,
      servedModel,
      fallbackUsed,
      usage,
      assistantText,
    };
  }, [result]);

  async function send() {
    setFormError(null);
    setResult(null);

    const trimmedKey = apiKey.trim();
    if (!trimmedKey) {
      setFormError("Project API key is required.");
      return;
    }
    if (modelIsEmpty) {
      setFormError("Model is required.");
      return;
    }
    if (userIsEmpty) {
      setFormError("User message is required.");
      return;
    }
    if (temperatureInvalid) {
      setFormError("Temperature must be a finite number (or empty).");
      return;
    }
    if (maxTokensInvalid) {
      setFormError("Max tokens must be a positive integer (or empty).");
      return;
    }

    setSubmitting(true);
    try {
      const res = await sendPlaygroundChatCompletion({
        apiKey: trimmedKey,
        payload,
      });
      setResult(res);
    } catch (err) {
      setResult({ ok: false, status: 0, error: err });
    } finally {
      setSubmitting(false);
    }
  }

  function clearKey() {
    setApiKey("");
    setShowKey(false);
  }

  const normalizedError = useMemo(() => {
    if (!result || result.ok) return null;
    const msg = safeString(result.error) ?? formatApiError(result.error);
    return redactApiKey(msg, apiKey.trim());
  }, [result, apiKey]);

  const safeRawValue = useMemo(() => {
    if (!result) return null;
    const trimmedKey = apiKey.trim();
    return redactSecretsDeep(result, trimmedKey ? [trimmedKey] : []);
  }, [result, apiKey]);

  return (
    <>
      <PageHeader
        eyebrow="Gateway"
        title="Playground"
        description={
          <>
            Send a non-streaming <InlineCode>POST /v1/chat/completions</InlineCode>{" "}
            request using a pasted Project API key. Keys are kept in memory only and
            never persisted.
          </>
        }
        actions={
          <Button type="button" variant="secondary" onClick={() => setResult(null)} disabled={submitting}>
            Clear result
          </Button>
        }
      />

      <Card>
        <SectionHeader
          title="Request"
          description="Paste a Project API key and send a single non-streaming chat completion."
        />

        {formError && <ErrorState message={formError} />}

        <div className="stack">
          <Field
            label="Project API key"
            hint={
              <span className="inline-actions">
                <HelpText>
                  Paste only. This page does not use localStorage/sessionStorage.
                </HelpText>
              </span>
            }
          >
            <Input
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="cx_live_..."
              autoComplete="off"
              spellCheck={false}
            />
          </Field>
          <div className="inline-actions">
            <Button type="button" variant="secondary" onClick={() => setShowKey((v) => !v)} disabled={keyIsEmpty}>
              {showKey ? "Hide key" : "Show key"}
            </Button>
            <Button type="button" variant="secondary" onClick={clearKey} disabled={keyIsEmpty}>
              Clear key
            </Button>
          </div>

          <FormRow>
            <Field label="Model">
              <Input value={model} onChange={(e) => setModel(e.target.value)} />
              {modelIsEmpty && <FieldError>Model is required.</FieldError>}
            </Field>
          </FormRow>

          <Field label="System message (optional)">
            <Textarea
              value={systemMessage}
              onChange={(e) => setSystemMessage(e.target.value)}
              rows={3}
              placeholder="You are a helpful assistant."
            />
          </Field>

          <Field label="User message">
            <Textarea
              value={userMessage}
              onChange={(e) => setUserMessage(e.target.value)}
              rows={4}
            />
            {userIsEmpty && <FieldError>User message is required.</FieldError>}
          </Field>

          <FormRow>
            <Field label="Temperature (optional)" hint="Must be a valid number.">
              <Input
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                inputMode="decimal"
                placeholder="0.2"
              />
              {temperatureInvalid && (
                <FieldError>Temperature must be a finite number.</FieldError>
              )}
            </Field>
            <Field label="Max tokens (optional)" hint="Must be a positive integer.">
              <Input
                value={maxTokens}
                onChange={(e) => setMaxTokens(e.target.value)}
                inputMode="numeric"
                placeholder="256"
              />
              {maxTokensInvalid && (
                <FieldError>Max tokens must be a positive integer.</FieldError>
              )}
            </Field>
          </FormRow>

          <Alert tone="info">
            Streaming playground mode is not implemented yet. Non-streaming requests
            are supported.
          </Alert>

          <div className="inline-actions">
            <Button type="button" onClick={send} disabled={!canSend}>
              {submitting ? "Sending..." : "Send request"}
            </Button>
          </div>
        </div>
      </Card>

      {result && (
        <Card>
          <SectionHeader title="Result" description="Summary and raw response for debugging." />

          {result.ok === false && (
            <>
              <ErrorState message={normalizedError ?? "Request failed."} />
              <div className="stack">
                <KeyValueGrid
                  items={[
                    { label: "http_status", value: String(result.status) },
                    {
                      label: "request_id",
                      value: result.requestId ? (
                        <span className="inline-actions">
                          <code className="wrap-anywhere">{result.requestId}</code>
                          <CopyButton value={result.requestId} />
                        </span>
                      ) : (
                        <span className="muted">not provided</span>
                      ),
                    },
                  ]}
                />
                <Alert tone="warning" title="Troubleshooting">
                  <ul>
                    <li>Check the Project API key is correct and not revoked.</li>
                    <li>Check provider configuration.</li>
                    <li>Check the model alias exists.</li>
                    <li>Check backend logs for the request id (if present).</li>
                  </ul>
                </Alert>
              </div>
            </>
          )}

          {summary && (
            <div className="stack">
              <KeyValueGrid
                items={[
                  { label: "http_status", value: String(summary.status) },
                  {
                    label: "request_id",
                    value: summary.requestId ? (
                      <span className="inline-actions">
                        <code className="wrap-anywhere">{summary.requestId}</code>
                        <CopyButton value={summary.requestId} />
                      </span>
                    ) : (
                      <span className="muted">not provided</span>
                    ),
                  },
                  { label: "response_id", value: summary.id ?? <span className="muted">unknown</span> },
                  { label: "provider", value: summary.provider ?? <span className="muted">unknown</span> },
                  { label: "model", value: summary.servedModel ?? <span className="muted">unknown</span> },
                  {
                    label: "fallback_used",
                    value:
                      summary.fallbackUsed === null ? (
                        <span className="muted">unknown</span>
                      ) : (
                        String(summary.fallbackUsed)
                      ),
                  },
                  {
                    label: "prompt_tokens",
                    value:
                      summary.usage && isUsageTokens(summary.usage)
                        ? renderTokens(summary.usage.prompt_tokens)
                        : <span className="muted">unknown</span>,
                  },
                  {
                    label: "completion_tokens",
                    value:
                      summary.usage && isUsageTokens(summary.usage)
                        ? renderTokens(summary.usage.completion_tokens)
                        : <span className="muted">unknown</span>,
                  },
                  {
                    label: "total_tokens",
                    value:
                      summary.usage && isUsageTokens(summary.usage)
                        ? renderTokens(summary.usage.total_tokens)
                        : <span className="muted">unknown</span>,
                  },
                  { label: "assistant_message", value: <pre>{summary.assistantText}</pre> },
                ]}
              />
            </div>
          )}

          {safeRawValue != null ? (
            <JsonBlock value={safeRawValue} title="Raw JSON" defaultOpen={false} />
          ) : null}
        </Card>
      )}
    </>
  );
}

