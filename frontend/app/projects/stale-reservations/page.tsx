"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionHeader,
  Table,
} from "@/components/ui";
import { BACKEND_BASE, adminSessionFetch } from "@/lib/api";
import type {
  ReservationRepairResponse,
  StaleReservationItem,
  StaleReservationsList,
} from "@/lib/types";

function formatUsd(n: number) {
  if (n === 0) return "$0";
  if (Math.abs(n) < 0.0001) return "<$0.0001";
  return `$${n.toFixed(4)}`;
}

function formatAge(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function StaleReservationsContent() {
  const searchParams = useSearchParams();
  const projectFilter = searchParams.get("project_id");
  const [data, setData] = useState<StaleReservationsList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ReservationRepairResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      if (projectFilter) q.set("project_id", projectFilter);
      q.set("limit", "100");
      const res = await adminSessionFetch(
        `${BACKEND_BASE}/admin/projects/limits/reservations/stale?${q.toString()}`,
      );
      if (!res.ok) {
        setError("Unable to load stale reservations.");
        return;
      }
      setData((await res.json()) as StaleReservationsList);
    } finally {
      setLoading(false);
    }
  }, [projectFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function dryRun(reservationId: string) {
    setActing(`${reservationId}:dry`);
    setError(null);
    setLastResult(null);
    try {
      const res = await adminSessionFetch(
        `${BACKEND_BASE}/admin/projects/limits/reservations/${reservationId}/repair/dry-run`,
        { method: "POST" },
      );
      if (!res.ok) {
        setError("Dry-run failed.");
        return;
      }
      setLastResult((await res.json()) as ReservationRepairResponse);
    } finally {
      setActing(null);
    }
  }

  async function applyRepair(reservationId: string) {
    setActing(`${reservationId}:apply`);
    setError(null);
    setLastResult(null);
    try {
      const res = await adminSessionFetch(
        `${BACKEND_BASE}/admin/projects/limits/reservations/${reservationId}/repair`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reason: "stale reservation repair from back office",
          }),
        },
      );
      if (!res.ok) {
        setError("Repair failed.");
        return;
      }
      setLastResult((await res.json()) as ReservationRepairResponse);
      await load();
    } finally {
      setActing(null);
    }
  }

  const items: StaleReservationItem[] = data?.items ?? [];

  return (
    <div className="stack">
      <PageHeader
        title="Stale limit reservations"
        description="Unreconciled reservations past the stale threshold. Use dry-run to preview counter changes, then repair when safe."
      />
      <div className="inline-actions">
        <Link className="nav-link" href="/projects">
          ← Back to projects
        </Link>
        {projectFilter ? (
          <span className="muted">
            Filtered to project <code>{projectFilter}</code>
          </span>
        ) : null}
      </div>

      {loading ? <LoadingState label="Loading stale reservations..." /> : null}
      {error ? <ErrorState message={error} /> : null}

      {lastResult ? (
        <Card className="card-muted">
          <SectionHeader title="Last repair result" />
          <p className="muted">
            <strong>{lastResult.action}</strong> — {lastResult.message}
            {lastResult.applied ? " (applied)" : " (not applied)"}
          </p>
        </Card>
      ) : null}

      {!loading && data ? (
        <Card>
          <SectionHeader
            title="Summary"
            description={`Threshold: older than ${data.older_than_seconds}s (UTC ${data.now}). Total matching: ${data.total_count}.`}
          />
          <p className="muted">
            Oldest stale age:{" "}
            {data.oldest_age_seconds == null ? "—" : formatAge(data.oldest_age_seconds)}
          </p>
        </Card>
      ) : null}

      {!loading && !error && data && items.length === 0 ? (
        <EmptyState title="No stale reservations">
          Nothing matches the current filters.
        </EmptyState>
      ) : null}

      {!loading && items.length > 0 ? (
        <Card>
          <SectionHeader title="Reservations" />
          <Table aria-label="Stale limit reservations">
            <thead>
              <tr>
                <th>Project</th>
                <th>Reservation</th>
                <th>Age</th>
                <th>Req slots</th>
                <th>Tokens (res.)</th>
                <th>Cost (res.)</th>
                <th>GW status</th>
                <th>Recommended</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.reservation_id}>
                  <td>
                    <code>{row.project_id}</code>
                  </td>
                  <td>
                    <code>{row.reservation_id}</code>
                  </td>
                  <td>{formatAge(row.age_seconds)}</td>
                  <td>{row.request_slots}</td>
                  <td>{row.tokens_reserved.toLocaleString()}</td>
                  <td>{formatUsd(row.cost_reserved)}</td>
                  <td>{row.gateway_request_status ?? "—"}</td>
                  <td>{row.recommended_action}</td>
                  <td>
                    <div className="inline-actions">
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={acting !== null}
                        onClick={() => void dryRun(row.reservation_id)}
                      >
                        {acting === `${row.reservation_id}:dry` ? "…" : "Dry-run"}
                      </Button>
                      <Button
                        type="button"
                        disabled={acting !== null}
                        onClick={() => void applyRepair(row.reservation_id)}
                      >
                        {acting === `${row.reservation_id}:apply` ? "…" : "Repair"}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      ) : null}
    </div>
  );
}

export default function StaleReservationsPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading stale reservations..." />}>
      <StaleReservationsContent />
    </Suspense>
  );
}
