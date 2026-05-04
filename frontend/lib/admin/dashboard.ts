import { AdminResult, getAdminJson } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";

export function getDashboardSummary(): Promise<AdminResult<DashboardSummary>> {
  return getAdminJson("/admin/dashboard/summary");
}
