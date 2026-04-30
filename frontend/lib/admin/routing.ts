import { AdminResult, getAdminJson } from "@/lib/api";
import type { RoutingPolicy } from "@/lib/types";
// getProviderCandidates is owned by providers.ts to avoid duplication.
export { listProviderCandidates as getProviderCandidates } from "@/lib/admin/providers";

export function getRoutingPolicy(): Promise<AdminResult<RoutingPolicy>> {
  return getAdminJson("/admin/routing/policy");
}

export function getModelAliases(): Promise<AdminResult<unknown>> {
  return getAdminJson("/admin/routing/model-aliases");
}
