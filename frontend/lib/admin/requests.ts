import { AdminResult, getAdminJson } from "@/lib/api";
import type { RequestDetail, RequestListResponse } from "@/lib/types";

export type RequestListParams = {
  limit?: number;
  offset?: number;
  project_id?: string;
  status?: string;
  sort?: string;
  order?: "asc" | "desc";
};

export function listRequests(
  params: RequestListParams = {},
): Promise<AdminResult<RequestListResponse>> {
  const q = new URLSearchParams();
  if (params.limit != null) q.set("limit", String(params.limit));
  if (params.offset != null) q.set("offset", String(params.offset));
  if (params.project_id) q.set("project_id", params.project_id);
  if (params.status) q.set("status", params.status);
  if (params.sort) q.set("sort", params.sort);
  if (params.order) q.set("order", params.order);
  const qs = q.toString();
  return getAdminJson(`/admin/requests${qs ? `?${qs}` : ""}`);
}

export function getRequest(requestId: string): Promise<AdminResult<RequestDetail>> {
  return getAdminJson(`/admin/requests/${requestId}`);
}
