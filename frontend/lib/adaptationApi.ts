"use client";

import { BACKEND_BASE, formatApiError, readJsonSafe } from "@/lib/api";
import type { StepResult } from "@/lib/types";

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

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<StepResult & ({ ok: true; data: T } | { ok: false; status?: number; error: unknown })> {
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
      window.location.href = "/login";
      return { ok: false, status: 401, error: "unauthorized" };
    }
    const body = await readJsonSafe(res);
    if (!res.ok) return { ok: false, status: res.status, error: body };
    return { ok: true, data: body as T };
  } catch (error) {
    return { ok: false, error };
  }
}

export function formatAdaptationError(result: StepResult): string {
  if (result.ok) return "";
  return formatApiError(result.error);
}

export const adaptationApi = {
  listPlans: (params?: URLSearchParams) =>
    requestJson<unknown>(`/admin/adaptation/plans${params ? `?${params.toString()}` : ""}`),
  getPlan: (planId: string) =>
    requestJson<unknown>(`/admin/adaptation/plans/${encodeURIComponent(planId)}`),
  listRunsForPlan: (planId: string) =>
    requestJson<unknown>(`/admin/adaptation/plans/${encodeURIComponent(planId)}/runs`),
  approvePlan: (planId: string) =>
    requestJson<unknown>(`/admin/adaptation/plans/${encodeURIComponent(planId)}/approve`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  startRun: (planId: string) =>
    requestJson<unknown>(`/admin/adaptation/plans/${encodeURIComponent(planId)}/run`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  listRuns: (params?: URLSearchParams) =>
    requestJson<unknown>(`/admin/adaptation/runs${params ? `?${params.toString()}` : ""}`),
  getRun: (runId: string) =>
    requestJson<unknown>(`/admin/adaptation/runs/${encodeURIComponent(runId)}`),
  getRunManifest: (runId: string) =>
    requestJson<unknown>(`/admin/adaptation/runs/${encodeURIComponent(runId)}/manifest`),
  getAdapterProfileByRunId: (runId: string) =>
    requestJson<unknown>(`/admin/adaptation/runs/${encodeURIComponent(runId)}/adapter-profile`),

  listProfiles: (params?: URLSearchParams) =>
    requestJson<unknown>(`/admin/adaptation/profiles${params ? `?${params.toString()}` : ""}`),
  getProfile: (profileId: string) =>
    requestJson<unknown>(`/admin/adaptation/profiles/${encodeURIComponent(profileId)}`),
};

