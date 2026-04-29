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

function bool(value: unknown) {
  return value === true || value === "true";
}

export default function AdapterProfileDetailPage({ params }: { params: { id: string } }) {
  const profileId = params.id;
  const [profile, setProfile] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    const res = await adaptationApi.getProfile(profileId);
    if (!res.ok) {
      setProfile(null);
      setError(formatAdaptationError(res));
      setLoading(false);
      return;
    }
    setProfile(res.data as any);
    setLoading(false);
  }

  useEffect(() => {
    void load();
  }, [profileId]);

  const approvedForRuntime = bool(profile?.approvedForRuntime ?? profile?.approved_for_runtime);
  const compositeScore = profile?.compositeScore ?? profile?.composite_score ?? null;

  const metrics = useMemo(() => {
    const raw = profile?.metrics ?? profile?.metricResults ?? profile?.metric_results ?? [];
    return asArray(raw);
  }, [profile]);

  const gates = useMemo(() => {
    const raw = profile?.gateResults ?? profile?.gate_results ?? profile?.gates ?? [];
    return asArray(raw);
  }, [profile]);

  const blockingFailures = useMemo(() => {
    return gates.filter((g) => bool(g?.blocking) && (g?.passed === false || g?.passed === "false")).length;
  }, [gates]);

  const planId = profile?.planId ?? profile?.plan_id ?? null;
  const runId = profile?.runId ?? profile?.run_id ?? null;

  return (
    <>
      <PageHeader
        eyebrow="Adapter profile"
        title={profileId}
        description="Inspect composite score, metrics, and gate results for this profile."
        actions={
          <div className="inline-actions">
            <LinkButton href="/adaptation/profiles">Back to profiles</LinkButton>
            {runId && <LinkButton href={`/adaptation/runs/${encodeURIComponent(runId)}`}>Open run</LinkButton>}
            {planId && <LinkButton href={`/adaptation/plans/${encodeURIComponent(planId)}`}>Open plan</LinkButton>}
          </div>
        }
      />

      {error && <ErrorState message={error} />}

      {loading ? (
        <Card>
          <LoadingState label="Loading profile..." />
        </Card>
      ) : !profile ? (
        <Card>
          <EmptyState title="Profile not found">No adapter profile data was returned for this ID.</EmptyState>
        </Card>
      ) : (
        <>
          <Card>
            <SectionHeader title="Profile Summary" />
            <KeyValueGrid
              items={[
                { label: "profileId", value: <code className="wrap-anywhere">{profileId}</code> },
                { label: "planId", value: planId ? <code className="wrap-anywhere">{planId}</code> : "—" },
                { label: "runId", value: runId ? <code className="wrap-anywhere">{runId}</code> : "—" },
                { label: "domainKey", value: <code className="wrap-anywhere">{profile?.domainKey ?? profile?.domain_key ?? "—"}</code> },
                { label: "status", value: <Badge tone={(profile?.status ?? "").toLowerCase() === "rejected" ? "danger" : "neutral"}>{profile?.status ?? "—"}</Badge> },
                { label: "approvedForRuntime", value: approvedForRuntime ? <Badge tone="success">true</Badge> : <Badge tone="neutral">false</Badge> },
                { label: "compositeScore", value: typeof compositeScore === "number" ? compositeScore.toFixed(4) : (compositeScore ?? "—") },
                { label: "createdAt", value: formatDate(profile?.createdAt ?? profile?.created_at) },
                { label: "evaluatedAt", value: formatDate(profile?.evaluatedAt ?? profile?.evaluated_at) },
                { label: "approvedAt", value: formatDate(profile?.approvedAt ?? profile?.approved_at) },
              ]}
            />
          </Card>

          <Card>
            <SectionHeader title="Runtime Profile Keys" description="These keys map to runtime config objects (not expanded here in v0.3d)." />
            <KeyValueGrid
              items={[
                { label: "modelProfile", value: <code className="wrap-anywhere">{profile?.modelProfile ?? profile?.model_profile ?? "—"}</code> },
                { label: "promptProfile", value: <code className="wrap-anywhere">{profile?.promptProfile ?? profile?.prompt_profile ?? "—"}</code> },
                { label: "retrievalProfile", value: <code className="wrap-anywhere">{profile?.retrievalProfile ?? profile?.retrieval_profile ?? "—"}</code> },
                { label: "safetyProfile", value: <code className="wrap-anywhere">{profile?.safetyProfile ?? profile?.safety_profile ?? "—"}</code> },
                { label: "toolProfile", value: <code className="wrap-anywhere">{profile?.toolProfile ?? profile?.tool_profile ?? "—"}</code> },
              ]}
            />
          </Card>

          <Card>
            <SectionHeader title="Metrics" description="Exact metric keys are shown for audit/debugging." />
            {metrics.length === 0 ? (
              <EmptyState title="No metrics">No metric results were returned for this profile.</EmptyState>
            ) : (
              <Table aria-label="Profile metrics">
                <thead>
                  <tr>
                    <th>Metric key</th>
                    <th>Value</th>
                    <th>Threshold</th>
                    <th>Passed</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((m) => {
                    const key = m?.key ?? m?.metricKey ?? m?.metric_key ?? "—";
                    const passed = m?.passed;
                    return (
                      <tr key={`${key}-${JSON.stringify(m).slice(0, 24)}`}>
                        <td><code className="wrap-anywhere">{key}</code></td>
                        <td><code className="wrap-anywhere">{String(m?.value ?? "—")}</code></td>
                        <td><code className="wrap-anywhere">{String(m?.threshold ?? "—")}</code></td>
                        <td>{passed === true ? <Badge tone="success">passed</Badge> : passed === false ? <Badge tone="danger">failed</Badge> : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <SectionHeader
              title="Gate Results"
              description={
                blockingFailures > 0
                  ? `Blocking failures detected: ${blockingFailures}.`
                  : "Gate results determine whether a profile is safe to approve for runtime."
              }
            />
            {gates.length === 0 ? (
              <EmptyState title="No gates">No gate results were returned for this profile.</EmptyState>
            ) : (
              <Table aria-label="Profile gate results">
                <thead>
                  <tr>
                    <th>Gate key</th>
                    <th>Blocking</th>
                    <th>Passed</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {gates.map((g) => {
                    const key = g?.key ?? g?.gateKey ?? g?.gate_key ?? "—";
                    const blocking = bool(g?.blocking);
                    const passed = g?.passed;
                    const blockingFailed = blocking && (passed === false || passed === "false");
                    return (
                      <tr
                        key={`${key}-${JSON.stringify(g).slice(0, 24)}`}
                        className={blockingFailed ? "row-warning" : undefined}
                      >
                        <td><code className="wrap-anywhere">{key}</code></td>
                        <td>{blocking ? <Badge tone="warning">blocking</Badge> : "—"}</td>
                        <td>
                          {passed === true ? (
                            <Badge tone="success">passed</Badge>
                          ) : passed === false ? (
                            <Badge tone={blocking ? "danger" : "warning"}>failed</Badge>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="truncate">{g?.message ?? "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <SectionHeader title="Raw JSON" description="For audit/debugging. Not all fields are rendered yet." />
            <JsonBlock value={profile} defaultOpen={false} />
            {blockingFailures > 0 && (
              <p className="muted">
                Failed blocking gates are highlighted above. This does not publish or activate a profile in v0.3d.
              </p>
            )}
          </Card>
        </>
      )}
    </>
  );
}

