import {
  normalizePlanDetail,
  normalizePlanList,
  normalizeProfileDetail,
  normalizeProfileList,
  normalizeRunDetail,
  normalizeRunList,
  normalizeRunManifest,
  normalizeStartRunResponse,
  parseProblemDetails,
} from "@/lib/adaptationNormalize";
import type {
  AdaptationPlan,
  AdaptationPlanListItem,
  AdaptationRun,
  AdaptationRunListItem,
  AdaptationRunManifest,
  AdaptationStartRunResponse,
  AdapterProfile,
  AdapterProfileListItem,
  ProblemDetailsLike,
} from "@/lib/adaptationTypes";
import { BACKEND_BASE, formatApiError, readJsonSafe } from "@/lib/api";

export type AdaptationResult<T> =
  | { ok: true; data: T }
  | { ok: false; status?: number; error: unknown };

function adminUrl(path: string) {
  if (!path.startsWith("/")) return `${BACKEND_BASE}/${path}`;
  if (typeof window !== "undefined") {
    try {
      const base = new URL(BACKEND_BASE);
      if (base.origin === window.location.origin) return path;
    } catch {
      // ignore invalid BACKEND_BASE
    }
  }
  return `${BACKEND_BASE}${path}`;
}

async function requestAdaptation<T>(
  path: string,
  successParser: (body: unknown) => T,
  init?: RequestInit,
): Promise<AdaptationResult<T>> {
  try {
    const res = await fetch(adminUrl(path), {
      ...init,
      credentials: "include",
      cache: "no-store",
      headers: {
        "content-type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
    if (res.status === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      return { ok: false, status: 401, error: "unauthorized" };
    }
    const body = await readJsonSafe(res);
    if (!res.ok) return { ok: false, status: res.status, error: body };
    return { ok: true, data: successParser(body) };
  } catch (error) {
    return { ok: false, error };
  }
}

/** Human-readable one-line error (detail or fallback). */
export function formatAdaptationError(result: AdaptationResult<unknown>): string {
  if (result.ok) return "";
  return formatApiError(result.error);
}

/** RFC 7807-style body from a failed adaptation response, if parseable. */
export function parseAdaptationProblem(result: AdaptationResult<unknown>): ProblemDetailsLike | null {
  if (result.ok) return null;
  return parseProblemDetails(result.error);
}

export const adaptationApi = {
  listPlans: (params?: URLSearchParams) =>
    requestAdaptation(`/admin/adaptation/plans${params ? `?${params.toString()}` : ""}`, normalizePlanList),

  getPlan: (planId: string) =>
    requestAdaptation(`/admin/adaptation/plans/${encodeURIComponent(planId)}`, normalizePlanDetail),

  listRunsForPlan: (planId: string) =>
    requestAdaptation(
      `/admin/adaptation/plans/${encodeURIComponent(planId)}/runs`,
      normalizeRunList,
    ),

  approvePlan: (planId: string) =>
    requestAdaptation(
      `/admin/adaptation/plans/${encodeURIComponent(planId)}/approve`,
      (body) => body as Record<string, unknown>,
      { method: "POST", body: JSON.stringify({}) },
    ),

  startRun: (planId: string) =>
    requestAdaptation(
      `/admin/adaptation/plans/${encodeURIComponent(planId)}/run`,
      normalizeStartRunResponse,
      { method: "POST", body: JSON.stringify({}) },
    ),

  listRuns: (params?: URLSearchParams) =>
    requestAdaptation(`/admin/adaptation/runs${params ? `?${params.toString()}` : ""}`, normalizeRunList),

  getRun: (runId: string) =>
    requestAdaptation(`/admin/adaptation/runs/${encodeURIComponent(runId)}`, normalizeRunDetail),

  getRunManifest: (runId: string) =>
    requestAdaptation(`/admin/adaptation/runs/${encodeURIComponent(runId)}/manifest`, normalizeRunManifest),

  getAdapterProfileByRunId: (runId: string) =>
    requestAdaptation(
      `/admin/adaptation/runs/${encodeURIComponent(runId)}/adapter-profile`,
      normalizeProfileDetail,
    ),

  listProfiles: (params?: URLSearchParams) =>
    requestAdaptation(`/admin/adaptation/profiles${params ? `?${params.toString()}` : ""}`, normalizeProfileList),

  getProfile: (profileId: string) =>
    requestAdaptation(`/admin/adaptation/profiles/${encodeURIComponent(profileId)}`, normalizeProfileDetail),
};

export type {
  AdaptationPlan,
  AdaptationPlanListItem,
  AdaptationRun,
  AdaptationRunListItem,
  AdaptationRunManifest,
  AdaptationStartRunResponse,
  AdapterProfile,
  AdapterProfileListItem,
  ProblemDetailsLike,
};
