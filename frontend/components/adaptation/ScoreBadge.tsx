"use client";

import { Badge } from "@/components/ui";

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null || Number.isNaN(score)) return <span>—</span>;
  const fixed = score.toFixed(4);
  return <Badge tone="neutral">{fixed}</Badge>;
}
