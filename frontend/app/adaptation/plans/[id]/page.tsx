"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  JsonBlock,
  KeyValueGrid,
  LinkButton,
  LoadingState,
  PageHeader,
  SectionHeader,
  Table,
} from "@/components/ui";
import { formatDate } from "@/lib/api";
import { adaptationApi, formatAdaptationError } from "@/lib/adaptationApi";

type PlanDetail = any;
type RunRow = any;

function asArray(value: unknown): any[] {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object" && "items" in value && Array.isArray((value as any).items)) {
    return (value as any).items as any[];
  }
  return [];
}

function planStatus(plan: PlanDetail | null) {
  const value = plan?.status;
  return typeof value === "string" ? value : "—";
}

export default function AdaptationPlanDetailPage({ params }: { params: { id: string } }) {
  const planId = params.id;
  const [plan, setPlan] = useState<PlanDetail | null>(null);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    const [planRes, runsRes] = await Promise.all([
      adaptationApi.getPlan(planId),
      adaptationApi.listRunsForPlan(planId),
    ]);
    if (!planRes.ok) {
      setError(formatAdaptationError(planRes));
      setPlan(null);
      setRuns([]);
      setLoading(false);
      return;
    }
    setPlan(planRes.data as any);
    if (runsRes.ok) setRuns(asArray(runsRes.data));
    else setRuns([]);
    setLoading(false);
  }

  useEffect(() => {
    void load();
  }, [planId]);

  async function approve() {
    setBusy(true);
    setError(null);
    const res = await adaptationApi.approvePlan(planId);
    if (!res.ok) setError(formatAdaptationError(res));
    await load();
    setBusy(false);
  }

  async function startRun() {
    setBusy(true);
    setError(null);
    const res = await adaptationApi.startRun(planId);
    if (!res.ok) {
      setError(formatAdaptationError(res));
      setBusy(false);
      return;
    }
    const body = res.data as any;
    const runId = body?.runId ?? body?.id ?? body?.run_id;
    if (typeof runId === "string" && runId) {
      window.location.href = `/adaptation/runs/${encodeURIComponent(runId)}`;
      return;
    }
    await load();
    setBusy(false);
  }

  const latestRunId = useMemo(() => {
    const candidates = runs
      .map((r) => r?.runId ?? r?.id ?? r?.run_id)
      .filter((id) => typeof id === "string" && id);
    return candidates.length ? candidates[0] : null;
  }, [runs]);

  const statusValue = planStatus(plan);
  const statusLower = statusValue.toLowerCase();

  return (
    <>
      <PageHeader
        eyebrow="Adaptation plan"
        title={planId}
        description="Inspect the plan, review planning reasons, and manage approval/run actions."
        actions={
          <div className="inline-actions">
            <LinkButton href="/adaptation/plans">Back to plans</LinkButton>
            <Button
              type="button"
              variant="secondary"
              disabled={busy || statusLower !== "draft"}
              onClick={() => void approve()}
            >
              Approve
            </Button>
            <Button
              type="button"
              variant="primary"
              disabled={busy || statusLower !== "approved"}
              onClick={() => void startRun()}
            >
              Start run
            </Button>
            {latestRunId && <LinkButton href={`/adaptation/runs/${encodeURIComponent(latestRunId)}`}>Latest run</LinkButton>}
          </div>
        }
      />

      {error && <ErrorState message={error} />}

      {loading ? (
        <Card>
          <LoadingState label="Loading plan..." />
        </Card>
      ) : !plan ? (
        <Card>
          <EmptyState title="Plan not found">No plan data was returned for this ID.</EmptyState>
        </Card>
      ) : (
        <>
          <Card>
            <SectionHeader title="Summary" />
            <KeyValueGrid
              items={[
                { label: "planId", value: <code className="wrap-anywhere">{planId}</code> },
                { label: "status", value: <Badge tone={statusLower === "draft" ? "warning" : "neutral"}>{statusValue}</Badge> },
                { label: "createdAt", value: formatDate(plan.createdAt ?? plan.created_at) },
                { label: "domainKey", value: <code className="wrap-anywhere">{plan.domainKey ?? plan.domain_key ?? "—"}</code> },
                { label: "recipeKey", value: <code className="wrap-anywhere">{plan.recipeKey ?? plan.recipe_key ?? "—"}</code> },
                { label: "recommendedStrategy", value: plan.recommendedStrategy ?? plan.recommended_strategy ?? "—" },
                { label: "requiresHumanApproval", value: String(plan.requiresHumanApproval ?? plan.requires_human_approval ?? false) },
                { label: "createdByUserId", value: <code className="wrap-anywhere">{plan.createdByUserId ?? plan.created_by_user_id ?? "—"}</code> },
              ]}
            />
          </Card>

          <Card>
            <SectionHeader title="Planner reasons" description="Reasons reported by the planner for the chosen and avoided strategies." />
            {Array.isArray(plan.planningReasons ?? plan.planning_reasons) &&
            (plan.planningReasons ?? plan.planning_reasons).length > 0 ? (
              <Table aria-label="Planning reasons">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Code</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {(plan.planningReasons ?? plan.planning_reasons).map((reason: any, idx: number) => (
                    <tr key={reason?.code ?? idx}>
                      <td>{reason?.severity ?? "—"}</td>
                      <td><code className="wrap-anywhere">{reason?.code ?? "—"}</code></td>
                      <td>{reason?.message ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <EmptyState title="No planning reasons">No planning reason entries were returned for this plan.</EmptyState>
            )}
          </Card>

          <Card>
            <SectionHeader title="Runs for this plan" />
            {runs.length === 0 ? (
              <EmptyState title="No runs">No runs are associated with this plan yet.</EmptyState>
            ) : (
              <Table aria-label="Plan runs">
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Started</th>
                    <th>Completed</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => {
                    const id = run?.runId ?? run?.id ?? run?.run_id;
                    const st = run?.status ?? "—";
                    const stLower = typeof st === "string" ? st.toLowerCase() : "";
                    return (
                      <tr key={id ?? JSON.stringify(run)}>
                        <td><code className="wrap-anywhere">{id ?? "—"}</code></td>
                        <td><Badge tone={stLower === "failed" ? "danger" : stLower === "completed" ? "success" : "neutral"}>{st}</Badge></td>
                        <td>{formatDate(run?.createdAt ?? run?.created_at)}</td>
                        <td>{formatDate(run?.startedAt ?? run?.started_at)}</td>
                        <td>{formatDate(run?.completedAt ?? run?.completed_at)}</td>
                        <td>
                          {typeof id === "string" && id ? (
                            <Link className="button button-secondary" href={`/adaptation/runs/${encodeURIComponent(id)}`}>
                              View run
                            </Link>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <SectionHeader title="Raw JSON" description="For audit/debugging. Not all fields are rendered yet." />
            <JsonBlock value={plan} defaultOpen={false} />
          </Card>
        </>
      )}
    </>
  );
}

