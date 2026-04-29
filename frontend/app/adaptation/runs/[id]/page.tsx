"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Badge,
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

function asArray(value: unknown): any[] {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object" && "items" in value && Array.isArray((value as any).items)) {
    return (value as any).items as any[];
  }
  return [];
}

export default function AdaptationRunDetailPage({ params }: { params: { id: string } }) {
  const runId = params.id;
  const [run, setRun] = useState<any | null>(null);
  const [manifest, setManifest] = useState<any | null>(null);
  const [profile, setProfile] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    const [runRes, manifestRes, profileRes] = await Promise.all([
      adaptationApi.getRun(runId),
      adaptationApi.getRunManifest(runId),
      adaptationApi.getAdapterProfileByRunId(runId),
    ]);
    if (!runRes.ok) {
      setError(formatAdaptationError(runRes));
      setRun(null);
      setManifest(null);
      setProfile(null);
      setLoading(false);
      return;
    }
    setRun(runRes.data as any);
    setManifest(manifestRes.ok ? (manifestRes.data as any) : null);
    setProfile(profileRes.ok ? (profileRes.data as any) : null);
    setLoading(false);
  }

  useEffect(() => {
    void load();
  }, [runId]);

  const statusValue = run?.status ?? "—";
  const statusLower = typeof statusValue === "string" ? statusValue.toLowerCase() : "";
  const statusTone = statusLower === "failed" ? "danger" : statusLower === "completed" ? "success" : statusLower === "running" ? "info" : "neutral";

  const steps = useMemo(() => {
    const candidates =
      run?.steps ??
      run?.stepTimeline ??
      run?.step_timeline ??
      run?.stepResults ??
      run?.step_results ??
      [];
    return asArray(candidates);
  }, [run]);

  const profileId = profile?.profileId ?? profile?.id ?? profile?.profile_id ?? null;

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

      {error && <ErrorState message={error} />}

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
          <Card>
            <SectionHeader title="Run Summary" />
            <KeyValueGrid
              items={[
                { label: "runId", value: <code className="wrap-anywhere">{runId}</code> },
                { label: "planId", value: <code className="wrap-anywhere">{run?.planId ?? run?.plan_id ?? "—"}</code> },
                { label: "domainKey", value: <code className="wrap-anywhere">{run?.domainKey ?? run?.domain_key ?? "—"}</code> },
                { label: "recipeKey", value: <code className="wrap-anywhere">{run?.recipeKey ?? run?.recipe_key ?? "—"}</code> },
                { label: "recipeVersion", value: run?.recipeVersion ?? run?.recipe_version ?? "—" },
                { label: "status", value: <Badge tone={statusTone as any}>{statusValue}</Badge> },
                { label: "createdAt", value: formatDate(run?.createdAt ?? run?.created_at) },
                { label: "startedAt", value: formatDate(run?.startedAt ?? run?.started_at) },
                { label: "completedAt", value: formatDate(run?.completedAt ?? run?.completed_at) },
                { label: "failedAt", value: formatDate(run?.failedAt ?? run?.failed_at) },
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
                  {steps.map((step) => {
                    const key = step?.stepKey ?? step?.key ?? step?.step_key ?? "—";
                    const executor = step?.executorKey ?? step?.executor_key ?? step?.executor ?? "—";
                    const st = step?.status ?? "—";
                    const stLower = typeof st === "string" ? st.toLowerCase() : "";
                    const tone = stLower === "failed" ? "danger" : stLower === "completed" || stLower === "passed" ? "success" : stLower === "running" ? "info" : "neutral";
                    return (
                      <tr key={`${key}-${executor}-${JSON.stringify(step).slice(0, 20)}`}>
                        <td><code className="wrap-anywhere">{key}</code></td>
                        <td><code className="wrap-anywhere">{executor}</code></td>
                        <td><Badge tone={tone as any}>{st}</Badge></td>
                        <td>{formatDate(step?.startedAt ?? step?.started_at)}</td>
                        <td>{formatDate(step?.completedAt ?? step?.completed_at)}</td>
                        <td><code className="wrap-anywhere">{step?.errorCode ?? step?.error_code ?? "—"}</code></td>
                        <td className="truncate">{step?.errorMessage ?? step?.error_message ?? "—"}</td>
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
                    { label: "runnerVersion", value: manifest?.runnerVersion ?? manifest?.runner_version ?? "—" },
                    { label: "plannerVersion", value: manifest?.plannerVersion ?? manifest?.planner_version ?? "—" },
                    { label: "corpusSnapshotId", value: <code className="wrap-anywhere">{manifest?.corpusSnapshotId ?? manifest?.corpus_snapshot_id ?? "—"}</code> },
                    { label: "indexManifestId", value: <code className="wrap-anywhere">{manifest?.indexManifestId ?? manifest?.index_manifest_id ?? "—"}</code> },
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
                <code className="wrap-anywhere">{profileId}</code>
                <Link className="button button-secondary" href={`/adaptation/profiles/${encodeURIComponent(profileId)}`}>
                  View profile
                </Link>
              </div>
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

