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
  gatewayProfileId?: string | null;
  canaryPercent?: number | null;
  publishedAt?: string | null;
  activatedAt?: string | null;
  rolledBackAt?: string | null;
  rollbackReason?: string | null;
};

export type AdapterProfile = AdapterProfileListItem & {
  evaluatedAt?: string;
  approvedAt?: string;
  toolProfile?: string;
  metrics?: EvaluationMetric[];
  gateResults?: EvaluationGateResult[];
};

/** v0.4 deployment action results (normalized). */
export type PublishAdapterProfileResult = {
  adapterProfileId: string;
  gatewayProfileId: string;
  status: string;
  wasDuplicate?: boolean;
};

export type AdapterProfileActivationResult = {
  activationId: string;
  adapterProfileId: string;
  status: string;
  wasDuplicate?: boolean;
};

export type PromoteAdapterProfileResult = {
  adapterProfileId: string;
  status: string;
  wasDuplicate?: boolean;
};

export type RollbackAdapterProfileResult = {
  adapterProfileId: string;
  status: string;
  wasDuplicate?: boolean;
};

/** Deployment audit events (tolerant DTO; upstream v0.4h). */
export type AdapterProfileDeploymentEvent = {
  id: string;
  eventType: string;
  createdAt: string;
  idempotencyKey?: string | null;
  detail?: string;
  userId?: string;
};

export type AdapterProfileActivation = {
  id: string;
  adapterProfileId: string;
  domainKey: string;
  status: string;
  canaryPercent: number;
  previousActiveProfileId?: string | null;
  rollbackReason?: string | null;
  createdAt: string;
  activatedAt?: string | null;
  rolledBackAt?: string | null;
};

export type EvaluationSecuritySummary = {
  summary?: string;
  riskLevel?: string;
  notes?: string;
};

export type CitationValidationIssue = {
  code?: string;
  message?: string;
  blocking?: boolean;
};

export type CitationValidationResult = {
  passed?: boolean;
  lexicalSupportScore?: number;
  issues?: CitationValidationIssue[];
};

export type RetrievedContextEvidence = {
  excerpt?: string;
  sourceId?: string;
  documentId?: string;
  chunkId?: string;
};

export type EvalQuestionEvidence = {
  questionId: string;
  question: string;
  category: string;
  answerExcerpt: string;
  answered: boolean;
  requiredSourceIds: string[];
  requiredDocumentIds: string[];
  requiredChunkIds: string[];
  retrievedContexts: RetrievedContextEvidence[];
  citationValidation: CitationValidationResult;
  estimatedCost: number;
  latencyMs: number;
};

export type EvaluationEvidence = {
  id: string;
  runId: string;
  planId: string;
  domainKey: string;
  evalSetId: string;
  createdAt: string;
  compositeScore: number;
  projectionVersion: string;
  evidenceHash: string;
  metrics: EvaluationMetric[];
  gates: EvaluationGateResult[];
  securitySummary: EvaluationSecuritySummary;
  questions: EvalQuestionEvidence[];
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
