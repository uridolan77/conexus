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

export type RequestStatusGroup = "success" | "failure" | "in_progress";

export type RequestRow = {
  id: string;
  request_id: string;
  project_id: string | null;
  project_name: string | null;
  api_key_id: string | null;
  api_key_prefix: string | null;
  requested_model: string;
  provider: string | null;
  model: string | null;
  status: string;
  latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  estimated_cost: number | null;
  fallback_used: boolean;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  duration_bucket: "fast" | "normal" | "slow" | null;
  cost_bucket: "free_or_unknown" | "low" | "medium" | "high";
};

export type RequestListResponse = {
  items: RequestRow[];
  limit: number;
  offset: number;
  total: number;
};

export type RequestDetail = RequestRow & {
  previous_request_id: string | null;
  next_request_id: string | null;
  request_age_seconds: number | null;
  completed_age_seconds: number | null;
  normalized_status_group: RequestStatusGroup;
  token_summary: {
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
  };
  cost_summary: {
    estimated_cost: number | null;
    currency: "USD";
  };
  error_summary: {
    code: string | null;
    message: string | null;
  };
  routing_summary: {
    requested_model: string;
    served_provider: string | null;
    served_model: string | null;
    fallback_used: boolean;
  };
};
