import { BACKEND_BASE, readJsonSafe } from "@/lib/api";

export type ParseResult<T> = { ok: true; value?: T } | { ok: false };

export function parseTemperature(value: string): ParseResult<number> {
  const trimmed = value.trim();
  if (!trimmed) return { ok: true };
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return { ok: false };
  return { ok: true, value: n };
}

export function parseMaxTokens(value: string): ParseResult<number> {
  const trimmed = value.trim();
  if (!trimmed) return { ok: true };
  if (!/^\d+$/.test(trimmed)) return { ok: false };
  const n = Number(trimmed);
  if (!Number.isInteger(n) || n <= 0) return { ok: false };
  return { ok: true, value: n };
}

export type ChatCompletionMessage = {
  role: "system" | "user";
  content: string;
};

export type ChatCompletionPayload = {
  model: string;
  messages: ChatCompletionMessage[];
  temperature?: number;
  max_tokens?: number;
};

export function buildChatCompletionPayload({
  model,
  systemMessage,
  userMessage,
  temperature,
  maxTokens,
}: {
  model: string;
  systemMessage?: string;
  userMessage: string;
  temperature?: string;
  maxTokens?: string;
}): ChatCompletionPayload {
  const trimmedModel = model.trim();
  const sys = (systemMessage ?? "").trim();
  const user = userMessage.trim();

  const messages: ChatCompletionMessage[] = [];
  if (sys) messages.push({ role: "system", content: sys });
  messages.push({ role: "user", content: user });

  const payload: ChatCompletionPayload = {
    model: trimmedModel,
    messages,
  };

  const t = (temperature ?? "").trim();
  if (t) {
    const n = Number(t);
    if (Number.isFinite(n)) payload.temperature = n;
  }

  const mt = (maxTokens ?? "").trim();
  if (mt) {
    const n = Number(mt);
    if (Number.isInteger(n) && n > 0) payload.max_tokens = n;
  }

  return payload;
}

export type PlaygroundOk = {
  ok: true;
  status: number;
  requestId?: string;
  data: unknown;
};

export type PlaygroundErr = {
  ok: false;
  status: number;
  requestId?: string;
  error: unknown;
};

export type PlaygroundResult = PlaygroundOk | PlaygroundErr;

export async function sendPlaygroundChatCompletion({
  apiKey,
  payload,
  signal,
}: {
  apiKey: string;
  payload: ChatCompletionPayload;
  signal?: AbortSignal;
}): Promise<PlaygroundResult> {
  const res = await fetch(`${BACKEND_BASE}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(payload),
    signal,
  });

  const requestId = res.headers.get("X-Conexus-Request-Id") ?? undefined;
  const data = await readJsonSafe(res);

  if (!res.ok) {
    return { ok: false, status: res.status, requestId, error: data };
  }
  return { ok: true, status: res.status, requestId, data };
}

