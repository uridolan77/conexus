import {
  AdminResult,
  deleteAdminJson,
  getAdminJson,
  postAdminJson,
  putAdminJson,
} from "@/lib/api";
import type {
  ApiKeyCreated,
  ApiKeyRow,
  ProjectLimits,
  ProjectLimitsReservations,
  ProjectLimitsUsage,
  ProjectRow,
  StaleReservationsList,
} from "@/lib/types";

export type SaveLimitsPayload = {
  limit_mode: ProjectLimits["limit_mode"];
  monthly_cost_limit: number | null;
  daily_request_limit: number | null;
  daily_token_limit: number | null;
};

export function listProjects(): Promise<AdminResult<ProjectRow[]>> {
  return getAdminJson("/admin/projects");
}

export function createProject(name: string): Promise<AdminResult<ProjectRow>> {
  return postAdminJson("/admin/projects", { name });
}

export function listProjectKeys(projectId: string): Promise<AdminResult<ApiKeyRow[]>> {
  return getAdminJson(`/admin/projects/${projectId}/keys`);
}

export function issueProjectKey(
  projectId: string,
  label?: string,
): Promise<AdminResult<ApiKeyCreated>> {
  return postAdminJson(`/admin/projects/${projectId}/keys`, {
    label: label ?? null,
  });
}

export function revokeProjectKey(
  projectId: string,
  keyId: string,
): Promise<AdminResult<void>> {
  return postAdminJson(`/admin/projects/${projectId}/keys/${keyId}/revoke`, {});
}

export function getProjectLimits(projectId: string): Promise<AdminResult<ProjectLimits>> {
  return getAdminJson(`/admin/projects/${projectId}/limits`);
}

export function saveProjectLimits(
  projectId: string,
  payload: SaveLimitsPayload,
): Promise<AdminResult<ProjectLimits>> {
  return putAdminJson(`/admin/projects/${projectId}/limits`, payload);
}

export function getProjectLimitsUsage(
  projectId: string,
): Promise<AdminResult<ProjectLimitsUsage>> {
  return getAdminJson(`/admin/projects/${projectId}/limits/usage`);
}

export function getProjectReservations(
  projectId: string,
): Promise<AdminResult<ProjectLimitsReservations>> {
  return getAdminJson(`/admin/projects/${projectId}/limits/reservations`);
}

export function getStaleReservations(
  projectId: string,
  limit = 100,
): Promise<AdminResult<StaleReservationsList>> {
  const params = new URLSearchParams({ project_id: projectId, limit: String(limit) });
  return getAdminJson(`/admin/projects/limits/reservations/stale?${params.toString()}`);
}

export function deleteProject(projectId: string): Promise<AdminResult<void>> {
  return deleteAdminJson(`/admin/projects/${projectId}`);
}
