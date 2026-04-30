import { AdminResult, buildQuery, getAdminJson } from "@/lib/api";
import type { AuditListResponse } from "@/lib/types";

export type AuditListParams = {
  limit?: number;
  offset?: number;
  actor_admin_user_id?: string;
  actor_username?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string;
  created_from?: string;
  created_to?: string;
};

export function listAuditLogs(
  params: AuditListParams = {},
): Promise<AdminResult<AuditListResponse>> {
  const qs = buildQuery({
    limit: params.limit,
    offset: params.offset,
    actor_admin_user_id: params.actor_admin_user_id,
    actor_username: params.actor_username,
    action: params.action,
    resource_type: params.resource_type,
    resource_id: params.resource_id,
    created_from: params.created_from,
    created_to: params.created_to,
  });
  return getAdminJson(`/admin/audit${qs}`);
}
