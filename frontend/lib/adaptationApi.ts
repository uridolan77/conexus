import {
  normalizeActivationList,
  normalizeActivationResult,
  normalizeActiveProfileDetail,
  normalizeDeploymentEventList,
  normalizeEvaluationEvidence,
  normalizePlanDetail,
  normalizePlanList,
  normalizeProfileDetail,
  normalizeProfileList,
  normalizePromoteResult,
  normalizePublishResult,
  normalizeRollbackResult,
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
  AdapterProfileActivation,
  AdapterProfileActivationResult,
  AdapterProfileDeploymentEvent,
  AdapterProfileListItem,
  EvaluationEvidence,
  ProblemDetailsLike,
  PromoteAdapterProfileResult,
  PublishAdapterProfileResult,
  RollbackAdapterProfileResult,
} from "@/lib/adaptationTypes";
import { BACKEND_BASE, adminSessionFetch, formatApiError, readJsonSafe } from "@/lib/api";

export type AdaptationResult<T> =
  | { ok: true; data: T }
  | { ok: false; status?: number; error: unknown };

export type GatewayRuntimeState = {
  adapterProfileId: string;
  registered: boolean;
  gatewayProfileId?: string | null;
  registrationStatus?: string | null;
  domainKey?: string | null;
  activeGatewayProfileId?: string | null;
  canaryGatewayProfileId?: string | null;
  canaryPercent?: number | null;
  last24h?: {
    requestCount: number;
    errorRate: number | null;
    latencyP95Ms: number | null;
    costPerAnswer: number | null;
  } | null;
};

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

function idempotencyHeaders(key: string | undefined): Record<string, string> | undefined {
  const k = key?.trim();
  if (!k) return undefined;
  return { "Idempotency-Key": k };
}

async function requestAdaptation<T>(
  path: string,
  successParser: (body: unknown) => T,
  init?: RequestInit,
): Promise<AdaptationResult<T>> {
  try {
    const res = await adminSessionFetch(adminUrl(path), {
      ...init,
      cache: "no-store",
      headers: {
        "content-type": "application/json",
        ...(init?.headers as Record<string, string> | undefined),
      },
    });
    if (res.status === 401) {
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

  getGatewayRuntimeState: (profileId: string) =>
    requestAdaptation(
      `/admin/adapter-profiles/${encodeURIComponent(profileId)}/runtime-state`,
      (body) => body as GatewayRuntimeState,
    ),

  getRunEvaluation: (runId: string) =>
    requestAdaptation(
      `/admin/adaptation/runs/${encodeURIComponent(runId)}/evaluation`,
      normalizeEvaluationEvidence,
    ),

  publishProfile: (profileId: string, input: { notes?: string | null; idempotencyKey?: string }) =>
    requestAdaptation(
      `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/publish`,
      normalizePublishResult,
      {
        method: "POST",
        body: JSON.stringify({ notes: input.notes ?? null }),
        headers: idempotencyHeaders(input.idempotencyKey),
      },
    ),

  activateCanary: (profileId: string, input: { canaryPercent: number; idempotencyKey?: string }) =>
    requestAdaptation(
      `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/activate-canary`,
      normalizeActivationResult,
      {
        method: "POST",
        body: JSON.stringify({ canaryPercent: input.canaryPercent }),
        headers: idempotencyHeaders(input.idempotencyKey),
      },
    ),

  promoteProfile: (profileId: string, input?: { idempotencyKey?: string }) =>
    requestAdaptation(
      `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/promote`,
      normalizePromoteResult,
      {
        method: "POST",
        body: JSON.stringify({}),
        headers: idempotencyHeaders(input?.idempotencyKey),
      },
    ),

  rollbackProfile: (profileId: string, input: { reason: string; idempotencyKey?: string }) =>
    requestAdaptation(
      `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/rollback`,
      normalizeRollbackResult,
      {
        method: "POST",
        body: JSON.stringify({ reason: input.reason }),
        headers: idempotencyHeaders(input.idempotencyKey),
      },
    ),

  listProfileActivations: (profileId: string) =>
    requestAdaptation(
      `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/activations`,
      normalizeActivationList,
    ),

  getActiveProfile: (domainKey: string) =>
    requestAdaptation(
      `/admin/adaptation/domains/${encodeURIComponent(domainKey)}/active-profile`,
      normalizeActiveProfileDetail,
    ),

  listProfileDeploymentEvents: (profileId: string) =>
    requestAdaptation(
      `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/deployment-events`,
      normalizeDeploymentEventList,
    ),

  cancelRun: (runId: string, input?: { reason?: string | null }) =>
    requestAdaptation(
      `/admin/adaptation/runs/${encodeURIComponent(runId)}/cancel`,
      (body) => body as Record<string, unknown>,
      {
        method: "POST",
        body: JSON.stringify({ reason: input?.reason ?? null }),
      },
    ),

  retryRun: (runId: string, input?: { idempotencyKey?: string }) =>
    requestAdaptation(
      `/admin/adaptation/runs/${encodeURIComponent(runId)}/retry`,
      (body) => body as Record<string, unknown>,
      {
        method: "POST",
        body: JSON.stringify({}),
        headers: idempotencyHeaders(input?.idempotencyKey),
      },
    ),

  resumeRun: (runId: string, input?: { idempotencyKey?: string }) =>
    requestAdaptation(
      `/admin/adaptation/runs/${encodeURIComponent(runId)}/resume`,
      (body) => body as Record<string, unknown>,
      {
        method: "POST",
        body: JSON.stringify({}),
        headers: idempotencyHeaders(input?.idempotencyKey),
      },
    ),

  getProfileDriftStatus: (profileId: string) =>
    requestAdaptation(
      `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/drift-status`,
      (body) => body as Record<string, unknown>,
    ),

  checkProfileDrift: (profileId: string, input?: { kind?: string | null }) =>
    requestAdaptation(
      `/admin/adaptation/profiles/${encodeURIComponent(profileId)}/check-drift`,
      (body) => body as Record<string, unknown>,
      {
        method: "POST",
        body: JSON.stringify(input?.kind ? { kind: input.kind } : {}),
      },
    ),

  getQueueDiagnostics: (params?: URLSearchParams) =>
    requestAdaptation(
      `/admin/adaptation/runs/queue/diagnostics${params ? `?${params.toString()}` : ""}`,
      (body) => body as Record<string, unknown>,
    ),

  queueRepairDryRun: (input?: Record<string, unknown>) =>
    requestAdaptation(
      `/admin/adaptation/runs/queue/repair/dry-run`,
      (body) => body as Record<string, unknown>,
      {
        method: "POST",
        body: JSON.stringify(input ?? {}),
      },
    ),

  queueRepairApply: (input?: Record<string, unknown>) =>
    requestAdaptation(
      `/admin/adaptation/runs/queue/repair`,
      (body) => body as Record<string, unknown>,
      {
        method: "POST",
        body: JSON.stringify(input ?? {}),
      },
    ),
};

export type {
  AdaptationPlan,
  AdaptationPlanListItem,
  AdaptationRun,
  AdaptationRunListItem,
  AdaptationRunManifest,
  AdaptationStartRunResponse,
  AdapterProfile,
  AdapterProfileActivation,
  AdapterProfileActivationResult,
  AdapterProfileDeploymentEvent,
  AdapterProfileListItem,
  EvaluationEvidence,
  ProblemDetailsLike,
  PromoteAdapterProfileResult,
  PublishAdapterProfileResult,
  RollbackAdapterProfileResult,
};
