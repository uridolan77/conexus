import { AdminResult, buildQuery, getAdminJson } from "@/lib/api";
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
  const qs = buildQuery({
    limit: params.limit,
    offset: params.offset,
    project_id: params.project_id,
    status: params.status,
    sort: params.sort,
    order: params.order,
  });
  return getAdminJson(`/admin/requests${qs}`);
}

export function getRequest(requestId: string): Promise<AdminResult<RequestDetail>> {
  return getAdminJson(`/admin/requests/${requestId}`);
}
