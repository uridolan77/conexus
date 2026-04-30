"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  JsonBlock,
  KeyValueGrid,
  LinkButton,
  LoadingState,
  PageHeader,
  SectionHeader,
  Table,
} from "@/components/ui";
import { AdaptationErrorBanner } from "@/components/adaptation/AdaptationErrorBanner";
import { CopyableId } from "@/components/adaptation/CopyableId";
import { formatDate } from "@/lib/api";
import { adaptationApi, type AdaptationPlan, type AdaptationResult, type AdaptationRunListItem } from "@/lib/adaptationApi";

function planStatus(plan: AdaptationPlan | null) {
  const value = plan?.status;
  return typeof value === "string" ? value : "—";
}

export default function AdaptationPlanDetailPage({ params }: { params: { id: string } }) {
  const planId = params.id;
  const [plan, setPlan] = useState<AdaptationPlan | null>(null);
  const [runs, setRuns] = useState<AdaptationRunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [lastError, setLastError] = useState<AdaptationResult<unknown> | null>(null);

  async function load() {
    setLoading(true);
    setLastError(null);
    const [planRes, runsRes] = await Promise.all([
      adaptationApi.getPlan(planId),
      adaptationApi.listRunsForPlan(planId),
    ]);
    if (!planRes.ok) {
      setLastError(planRes);
      setPlan(null);
      setRuns([]);
      setLoading(false);
      return;
    }
    setPlan(planRes.data);
    if (runsRes.ok) setRuns(runsRes.data);
    else setRuns([]);
    setLoading(false);
  }

  useEffect(() => {
    void load();
  }, [planId]);

  async function approve() {
    setBusy(true);
    setLastError(null);
    const res = await adaptationApi.approvePlan(planId);
    if (!res.ok) setLastError(res);
    await load();
    setBusy(false);
  }

  async function startRun() {
    setBusy(true);
    setLastError(null);
    const res = await adaptationApi.startRun(planId);
    if (!res.ok) {
      setLastError(res);
      setBusy(false);
      return;
    }
    const runId = res.data.runId;
    if (typeof runId === "string" && runId) {
      window.location.href = `/adaptation/runs/${encodeURIComponent(runId)}`;
      return;
    }
    await load();
    setBusy(false);
  }

  const latestRunId = useMemo(() => {
    const candidates = runs
      .map((r) => r.runId ?? r.id)
      .filter((id): id is string => typeof id === "string" && id.length > 0);
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

      {lastError && <AdaptationErrorBanner result={lastError} />}

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
                { label: "planId", value: <CopyableId value={planId} /> },
                {
                  label: "status",
                  value: <Badge tone={statusLower === "draft" ? "warning" : "neutral"}>{statusValue}</Badge>,
                },
                { label: "createdAt", value: formatDate(plan.createdAt) },
                { label: "domainKey", value: <code className="wrap-anywhere">{plan.domainKey ?? "—"}</code> },
                { label: "recipeKey", value: <code className="wrap-anywhere">{plan.recipeKey ?? "—"}</code> },
                { label: "recommendedStrategy", value: plan.recommendedStrategy ?? "—" },
                { label: "requiresHumanApproval", value: String(plan.requiresHumanApproval ?? false) },
                { label: "createdByUserId", value: <code className="wrap-anywhere">{plan.createdByUserId ?? "—"}</code> },
              ]}
            />
          </Card>

          <Card>
            <SectionHeader title="Planner reasons" description="Reasons reported by the planner for the chosen and avoided strategies." />
            {plan.planningReasons && plan.planningReasons.length > 0 ? (
              <Table aria-label="Planning reasons">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Code</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.planningReasons.map((reason, idx) => (
                    <tr key={reason.code ?? idx}>
                      <td>{reason.severity ?? "—"}</td>
                      <td>
                        <code className="wrap-anywhere">{reason.code ?? "—"}</code>
                      </td>
                      <td>{reason.message ?? "—"}</td>
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
                    const id = run.runId ?? run.id ?? "";
                    const st = run.status ?? "—";
                    const stLower = typeof st === "string" ? st.toLowerCase() : "";
                    return (
                      <tr key={id || JSON.stringify(run)}>
                        <td>
                          <code className="wrap-anywhere">{id || "—"}</code>
                        </td>
                        <td>
                          <Badge tone={stLower === "failed" ? "danger" : stLower === "completed" ? "success" : "neutral"}>
                            {st}
                          </Badge>
                        </td>
                        <td>{formatDate(run.createdAt)}</td>
                        <td>{formatDate(run.startedAt)}</td>
                        <td>{formatDate(run.completedAt)}</td>
                        <td>
                          {id ? (
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
