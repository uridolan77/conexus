import { AdminResult, getAdminJson } from "@/lib/api";
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
  const q = new URLSearchParams();
  if (params.limit != null) q.set("limit", String(params.limit));
  if (params.offset != null) q.set("offset", String(params.offset));
  if (params.actor) q.set("actor", params.actor);
  if (params.action) q.set("action", params.action);
  if (params.resource_type) q.set("resource_type", params.resource_type);
  const qs = q.toString();
  return getAdminJson(`/admin/audit${qs ? `?${qs}` : ""}`);
}
