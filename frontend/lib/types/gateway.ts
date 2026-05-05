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

export type ProjectLimits = {
  project_id: string;
  limit_mode: "disabled" | "soft" | "hard";
  monthly_cost_limit: number | null;
  daily_request_limit: number | null;
  daily_token_limit: number | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ProjectLimitsUsage = {
  project_id: string;
  now: string;
  daily: {
    window: "utc_day";
    start_at: string;
    reset_at: string;
    request_count: number;
    total_tokens: number;
  };
  monthly: {
    window: "utc_month";
    start_at: string;
    reset_at: string;
    estimated_cost: number;
    currency: "USD";
  };
};

/** Stale unreconciled limit reservations (v0.8 repair). */
export type StaleReservationItem = {
  reservation_id: string;
  project_id: string;
  created_at: string;
  age_seconds: number;
  daily_window_id: string;
  monthly_window_id: string | null;
  request_slots: number;
  tokens_reserved: number;
  cost_reserved: number;
  gateway_request_id: string | null;
  gateway_request_status: string | null;
  gateway_request_completed_at: string | null;
  repair_kind: string;
  recommended_action: string;
};

export type StaleReservationsList = {
  now: string;
  older_than_seconds: number;
  total_count: number;
  oldest_age_seconds: number | null;
  items: StaleReservationItem[];
};

export type ReservationRepairResponse = {
  reservation_id: string;
  project_id: string;
  repair_kind: string;
  action: string;
  applied: boolean;
  message: string;
  before: unknown;
  after: unknown;
};

/** Current UTC usage-window counters (v0.7 admission). */
export type ProjectLimitsReservations = {
  project_id: string;
  now: string;
  daily: {
    window_start: string;
    window_end: string;
    request_count_reserved: number;
    request_count_completed: number;
    token_count_reserved: number;
    token_count_completed: number;
  } | null;
  monthly: {
    window_start: string;
    window_end: string;
    cost_reserved: number;
    cost_completed: number;
  } | null;
};

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

export type UsageSummary = {
  window: "24h" | "7d" | "30d";
  created_from: string;
  created_to: string;
  currency: "USD";
  total_requests: number;
  completed_requests: number;
  failed_requests: number;
  success_rate: number;
  fallback_count: number;
  fallback_rate: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  estimated_cost: number;
  avg_latency_ms: number | null;
};

export type DashboardLatestError = {
  request_id: string;
  project_id: string | null;
  project_name: string | null;
  requested_model: string;
  provider: string | null;
  model: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
};

export type DashboardSummary = {
  requests_today: number;
  success_rate: number;
  failed_requests: number;
  average_latency_ms: number | null;
  estimated_cost_today: number;
  latest_errors: DashboardLatestError[];
};

type UsageSummaryMetrics = {
  total_requests: number;
  completed_requests: number;
  failed_requests: number;
  success_rate: number;
  fallback_count: number;
  fallback_rate: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  estimated_cost: number;
  avg_latency_ms: number | null;
};

export type UsageProjectRow = UsageSummaryMetrics & {
  project_id: string | null;
  project_name: string | null;
};

export type UsageProviderRow = UsageSummaryMetrics & {
  provider: string | null;
};

export type UsageBreakdownResponse<T> = {
  window: "24h" | "7d" | "30d";
  created_from: string;
  created_to: string;
  currency: "USD";
  items: T[];
};

export type UsageTimeseriesPoint = UsageSummaryMetrics & {
  bucket_start: string;
  bucket_end: string;
};

export type UsageTimeseriesResponse = {
  window: "24h" | "7d" | "30d";
  created_from: string;
  created_to: string;
  interval: "hour" | "day";
  currency: "USD";
  items: UsageTimeseriesPoint[];
};

export type RoutingPolicy = {
  id: string;
  name: string;
  mode: string;
  default_alias: string;
  aliases: Array<{
    alias: string;
    primary_provider: string;
    primary_model: string;
    fallback_provider: string;
    fallback_model: string;
  }>;
  direct_routes: Array<{
    provider: string;
    model_prefixes: string[];
    fallback_enabled: boolean;
  }>;
};

export type ProviderCandidate = {
  provider: string;
  source: "bo_config" | "env";
  config_id: string | null;
  label: string | null;
  key_mask: string | null;
  is_active: boolean;
  last_test_status: string | null;
  last_tested_at: string | null;
};

export type GatewayAdapterProfileRow = {
  gateway_profile_id: string;
  adapter_profile_id: string;
  domain_key: string;
  status: string;
  composite_score: number | null;
  profile_version: string | null;
  evidence_hash: string | null;
  semantic_context_hash: string | null;
  slod_model_version: string | null;
  created_at: string;
};

export type GatewayAdapterProfileDetail = GatewayAdapterProfileRow & {
  source_run_id: string | null;
  source_plan_id: string | null;
  metadata: unknown | null;
  updated_at: string;
  published_at: string | null;
};

export type GatewayAdapterProfileActivationRow = {
  id: string;
  domain_key: string;
  gateway_profile_id: string;
  status: string;
  canary_percent: number | null;
  previous_gateway_profile_id: string | null;
  created_at: string;
  activated_at: string | null;
  promoted_at: string | null;
  rolled_back_at: string | null;
  metadata: unknown | null;
};

export type GatewayAdapterProfileListResponse = {
  items: GatewayAdapterProfileRow[];
  limit: number;
  offset: number;
  total: number;
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

export type AuditLogItem = {
  id: string;
  actor_admin_user_id: string | null;
  actor_username: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  metadata: unknown | null;
  created_at: string;
};

export type AuditListResponse = {
  items: AuditLogItem[];
  limit: number;
  offset: number;
  total: number;
};
