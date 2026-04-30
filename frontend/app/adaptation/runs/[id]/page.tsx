"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Badge,
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
import { EvaluationEvidencePanel } from "@/components/adaptation/EvaluationEvidencePanel";
import { formatDate } from "@/lib/api";
import {
  adaptationApi,
  type AdaptationResult,
  type AdaptationRun,
  type AdaptationRunManifest,
  type AdapterProfile,
  type EvaluationEvidence,
} from "@/lib/adaptationApi";

export default function AdaptationRunDetailPage({ params }: { params: { id: string } }) {
  const runId = params.id;
  const [run, setRun] = useState<AdaptationRun | null>(null);
  const [manifest, setManifest] = useState<AdaptationRunManifest | null>(null);
  const [profile, setProfile] = useState<AdapterProfile | null>(null);
  const [profileUnavailable, setProfileUnavailable] = useState(false);
  const [evidence, setEvidence] = useState<EvaluationEvidence | null>(null);
  const [evidenceLoad, setEvidenceLoad] = useState<"loading" | "ok" | "404" | "error">("loading");
  const [loading, setLoading] = useState(true);
  const [lastError, setLastError] = useState<AdaptationResult<unknown> | null>(null);

  async function load() {
    setLoading(true);
    setLastError(null);
    setProfileUnavailable(false);
    setEvidenceLoad("loading");
    const [runRes, manifestRes, profileRes, evRes] = await Promise.all([
      adaptationApi.getRun(runId),
      adaptationApi.getRunManifest(runId),
      adaptationApi.getAdapterProfileByRunId(runId),
      adaptationApi.getRunEvaluation(runId),
    ]);
    if (!runRes.ok) {
      setLastError(runRes);
      setRun(null);
      setManifest(null);
      setProfile(null);
      setEvidence(null);
      setEvidenceLoad("error");
      setLoading(false);
      return;
    }
    setRun(runRes.data);
    setManifest(manifestRes.ok ? manifestRes.data : null);
    if (profileRes.ok) {
      setProfile(profileRes.data);
    } else {
      setProfile(null);
      setProfileUnavailable(profileRes.status === 404);
    }
    if (evRes.ok) {
      setEvidence(evRes.data);
      setEvidenceLoad("ok");
    } else if (evRes.status === 404) {
      setEvidence(null);
      setEvidenceLoad("404");
    } else {
      setEvidence(null);
      setEvidenceLoad("error");
    }
    setLoading(false);
  }

  useEffect(() => {
    void load();
  }, [runId]);

  const statusValue = run?.status ?? "—";
  const statusLower = typeof statusValue === "string" ? statusValue.toLowerCase() : "";
  const statusTone = statusLower === "failed" ? "danger" : statusLower === "completed" ? "success" : statusLower === "running" ? "info" : "neutral";

  const steps = useMemo(() => run?.steps ?? [], [run]);

  const profileId = profile?.profileId ?? profile?.id ?? null;

  return (
    <>
      <PageHeader
        eyebrow="Adaptation run"
        title={runId}
        description="Inspect steps, manifests, and produced adapter profile."
        actions={
          <div className="inline-actions">
            <LinkButton href="/adaptation/runs">Back to runs</LinkButton>
            {profileId && <LinkButton href={`/adaptation/profiles/${encodeURIComponent(profileId)}`}>Open profile</LinkButton>}
          </div>
        }
      />

      {lastError && <AdaptationErrorBanner result={lastError} />}

      {loading ? (
        <Card>
          <LoadingState label="Loading run..." />
        </Card>
      ) : !run ? (
        <Card>
          <EmptyState title="Run not found">No run data was returned for this ID.</EmptyState>
        </Card>
      ) : (
        <>
          <EvaluationEvidencePanel evidence={evidence} status={evidenceLoad} />

          <Card>
            <SectionHeader title="Run Summary" />
            <KeyValueGrid
              items={[
                { label: "runId", value: <CopyableId value={runId} /> },
                { label: "planId", value: <CopyableId value={run.planId ?? ""} /> },
                { label: "domainKey", value: <code className="wrap-anywhere">{run.domainKey ?? "—"}</code> },
                { label: "recipeKey", value: <code className="wrap-anywhere">{run.recipeKey ?? "—"}</code> },
                { label: "recipeVersion", value: run.recipeVersion ?? "—" },
                { label: "status", value: <Badge tone={statusTone}>{statusValue}</Badge> },
                { label: "createdAt", value: formatDate(run.createdAt) },
                { label: "startedAt", value: formatDate(run.startedAt) },
                { label: "completedAt", value: formatDate(run.completedAt) },
                { label: "failedAt", value: formatDate(run.failedAt) },
              ]}
            />
          </Card>

          <Card>
            <SectionHeader title="Step Timeline" description="Step keys and executor status. Expand raw JSON below for full detail." />
            {steps.length === 0 ? (
              <EmptyState title="No steps">No step timeline was returned for this run.</EmptyState>
            ) : (
              <Table aria-label="Run steps">
                <thead>
                  <tr>
                    <th>Step key</th>
                    <th>Executor</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Completed</th>
                    <th>Error code</th>
                    <th>Error message</th>
                  </tr>
                </thead>
                <tbody>
                  {steps.map((step, idx) => {
                    const key = step.stepKey ?? "—";
                    const executor = step.executorKey ?? "—";
                    const st = step.status ?? "—";
                    const stLower = typeof st === "string" ? st.toLowerCase() : "";
                    const tone =
                      stLower === "failed"
                        ? "danger"
                        : stLower === "completed" || stLower === "passed"
                          ? "success"
                          : stLower === "running"
                            ? "info"
                            : "neutral";
                    return (
                      <tr key={`${key}-${executor}-${idx}`}>
                        <td>
                          <code className="wrap-anywhere">{key}</code>
                        </td>
                        <td>
                          <code className="wrap-anywhere">{executor}</code>
                        </td>
                        <td>
                          <Badge tone={tone}>{st}</Badge>
                        </td>
                        <td>{formatDate(step.startedAt)}</td>
                        <td>{formatDate(step.completedAt)}</td>
                        <td>
                          <code className="wrap-anywhere">{step.errorCode ?? "—"}</code>
                        </td>
                        <td className="truncate">{step.errorMessage ?? "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            )}
          </Card>

          <Card id="manifest">
            <SectionHeader title="Manifest Summary" description="Key runner/planner versions and artifact IDs." />
            {manifest ? (
              <>
                <KeyValueGrid
                  items={[
                    { label: "runnerVersion", value: manifest.runnerVersion ?? "—" },
                    { label: "plannerVersion", value: manifest.plannerVersion ?? "—" },
                    {
                      label: "corpusSnapshotId",
                      value: <code className="wrap-anywhere">{manifest.corpusSnapshotId ?? "—"}</code>,
                    },
                    {
                      label: "indexManifestId",
                      value: <code className="wrap-anywhere">{manifest.indexManifestId ?? "—"}</code>,
                    },
                  ]}
                />
                <JsonBlock value={manifest} title="Manifest JSON" defaultOpen={false} />
              </>
            ) : (
              <EmptyState title="No manifest">This run did not return a manifest (or it is not available yet).</EmptyState>
            )}
          </Card>

          <Card>
            <SectionHeader title="Adapter Profile" description="A completed run may produce an adapter profile." />
            {profileId ? (
              <div className="inline-actions">
                <CopyableId value={profileId} />
                <Link className="button button-secondary" href={`/adaptation/profiles/${encodeURIComponent(profileId)}`}>
                  View profile
                </Link>
              </div>
            ) : profileUnavailable ? (
              <EmptyState title="No profile produced yet">The adapter-profile endpoint returned 404; the run may still be in progress.</EmptyState>
            ) : (
              <EmptyState title="No profile produced">This run did not return an adapter profile.</EmptyState>
            )}
          </Card>

          <Card>
            <SectionHeader title="Raw JSON" description="For audit/debugging. Not all fields are rendered yet." />
            <JsonBlock value={run} title="Run JSON" defaultOpen={false} />
            {profile && <JsonBlock value={profile} title="Adapter Profile JSON (by run)" defaultOpen={false} />}
          </Card>
        </>
      )}
    </>
  );
}
