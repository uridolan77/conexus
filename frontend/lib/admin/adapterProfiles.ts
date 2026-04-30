import { AdminResult, buildQuery, getAdminJson } from "@/lib/api";
import type {
  GatewayAdapterProfileActivationRow,
  GatewayAdapterProfileDetail,
  GatewayAdapterProfileListResponse,
} from "@/lib/types";

export type AdapterProfilesListParams = {
  limit?: number;
  offset?: number;
};

export function listAdapterProfiles(
  params: AdapterProfilesListParams = {},
): Promise<AdminResult<GatewayAdapterProfileListResponse>> {
  const qs = buildQuery({ limit: params.limit, offset: params.offset });
  return getAdminJson(`/admin/adapter-profiles${qs}`);
}

export function getAdapterProfile(
  gatewayProfileId: string,
): Promise<AdminResult<GatewayAdapterProfileDetail>> {
  return getAdminJson(`/admin/adapter-profiles/${encodeURIComponent(gatewayProfileId)}`);
}

export function listAdapterProfileActivations(
  gatewayProfileId: string,
): Promise<AdminResult<GatewayAdapterProfileActivationRow[]>> {
  return getAdminJson(
    `/admin/adapter-profiles/${encodeURIComponent(gatewayProfileId)}/activations`,
  );
}

