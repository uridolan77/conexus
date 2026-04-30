"use client";

import Link from "next/link";
import { KeyValueGrid, LoadingState } from "@/components/ui";
import { formatDate } from "@/lib/api";
import { computePercent, formatCost, formatPercentValue, formatTokens } from "@/lib/format";
import type {
  ProjectLimits,
  ProjectLimitsReservations,
  ProjectLimitsUsage,
  StaleReservationsList,
} from "@/lib/types";

function UsageBar({
  label,
  current,
  limit,
  formatValue,
}: {
  label: string;
  current: number;
  limit: number | null | undefined;
  formatValue: (v: number) => string;
}) {
  const pct = computePercent(current, limit);
  return (
    <div>
      <div className="inline-actions" style={{ justifyContent: "space-between" }}>
        <strong>{label}</strong>
        <span className="muted">
          {formatValue(current)} / {limit == null ? "unlimited" : formatValue(limit)}
          {pct != null ? ` (${formatPercentValue(pct)})` : ""}
        </span>
      </div>
      {pct != null && (
        <div className="progress-bar">
          <div
            className={`progress-bar-fill${pct >= 100 ? " progress-bar-fill-danger" : ""}`}
            style={{ width: `${Math.min(100, pct)}%` }}
          />
        </div>
      )}
    </div>
  );
}

export function ProjectUsageCard({
  projectId,
  limits,
  usage,
  reservations,
  stale,
  loadingUsage,
  loadingReservations,
  loadingStale,
}: {
  projectId: string;
  limits: ProjectLimits | null;
  usage: ProjectLimitsUsage | null;
  reservations: ProjectLimitsReservations | null;
  stale: StaleReservationsList | null;
  loadingUsage: boolean;
  loadingReservations: boolean;
  loadingStale: boolean;
}) {
  if (loadingUsage) return <LoadingState label="Loading usage..." />;
  if (!usage) return null;

  return (
    <div className="stack" style={{ marginBottom: 12 }}>
      <div className="muted">
        Usage windows use UTC boundaries. Daily reset:{" "}
        {formatDate(usage.daily.reset_at)}. Monthly reset:{" "}
        {formatDate(usage.monthly.reset_at)}.
      </div>

      {loadingReservations ? (
        <LoadingState label="Loading reservation counters..." />
      ) : reservations ? (
        <div className="stack" style={{ marginBottom: 12 }}>
          <div className="muted">
            Admission counters (UTC): reserved slots vs completed for the active windows.
            Empty until the first hard-limit gateway call creates rows.
          </div>
          <KeyValueGrid
            items={[
              {
                label: "Daily requests (reserved / completed)",
                value:
                  reservations.daily == null
                    ? "—"
                    : `${formatTokens(reservations.daily.request_count_reserved)} / ${formatTokens(reservations.daily.request_count_completed)}`,
              },
              {
                label: "Daily tokens (reserved / completed)",
                value:
                  reservations.daily == null
                    ? "—"
                    : `${formatTokens(reservations.daily.token_count_reserved)} / ${formatTokens(reservations.daily.token_count_completed)}`,
              },
              {
                label: "Monthly cost (reserved / completed)",
                value:
                  reservations.monthly == null
                    ? "—"
                    : `${formatCost(reservations.monthly.cost_reserved)} / ${formatCost(reservations.monthly.cost_completed)}`,
              },
            ]}
          />

          {loadingStale ? (
            <LoadingState label="Loading stale reservation summary..." />
          ) : stale ? (
            <div className="stack" style={{ marginBottom: 12 }}>
              <div className="muted">
                Stale reservations are unreconciled limit rows older than the configured threshold.{" "}
                <Link
                  className="nav-link"
                  href={`/projects/stale-reservations?project_id=${projectId}`}
                >
                  View stale reservations
                </Link>{" "}
                for this project.
              </div>
              <KeyValueGrid
                items={[
                  {
                    label: "Stale reservations (count)",
                    value: formatTokens(stale.total_count),
                  },
                  {
                    label: "Oldest stale age",
                    value:
                      stale.oldest_age_seconds == null
                        ? "—"
                        : formatDuration(stale.oldest_age_seconds),
                  },
                ]}
              />
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="stack">
        <UsageBar
          label="Daily requests"
          current={usage.daily.request_count}
          limit={limits?.daily_request_limit}
          formatValue={formatTokens}
        />
        <UsageBar
          label="Daily tokens"
          current={usage.daily.total_tokens}
          limit={limits?.daily_token_limit}
          formatValue={formatTokens}
        />
        <UsageBar
          label="Monthly cost (USD)"
          current={usage.monthly.estimated_cost}
          limit={limits?.monthly_cost_limit}
          formatValue={formatCost}
        />
      </div>
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}
