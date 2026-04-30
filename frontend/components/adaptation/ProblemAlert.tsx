"use client";

import type { ProblemDetailsLike } from "@/lib/adaptationTypes";
import { Alert } from "@/components/ui";

export function ProblemAlert({ problem }: { problem: ProblemDetailsLike }) {
  const title = problem.title ?? "Request failed";
  const detail = problem.detail ?? "";
  const parts: string[] = [];
  if (problem.status != null) parts.push(`HTTP ${problem.status}`);
  if (problem.traceId) parts.push(`traceId: ${problem.traceId}`);
  const meta = parts.length ? parts.join(" · ") : null;

  return (
    <Alert tone="danger" title={title}>
      {detail ? <p>{detail}</p> : null}
      {meta ? <p className="muted">{meta}</p> : null}
    </Alert>
  );
}
