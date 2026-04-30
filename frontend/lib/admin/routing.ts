import { AdminResult, getAdminJson } from "@/lib/api";
import type { ProviderCandidate, RoutingPolicy } from "@/lib/types";

export function getRoutingPolicy(): Promise<AdminResult<RoutingPolicy>> {
  return getAdminJson("/admin/routing/policy");
}

export function getProviderCandidates(): Promise<AdminResult<ProviderCandidate[]>> {
  return getAdminJson("/admin/routing/provider-candidates");
}

export function getModelAliases(): Promise<AdminResult<unknown>> {
  return getAdminJson("/admin/routing/model-aliases");
}
