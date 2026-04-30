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
import {
  buildChatCompletionPayload,
  sendPlaygroundChatCompletion,
  type PlaygroundResult,
} from "@/lib/admin/playground";
import type { ChatCompletionsResponse } from "@/lib/types";

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

  const canSend = !submitting && !keyIsEmpty && !modelIsEmpty && !userIsEmpty;

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
    if (!trimmedKey) return result;

    if (result.ok) {
      // Ensure we never accidentally include the key in a debug block
      return result;
    }

    const errStr = safeString(result.error);
    if (!errStr) return result;

    return {
      ...result,
      error: redactApiKey(errStr, trimmedKey),
    };
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
              placeholder="cnx_..."
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
            </Field>
            <Field label="Max tokens (optional)" hint="Must be a positive integer.">
              <Input
                value={maxTokens}
                onChange={(e) => setMaxTokens(e.target.value)}
                inputMode="numeric"
                placeholder="256"
              />
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
                      summary.usage && typeof (summary.usage as any).prompt_tokens === "number"
                        ? (summary.usage as any).prompt_tokens
                        : <span className="muted">unknown</span>,
                  },
                  {
                    label: "completion_tokens",
                    value:
                      summary.usage && typeof (summary.usage as any).completion_tokens === "number"
                        ? (summary.usage as any).completion_tokens
                        : <span className="muted">unknown</span>,
                  },
                  {
                    label: "total_tokens",
                    value:
                      summary.usage && typeof (summary.usage as any).total_tokens === "number"
                        ? (summary.usage as any).total_tokens
                        : <span className="muted">unknown</span>,
                  },
                  { label: "assistant_message", value: <pre>{summary.assistantText}</pre> },
                ]}
              />
            </div>
          )}

          {safeRawValue && <JsonBlock value={safeRawValue} title="Raw JSON" defaultOpen={false} />}
        </Card>
      )}
    </>
  );
}

