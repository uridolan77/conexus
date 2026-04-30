import { AdminResult, buildQuery, getAdminJson } from "@/lib/api";
import type { AuditListResponse } from "@/lib/types";

export type AuditListParams = {
  limit?: number;
  offset?: number;
  actor?: string;
  action?: string;
  resource_type?: string;
};

export function listAuditLogs(
  params: AuditListParams = {},
): Promise<AdminResult<AuditListResponse>> {
  const qs = buildQuery({
    limit: params.limit,
    offset: params.offset,
    actor: params.actor,
    action: params.action,
    resource_type: params.resource_type,
  });
  return getAdminJson(`/admin/audit${qs}`);
}
