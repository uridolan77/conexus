"use client";

import { ErrorState } from "@/components/ui";
import { formatAdaptationError, parseAdaptationProblem, type AdaptationResult } from "@/lib/adaptationApi";
import { ProblemAlert } from "./ProblemAlert";

/** Renders ProblemDetails when available, otherwise a generic error string. */
export function AdaptationErrorBanner({ result }: { result: AdaptationResult<unknown> | null }) {
  if (!result || result.ok) return null;
  const problem = parseAdaptationProblem(result);
  if (problem && (problem.detail || problem.title || problem.status != null || problem.traceId)) {
    return <ProblemAlert problem={problem} />;
  }
  return <ErrorState message={formatAdaptationError(result)} />;
}
