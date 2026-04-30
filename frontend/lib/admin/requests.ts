import { AdminResult, buildQuery, getAdminJson } from "@/lib/api";
import type { RequestDetail, RequestListResponse } from "@/lib/types";

export type RequestListParams = {
  limit?: number;
  offset?: number;
  request_id?: string;
  project_id?: string;
  api_key_id?: string;
  status?: string;
  provider?: string;
  model?: string;
  requested_model?: string;
  model_search?: string;
  fallback_used?: boolean;
  error_code?: string;
  created_from?: string;
  created_to?: string;
  completed_from?: string;
  completed_to?: string;
  min_latency_ms?: number;
  max_latency_ms?: number;
  min_total_tokens?: number;
  max_total_tokens?: number;
  min_estimated_cost?: number;
  max_estimated_cost?: number;
  sort_by?: "created_at" | "completed_at" | "latency_ms" | "total_tokens" | "estimated_cost";
  sort_dir?: "asc" | "desc";
};

export function listRequests(
  params: RequestListParams = {},
): Promise<AdminResult<RequestListResponse>> {
  const qs = buildQuery({
    limit: params.limit,
    offset: params.offset,
    request_id: params.request_id,
    project_id: params.project_id,
    api_key_id: params.api_key_id,
    status: params.status,
    provider: params.provider,
    model: params.model,
    requested_model: params.requested_model,
    model_search: params.model_search,
    fallback_used: params.fallback_used,
    error_code: params.error_code,
    created_from: params.created_from,
    created_to: params.created_to,
    completed_from: params.completed_from,
    completed_to: params.completed_to,
    min_latency_ms: params.min_latency_ms,
    max_latency_ms: params.max_latency_ms,
    min_total_tokens: params.min_total_tokens,
    max_total_tokens: params.max_total_tokens,
    min_estimated_cost: params.min_estimated_cost,
    max_estimated_cost: params.max_estimated_cost,
    sort_by: params.sort_by,
    sort_dir: params.sort_dir,
  });
  return getAdminJson(`/admin/requests${qs}`);
}

export function getRequest(requestId: string): Promise<AdminResult<RequestDetail>> {
  return getAdminJson(`/admin/requests/${requestId}`);
}
