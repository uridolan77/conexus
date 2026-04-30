import type {
  AdaptationPlan,
  AdaptationPlanListItem,
  AdaptationRun,
  AdaptationRunListItem,
  AdaptationRunManifest,
  AdaptationRunStep,
  AdaptationStartRunResponse,
  AdapterProfile,
  AdapterProfileActivation,
  AdapterProfileActivationResult,
  AdapterProfileDeploymentEvent,
  AdapterProfileListItem,
  CitationValidationIssue,
  CitationValidationResult,
  EvalQuestionEvidence,
  EvaluationEvidence,
  EvaluationGateResult,
  EvaluationMetric,
  EvaluationSecuritySummary,
  PlanningReason,
  ProblemDetailsLike,
  PromoteAdapterProfileResult,
  PublishAdapterProfileResult,
  RetrievedContextEvidence,
  RollbackAdapterProfileResult,
} from "@/lib/adaptationTypes";

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

function num(v: unknown): number | undefined {
  return typeof v === "number" && !Number.isNaN(v) ? v : undefined;
}

function numOrZero(v: unknown): number {
  const n = num(v);
  return n ?? 0;
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
  const canary =
    num(o.canaryPercent) ??
    num(o.canary_percent) ??
    (typeof o.canaryPercent === "string" ? Number(o.canaryPercent) : undefined) ??
    (typeof o.canary_percent === "string" ? Number(o.canary_percent) : undefined);
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
    gatewayProfileId: str(o.gatewayProfileId) ?? str(o.gateway_profile_id) ?? null,
    canaryPercent: canary !== undefined && !Number.isNaN(canary) ? canary : null,
    publishedAt: str(o.publishedAt) ?? str(o.published_at) ?? null,
    activatedAt: str(o.activatedAt) ?? str(o.activated_at) ?? null,
    rolledBackAt: str(o.rolledBackAt) ?? str(o.rolled_back_at) ?? null,
    rollbackReason: str(o.rollbackReason) ?? str(o.rollback_reason) ?? null,
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

function normalizeCitationIssue(raw: unknown): CitationValidationIssue {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    code: str(o.code),
    message: str(o.message),
    blocking: bool(o.blocking),
  };
}

function normalizeCitationValidation(raw: unknown): CitationValidationResult {
  if (!raw || typeof raw !== "object") return { issues: [] };
  const o = raw as Record<string, unknown>;
  const issuesRaw = o.issues ?? o.citationIssues;
  const issues = Array.isArray(issuesRaw) ? issuesRaw.map(normalizeCitationIssue) : [];
  return {
    passed: bool(o.passed),
    lexicalSupportScore: num(o.lexicalSupportScore) ?? num(o.lexical_support_score),
    issues,
  };
}

function normalizeRetrievedContext(raw: unknown): RetrievedContextEvidence {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    excerpt: str(o.excerpt) ?? str(o.text),
    sourceId: str(o.sourceId) ?? str(o.source_id),
    documentId: str(o.documentId) ?? str(o.document_id),
    chunkId: str(o.chunkId) ?? str(o.chunk_id),
  };
}

function strArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.map((x) => String(x)).filter(Boolean);
}

export function normalizeEvalQuestionEvidence(raw: unknown): EvalQuestionEvidence {
  if (!raw || typeof raw !== "object") {
    return {
      questionId: "",
      question: "",
      category: "",
      answerExcerpt: "",
      answered: false,
      requiredSourceIds: [],
      requiredDocumentIds: [],
      requiredChunkIds: [],
      retrievedContexts: [],
      citationValidation: { issues: [] },
      estimatedCost: 0,
      latencyMs: 0,
    };
  }
  const o = raw as Record<string, unknown>;
  const ctxRaw = o.retrievedContexts ?? o.retrieved_contexts ?? o.contexts;
  const citation = o.citationValidation ?? o.citation_validation;
  return {
    questionId: str(o.questionId) ?? str(o.question_id) ?? "",
    question: str(o.question) ?? "",
    category: str(o.category) ?? "",
    answerExcerpt: str(o.answerExcerpt) ?? str(o.answer_excerpt) ?? "",
    answered: bool(o.answered) ?? false,
    requiredSourceIds: strArray(o.requiredSourceIds ?? o.required_source_ids),
    requiredDocumentIds: strArray(o.requiredDocumentIds ?? o.required_document_ids),
    requiredChunkIds: strArray(o.requiredChunkIds ?? o.required_chunk_ids),
    retrievedContexts: Array.isArray(ctxRaw) ? ctxRaw.map(normalizeRetrievedContext) : [],
    citationValidation: normalizeCitationValidation(citation),
    estimatedCost: numOrZero(o.estimatedCost ?? o.estimated_cost),
    latencyMs: numOrZero(o.latencyMs ?? o.latency_ms),
  };
}

function normalizeSecuritySummary(raw: unknown): EvaluationSecuritySummary {
  if (!raw || typeof raw !== "object") return {};
  const o = raw as Record<string, unknown>;
  return {
    summary: str(o.summary) ?? str(o.overview),
    riskLevel: str(o.riskLevel) ?? str(o.risk_level),
    notes: str(o.notes),
  };
}

export function normalizeEvaluationEvidence(raw: unknown): EvaluationEvidence {
  if (!raw || typeof raw !== "object") {
    return {
      id: "",
      runId: "",
      planId: "",
      domainKey: "",
      evalSetId: "",
      createdAt: "",
      compositeScore: 0,
      projectionVersion: "",
      evidenceHash: "",
      metrics: [],
      gates: [],
      securitySummary: {},
      questions: [],
    };
  }
  const o = raw as Record<string, unknown>;
  const metricsRaw = o.metrics ?? o.metricResults ?? o.metric_results;
  const gatesRaw = o.gates ?? o.gateResults ?? o.gate_results;
  const questionsRaw = o.questions ?? o.questionEvidence ?? o.question_evidence;
  const sec = o.securitySummary ?? o.security_summary;
  return {
    id: str(o.id) ?? "",
    runId: str(o.runId) ?? str(o.run_id) ?? "",
    planId: str(o.planId) ?? str(o.plan_id) ?? "",
    domainKey: str(o.domainKey) ?? str(o.domain_key) ?? "",
    evalSetId: str(o.evalSetId) ?? str(o.eval_set_id) ?? str(o.evaluationSetId) ?? "",
    createdAt: str(o.createdAt) ?? str(o.created_at) ?? "",
    compositeScore: numOrZero(o.compositeScore ?? o.composite_score),
    projectionVersion: str(o.projectionVersion) ?? str(o.projection_version) ?? "",
    evidenceHash: str(o.evidenceHash) ?? str(o.evidence_hash) ?? "",
    metrics: Array.isArray(metricsRaw) ? metricsRaw.map(normalizeMetric) : [],
    gates: Array.isArray(gatesRaw) ? gatesRaw.map(normalizeGate) : [],
    securitySummary: normalizeSecuritySummary(sec),
    questions: Array.isArray(questionsRaw) ? questionsRaw.map(normalizeEvalQuestionEvidence) : [],
  };
}

export function normalizeActivationList(raw: unknown): AdapterProfileActivation[] {
  return asItemArray(raw).map((item) => {
    if (!item || typeof item !== "object") {
      return {
        id: "",
        adapterProfileId: "",
        domainKey: "",
        status: "",
        canaryPercent: 0,
        createdAt: "",
      };
    }
    const o = item as Record<string, unknown>;
    const pct = num(o.canaryPercent) ?? num(o.canary_percent) ?? 0;
    return {
      id: str(o.id) ?? str(o.activationId) ?? str(o.activation_id) ?? "",
      adapterProfileId: str(o.adapterProfileId) ?? str(o.adapter_profile_id) ?? "",
      domainKey: str(o.domainKey) ?? str(o.domain_key) ?? "",
      status: str(o.status) ?? "",
      canaryPercent: pct,
      previousActiveProfileId: str(o.previousActiveProfileId) ?? str(o.previous_active_profile_id) ?? null,
      rollbackReason: str(o.rollbackReason) ?? str(o.rollback_reason) ?? null,
      createdAt: str(o.createdAt) ?? str(o.created_at) ?? "",
      activatedAt: str(o.activatedAt) ?? str(o.activated_at) ?? null,
      rolledBackAt: str(o.rolledBackAt) ?? str(o.rolled_back_at) ?? null,
    };
  });
}

function normalizeWasDuplicate(o: Record<string, unknown>): boolean | undefined {
  const v = bool(o.wasDuplicate) ?? bool(o.was_duplicate);
  return v === undefined ? undefined : v;
}

export function normalizePublishResult(raw: unknown): PublishAdapterProfileResult {
  if (!raw || typeof raw !== "object") {
    return { adapterProfileId: "", gatewayProfileId: "", status: "" };
  }
  const o = raw as Record<string, unknown>;
  const dup = normalizeWasDuplicate(o);
  return {
    adapterProfileId: str(o.adapterProfileId) ?? str(o.adapter_profile_id) ?? str(o.profileId) ?? str(o.profile_id) ?? "",
    gatewayProfileId: str(o.gatewayProfileId) ?? str(o.gateway_profile_id) ?? "",
    status: str(o.status) ?? "",
    ...(dup !== undefined ? { wasDuplicate: dup } : {}),
  };
}

export function normalizeActivationResult(raw: unknown): AdapterProfileActivationResult {
  if (!raw || typeof raw !== "object") {
    return { activationId: "", adapterProfileId: "", status: "" };
  }
  const o = raw as Record<string, unknown>;
  const dup = normalizeWasDuplicate(o);
  return {
    activationId: str(o.activationId) ?? str(o.activation_id) ?? str(o.id) ?? "",
    adapterProfileId: str(o.adapterProfileId) ?? str(o.adapter_profile_id) ?? str(o.profileId) ?? "",
    status: str(o.status) ?? "",
    ...(dup !== undefined ? { wasDuplicate: dup } : {}),
  };
}

export function normalizePromoteResult(raw: unknown): PromoteAdapterProfileResult {
  if (!raw || typeof raw !== "object") {
    return { adapterProfileId: "", status: "" };
  }
  const o = raw as Record<string, unknown>;
  const dup = normalizeWasDuplicate(o);
  return {
    adapterProfileId: str(o.adapterProfileId) ?? str(o.adapter_profile_id) ?? str(o.profileId) ?? str(o.profile_id) ?? "",
    status: str(o.status) ?? "",
    ...(dup !== undefined ? { wasDuplicate: dup } : {}),
  };
}

export function normalizeRollbackResult(raw: unknown): RollbackAdapterProfileResult {
  if (!raw || typeof raw !== "object") {
    return { adapterProfileId: "", status: "" };
  }
  const o = raw as Record<string, unknown>;
  const dup = normalizeWasDuplicate(o);
  return {
    adapterProfileId: str(o.adapterProfileId) ?? str(o.adapter_profile_id) ?? str(o.profileId) ?? str(o.profile_id) ?? "",
    status: str(o.status) ?? "",
    ...(dup !== undefined ? { wasDuplicate: dup } : {}),
  };
}

export function normalizeDeploymentEventList(raw: unknown): AdapterProfileDeploymentEvent[] {
  return asItemArray(raw).map((item) => {
    if (!item || typeof item !== "object") {
      return { id: "", eventType: "", createdAt: "" };
    }
    const o = item as Record<string, unknown>;
    return {
      id: str(o.id) ?? str(o.eventId) ?? str(o.event_id) ?? "",
      eventType: str(o.eventType) ?? str(o.event_type) ?? str(o.type) ?? "",
      createdAt: str(o.createdAt) ?? str(o.created_at) ?? str(o.timestamp) ?? "",
      idempotencyKey: str(o.idempotencyKey) ?? str(o.idempotency_key) ?? null,
      detail: str(o.detail) ?? str(o.message) ?? str(o.description),
      userId: str(o.userId) ?? str(o.user_id),
    };
  });
}

/** Active profile for domain — same shape as profile list/detail fragment. */
export function normalizeActiveProfileDetail(raw: unknown): AdapterProfile {
  return normalizeProfileDetail(raw);
}
