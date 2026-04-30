import { AdminResult, getAdminJson, postAdminJson } from "@/lib/api";
import type { ProviderCandidate, ProviderRow, ProviderTestResult } from "@/lib/types";

export type CreateProviderPayload = {
  provider: "openai" | "anthropic";
  label?: string | null;
  api_key: string;
};

export function listProviders(): Promise<AdminResult<ProviderRow[]>> {
  return getAdminJson("/admin/providers");
}

export function createProvider(
  payload: CreateProviderPayload,
): Promise<AdminResult<ProviderRow>> {
  return postAdminJson("/admin/providers", payload);
}

export function revokeProvider(providerId: string): Promise<AdminResult<void>> {
  return postAdminJson(`/admin/providers/${providerId}/revoke`, {});
}

export function testProvider(providerId: string): Promise<AdminResult<ProviderTestResult>> {
  return postAdminJson(`/admin/providers/${providerId}/test`, {});
}

export function listProviderCandidates(): Promise<AdminResult<ProviderCandidate[]>> {
  return getAdminJson("/admin/routing/provider-candidates");
}
