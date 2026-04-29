import type {
  AdaptationPlan,
  AdaptationPlanListItem,
  AdaptationRun,
  AdaptationRunListItem,
  AdaptationRunManifest,
  AdaptationRunStep,
  AdaptationStartRunResponse,
  AdapterProfile,
  AdapterProfileListItem,
  EvaluationGateResult,
  EvaluationMetric,
  PlanningReason,
  ProblemDetailsLike,
} from "@/lib/adaptationTypes";

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function num(v: unknown): number | undefined {
  return typeof v === "number" && !Number.isNaN(v) ? v : undefined;
}

function bool(v: unknown): boolean | undefined {
  if (typeof v === "boolean") return v;
  if (v === "true") return true;
  if (v === "false") return false;
  return undefined;
}

export function parseProblemDetails(body: unknown): ProblemDetailsLike | null {
  if (!body || typeof body !== "object") return null;
  const o = body as Record<string, unknown>;
  const detail = str(o.detail);
  const title = str(o.title);
  if (detail === undefined && title === undefined) return null;
  const status = typeof o.status === "number" ? o.status : undefined;
  const traceId = str(o.traceId) ?? str(o.trace_id);
  return { title, detail, status, traceId };
}

export function asItemArray(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object" && "items" in value) {
    const items = (value as { items?: unknown }).items;
    if (Array.isArray(items)) return items;
  }
  return [];
}

export function normalizePlanningReason(raw: unknown): PlanningReason {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    severity: str(o.severity),
    code: str(o.code),
    message: str(o.message),
  };
}

export function normalizeRunStep(raw: unknown): AdaptationRunStep {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    stepKey: str(o.stepKey) ?? str(o.key) ?? str(o.step_key),
    executorKey: str(o.executorKey) ?? str(o.executor_key) ?? str(o.executor),
    status: str(o.status),
    startedAt: str(o.startedAt) ?? str(o.started_at),
    completedAt: str(o.completedAt) ?? str(o.completed_at),
    errorCode: str(o.errorCode) ?? str(o.error_code),
    errorMessage: str(o.errorMessage) ?? str(o.error_message),
  };
}

export function normalizePlanListItem(raw: unknown): AdaptationPlanListItem {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    id: str(o.id) ?? str(o.planId) ?? str(o.plan_id),
    planId: str(o.planId) ?? str(o.plan_id) ?? str(o.id),
    createdAt: str(o.createdAt) ?? str(o.created_at),
    domainKey: str(o.domainKey) ?? str(o.domain_key),
    taskDescription: str(o.taskDescription) ?? str(o.task_description),
    recommendedStrategy: str(o.recommendedStrategy) ?? str(o.recommended_strategy),
    recipeKey: str(o.recipeKey) ?? str(o.recipe_key),
    status: str(o.status),
    requiresHumanApproval: bool(o.requiresHumanApproval) ?? bool(o.requires_human_approval),
    createdByUserId: str(o.createdByUserId) ?? str(o.created_by_user_id),
  };
}

export function normalizePlanDetail(raw: unknown): AdaptationPlan {
  const base = normalizePlanListItem(raw);
  if (!raw || typeof raw !== "object") return base;
  const o = raw as Record<string, unknown>;
  const reasonsRaw = o.planningReasons ?? o.planning_reasons;
  const planningReasons = Array.isArray(reasonsRaw)
    ? reasonsRaw.map(normalizePlanningReason)
    : undefined;
  return {
    ...base,
    planningReasons,
    constraints: o.constraints,
    qualityTargets: o.qualityTargets ?? o.quality_targets,
    dataSources: o.dataSources ?? o.data_sources,
    plannerDecision: o.plannerDecision ?? o.planner_decision,
    avoidedStrategies: o.avoidedStrategies ?? o.avoided_strategies,
    approvalState: o.approvalState ?? o.approval_state,
  };
}

export function normalizeRunListItem(raw: unknown): AdaptationRunListItem {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    runId: str(o.runId) ?? str(o.run_id) ?? str(o.id),
    id: str(o.id) ?? str(o.runId) ?? str(o.run_id),
    createdAt: str(o.createdAt) ?? str(o.created_at),
    domainKey: str(o.domainKey) ?? str(o.domain_key),
    planId: str(o.planId) ?? str(o.plan_id),
    recipeKey: str(o.recipeKey) ?? str(o.recipe_key),
    status: str(o.status),
    stepCount: num(o.stepCount) ?? num(o.step_count),
    startedAt: str(o.startedAt) ?? str(o.started_at),
    completedAt: str(o.completedAt) ?? str(o.completed_at),
    failedAt: str(o.failedAt) ?? str(o.failed_at),
  };
}

function stepArrayFromRun(o: Record<string, unknown>): unknown[] {
  const candidates = [
    o.steps,
    o.stepTimeline,
    o.step_timeline,
    o.stepResults,
    o.step_results,
  ];
  for (const c of candidates) {
    if (Array.isArray(c)) return c;
  }
  return [];
}

export function normalizeRunDetail(raw: unknown): AdaptationRun {
  const base = normalizeRunListItem(raw);
  if (!raw || typeof raw !== "object") return base;
  const o = raw as Record<string, unknown>;
  const steps = stepArrayFromRun(o).map(normalizeRunStep);
  return {
    ...base,
    recipeVersion: str(o.recipeVersion) ?? str(o.recipe_version),
    steps: steps.length ? steps : undefined,
  };
}

export function normalizeRunManifest(raw: unknown): AdaptationRunManifest {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    runnerVersion: str(o.runnerVersion) ?? str(o.runner_version),
    plannerVersion: str(o.plannerVersion) ?? str(o.planner_version),
    corpusSnapshotId: str(o.corpusSnapshotId) ?? str(o.corpus_snapshot_id),
    indexManifestId: str(o.indexManifestId) ?? str(o.index_manifest_id),
    stepOutputHashes: o.stepOutputHashes ?? o.step_output_hashes,
  };
}

export function normalizeMetric(raw: unknown): EvaluationMetric {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    key: str(o.key) ?? str(o.metricKey) ?? str(o.metric_key),
    metricKey: str(o.metricKey) ?? str(o.metric_key),
    value: (o.value as EvaluationMetric["value"]) ?? null,
    threshold: (o.threshold as EvaluationMetric["threshold"]) ?? null,
    passed: bool(o.passed),
  };
}

export function normalizeGate(raw: unknown): EvaluationGateResult {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    key: str(o.key) ?? str(o.gateKey) ?? str(o.gate_key),
    gateKey: str(o.gateKey) ?? str(o.gate_key),
    blocking: bool(o.blocking),
    passed: bool(o.passed),
    message: str(o.message),
  };
}

export function normalizeProfileListItem(raw: unknown): AdapterProfileListItem {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  const gatesRaw = o.gateResults ?? o.gate_results ?? o.gates;
  const gateResults = Array.isArray(gatesRaw) ? gatesRaw.map(normalizeGate) : undefined;
  return {
    profileId: str(o.profileId) ?? str(o.profile_id) ?? str(o.id),
    id: str(o.id) ?? str(o.profileId) ?? str(o.profile_id),
    createdAt: str(o.createdAt) ?? str(o.created_at),
    domainKey: str(o.domainKey) ?? str(o.domain_key),
    status: str(o.status),
    approvedForRuntime: bool(o.approvedForRuntime) ?? bool(o.approved_for_runtime),
    compositeScore: typeof o.compositeScore === "number" ? o.compositeScore : typeof o.composite_score === "number" ? (o.composite_score as number) : undefined,
    modelProfile: str(o.modelProfile) ?? str(o.model_profile),
    promptProfile: str(o.promptProfile) ?? str(o.prompt_profile),
    retrievalProfile: str(o.retrievalProfile) ?? str(o.retrieval_profile),
    safetyProfile: str(o.safetyProfile) ?? str(o.safety_profile),
    planId: str(o.planId) ?? str(o.plan_id),
    runId: str(o.runId) ?? str(o.run_id),
    gateResults,
  };
}

export function normalizeProfileDetail(raw: unknown): AdapterProfile {
  const base = normalizeProfileListItem(raw);
  if (!raw || typeof raw !== "object") return base;
  const o = raw as Record<string, unknown>;
  const metricsRaw = o.metrics ?? o.metricResults ?? o.metric_results;
  const gatesRaw = o.gateResults ?? o.gate_results ?? o.gates;
  const metrics = Array.isArray(metricsRaw) ? metricsRaw.map(normalizeMetric) : undefined;
  const gateResults = Array.isArray(gatesRaw) ? gatesRaw.map(normalizeGate) : base.gateResults;
  return {
    ...base,
    evaluatedAt: str(o.evaluatedAt) ?? str(o.evaluated_at),
    approvedAt: str(o.approvedAt) ?? str(o.approved_at),
    toolProfile: str(o.toolProfile) ?? str(o.tool_profile),
    metrics,
    gateResults,
  };
}

export function normalizePlanList(value: unknown): AdaptationPlanListItem[] {
  return asItemArray(value).map(normalizePlanListItem);
}

export function normalizeRunList(value: unknown): AdaptationRunListItem[] {
  return asItemArray(value).map(normalizeRunListItem);
}

export function normalizeProfileList(value: unknown): AdapterProfileListItem[] {
  return asItemArray(value).map(normalizeProfileListItem);
}

export function normalizeStartRunResponse(raw: unknown): AdaptationStartRunResponse {
  if (!raw || typeof raw !== "object") return { runId: null };
  const o = raw as Record<string, unknown>;
  const runId = str(o.runId) ?? str(o.run_id) ?? str(o.id);
  return { runId: runId ?? null };
}
