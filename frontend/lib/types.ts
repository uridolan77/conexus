export type ProjectRow = {
  id: string;
  name: string;
  created_at: string;
  active_key_count: number;
  total_request_count: number;
};

export type ApiKeyRow = {
  id: string;
  project_id: string;
  label: string | null;
  prefix: string;
  created_at: string;
  revoked_at: string | null;
};

export type ApiKeyCreated = ApiKeyRow & { plaintext: string };

export type ProviderRow = {
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

export type ProviderTestResult = {
  status: string;
  latency_ms: number;
  error: string | null;
};

export type ChatCompletionsResponse = {
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

export type StepStatus = "not-run" | "running" | "passed" | "failed";

export type StepResult =
  | { ok: true; data: unknown }
  | { ok: false; status?: number; error: unknown };
