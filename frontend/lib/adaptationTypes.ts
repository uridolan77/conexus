/**
 * Canonical Adaptation BO DTO shapes (camelCase).
 * Upstream may send snake_case; see `adaptationNormalize.ts`.
 */

export type PlanningReason = {
  severity?: string;
  code?: string;
  message?: string;
};

export type AdaptationRunStep = {
  stepKey?: string;
  executorKey?: string;
  status?: string;
  startedAt?: string;
  completedAt?: string;
  errorCode?: string;
  errorMessage?: string;
};

export type AdaptationPlanListItem = {
  id?: string;
  planId?: string;
  createdAt?: string;
  domainKey?: string;
  taskDescription?: string;
  recommendedStrategy?: string;
  recipeKey?: string;
  status?: string;
  requiresHumanApproval?: boolean;
  createdByUserId?: string;
};

export type AdaptationPlan = AdaptationPlanListItem & {
  planningReasons?: PlanningReason[];
  constraints?: unknown;
  qualityTargets?: unknown;
  dataSources?: unknown;
  plannerDecision?: unknown;
  avoidedStrategies?: unknown;
  approvalState?: unknown;
};

export type AdaptationRunListItem = {
  runId?: string;
  id?: string;
  createdAt?: string;
  domainKey?: string;
  planId?: string;
  recipeKey?: string;
  status?: string;
  stepCount?: number;
  startedAt?: string;
  completedAt?: string;
  failedAt?: string;
};

export type AdaptationRun = AdaptationRunListItem & {
  steps?: AdaptationRunStep[];
  recipeVersion?: string;
};

export type AdaptationRunManifest = {
  runnerVersion?: string;
  plannerVersion?: string;
  corpusSnapshotId?: string;
  indexManifestId?: string;
  stepOutputHashes?: Record<string, string> | unknown;
};

export type EvaluationMetric = {
  key?: string;
  metricKey?: string;
  value?: string | number | boolean | null;
  threshold?: string | number | boolean | null;
  passed?: boolean;
};

export type EvaluationGateResult = {
  key?: string;
  gateKey?: string;
  blocking?: boolean;
  passed?: boolean;
  message?: string;
};

export type AdapterProfileListItem = {
  profileId?: string;
  id?: string;
  createdAt?: string;
  domainKey?: string;
  status?: string;
  approvedForRuntime?: boolean;
  compositeScore?: number | null;
  modelProfile?: string;
  promptProfile?: string;
  retrievalProfile?: string;
  safetyProfile?: string;
  planId?: string;
  runId?: string;
  /** Present when list API includes gate summaries. */
  gateResults?: EvaluationGateResult[];
};

export type AdapterProfile = AdapterProfileListItem & {
  evaluatedAt?: string;
  approvedAt?: string;
  toolProfile?: string;
  metrics?: EvaluationMetric[];
  gateResults?: EvaluationGateResult[];
};

/** POST /plans/{id}/run success body (normalized). */
export type AdaptationStartRunResponse = {
  runId: string | null;
};

/** ProblemDetails / RFC 7807-style error body from proxy or upstream. */
export type ProblemDetailsLike = {
  title?: string;
  detail?: string;
  status?: number;
  traceId?: string;
};
