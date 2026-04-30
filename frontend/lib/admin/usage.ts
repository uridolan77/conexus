import { AdminResult, getAdminJson } from "@/lib/api";
import type {
  UsageBreakdownResponse,
  UsageProjectRow,
  UsageProviderRow,
  UsageSummary,
  UsageTimeseriesResponse,
} from "@/lib/types";

export type UsageWindow = "24h" | "7d" | "30d";
export type TimeseriesInterval = "hour" | "day";

export function getUsageSummary(window: UsageWindow): Promise<AdminResult<UsageSummary>> {
  return getAdminJson(`/admin/usage/summary?window=${window}`);
}

export function getUsageByProject(
  window: UsageWindow,
): Promise<AdminResult<UsageBreakdownResponse<UsageProjectRow>>> {
  return getAdminJson(`/admin/usage/by-project?window=${window}`);
}

export function getUsageByProvider(
  window: UsageWindow,
): Promise<AdminResult<UsageBreakdownResponse<UsageProviderRow>>> {
  return getAdminJson(`/admin/usage/by-provider?window=${window}`);
}

export function getUsageTimeseries(
  window: UsageWindow,
  interval?: TimeseriesInterval,
): Promise<AdminResult<UsageTimeseriesResponse>> {
  const q = new URLSearchParams({ window });
  if (interval) q.set("interval", interval);
  return getAdminJson(`/admin/usage/timeseries?${q.toString()}`);
}
