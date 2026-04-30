"use client";

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
import { DeploymentActionPanel } from "@/components/adaptation/DeploymentActionPanel";
import { ScoreBadge } from "@/components/adaptation/ScoreBadge";
import { formatDate } from "@/lib/api";
import {
  adaptationApi,
  type AdapterProfile,
  type AdapterProfileActivation,
  type AdapterProfileDeploymentEvent,
  type AdaptationResult,
} from "@/lib/adaptationApi";

function bool(value: unknown) {
  return value === true || value === "true";
}

export default function AdapterProfileDetailPage({ params }: { params: { id: string } }) {
  const profileId = params.id;
  const [profile, setProfile] = useState<AdapterProfile | null>(null);
  const [activations, setActivations] = useState<AdapterProfileActivation[]>([]);
  const [deploymentEvents, setDeploymentEvents] = useState<AdapterProfileDeploymentEvent[]>([]);
  const [activeForDomain, setActiveForDomain] = useState<AdapterProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastError, setLastError] = useState<AdaptationResult<unknown> | null>(null);
  const [deploymentError, setDeploymentError] = useState<AdaptationResult<unknown> | null>(null);
  const [deploymentSuccess, setDeploymentSuccess] = useState<{ message: string; wasDuplicate?: boolean } | null>(null);

  async function loadProfileData(options?: { quiet?: boolean }) {
    const quiet = options?.quiet === true;
    if (!quiet) {
      setLoading(true);
      setLastError(null);
      setDeploymentError(null);
      setDeploymentSuccess(null);
    }
    const res = await adaptationApi.getProfile(profileId);
    if (!res.ok) {
      setProfile(null);
      setActivations([]);
      setDeploymentEvents([]);
      setActiveForDomain(null);
      setLastError(res);
      if (!quiet) setLoading(false);
      return;
    }
    const p = res.data;
    setProfile(p);
    const [actRes, evRes] = await Promise.all([
      adaptationApi.listProfileActivations(profileId),
      adaptationApi.listProfileDeploymentEvents(profileId),
    ]);
    setActivations(actRes.ok ? actRes.data : []);
    setDeploymentEvents(evRes.ok ? evRes.data : []);
    const dk = p.domainKey?.trim();
    if (dk) {
      const domRes = await adaptationApi.getActiveProfile(dk);
      setActiveForDomain(domRes.ok ? domRes.data : null);
    } else {
      setActiveForDomain(null);
    }
    if (!quiet) setLoading(false);
  }

  useEffect(() => {
    void loadProfileData();
  }, [profileId]);

  const approvedForRuntime = bool(profile?.approvedForRuntime);
  const compositeScore = profile?.compositeScore ?? null;

  const metrics = useMemo(() => profile?.metrics ?? [], [profile]);

  const gates = useMemo(() => profile?.gateResults ?? [], [profile]);

  const blockingFailures = useMemo(() => {
    return gates.filter((g) => bool(g.blocking) && g.passed === false).length;
  }, [gates]);

  const planId = profile?.planId ?? null;
  const runId = profile?.runId ?? null;

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

      {lastError && <AdaptationErrorBanner result={lastError} />}

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
                { label: "profileId", value: <CopyableId value={profileId} /> },
                { label: "planId", value: planId ? <CopyableId value={planId} /> : "—" },
                { label: "runId", value: runId ? <CopyableId value={runId} /> : "—" },
                { label: "domainKey", value: <code className="wrap-anywhere">{profile.domainKey ?? "—"}</code> },
                {
                  label: "status",
                  value: (
                    <Badge tone={(profile.status ?? "").toLowerCase() === "rejected" ? "danger" : "neutral"}>
                      {profile.status ?? "—"}
                    </Badge>
                  ),
                },
                {
                  label: "approvedForRuntime",
                  value: approvedForRuntime ? <Badge tone="success">true</Badge> : <Badge tone="neutral">false</Badge>,
                },
                { label: "compositeScore", value: <ScoreBadge score={compositeScore} /> },
                { label: "createdAt", value: formatDate(profile.createdAt) },
                { label: "evaluatedAt", value: formatDate(profile.evaluatedAt) },
                { label: "approvedAt", value: formatDate(profile.approvedAt) },
                {
                  label: "gatewayProfileId",
                  value: profile.gatewayProfileId ? (
                    <code className="wrap-anywhere">{profile.gatewayProfileId}</code>
                  ) : (
                    "—"
                  ),
                },
                {
                  label: "canaryPercent",
                  value:
                    profile.canaryPercent !== undefined && profile.canaryPercent !== null
                      ? String(profile.canaryPercent)
                      : "—",
                },
                { label: "publishedAt", value: formatDate(profile.publishedAt ?? undefined) },
                { label: "activatedAt", value: formatDate(profile.activatedAt ?? undefined) },
                { label: "rolledBackAt", value: formatDate(profile.rolledBackAt ?? undefined) },
                {
                  label: "rollbackReason",
                  value: profile.rollbackReason ? <span className="truncate">{profile.rollbackReason}</span> : "—",
                },
              ]}
            />
          </Card>

          {deploymentSuccess && (
            <Card className="card-muted">
              <div className="inline-actions">
                <p style={{ margin: 0, color: "var(--color-success)" }}>{deploymentSuccess.message}</p>
                {deploymentSuccess.wasDuplicate ? <Badge tone="info">Idempotent replay</Badge> : null}
              </div>
            </Card>
          )}
          {deploymentError && <AdaptationErrorBanner result={deploymentError} />}

          <DeploymentActionPanel
            profile={profile}
            profileId={profileId}
            activations={activations}
            activeForDomain={activeForDomain}
            onRefresh={async () => {
              await loadProfileData({ quiet: true });
            }}
            onDeploymentError={(r) => {
              setDeploymentError(r);
              setDeploymentSuccess(null);
            }}
            onDeploymentSuccess={(payload) => {
              setDeploymentSuccess(payload);
              setDeploymentError(null);
            }}
          />

          <Card>
            <SectionHeader title="Deployment events" description="Audit trail from the adaptation service (v0.4h)." />
            {deploymentEvents.length === 0 ? (
              <EmptyState title="No deployment events">No deployment events were returned for this profile.</EmptyState>
            ) : (
              <Table aria-label="Deployment events">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Event</th>
                    <th>Idempotency key</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {deploymentEvents.map((ev, idx) => (
                    <tr key={ev.id || `${ev.createdAt}-${idx}`}>
                      <td>{formatDate(ev.createdAt)}</td>
                      <td>
                        <code className="wrap-anywhere">{ev.eventType || "—"}</code>
                      </td>
                      <td>
                        {ev.idempotencyKey ? (
                          <code className="wrap-anywhere">{ev.idempotencyKey}</code>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="truncate">{ev.detail ?? ev.userId ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <SectionHeader title="Runtime Profile Keys" description="These keys map to runtime config objects (not expanded here in v0.3d)." />
            <KeyValueGrid
              items={[
                { label: "modelProfile", value: <code className="wrap-anywhere">{profile.modelProfile ?? "—"}</code> },
                { label: "promptProfile", value: <code className="wrap-anywhere">{profile.promptProfile ?? "—"}</code> },
                { label: "retrievalProfile", value: <code className="wrap-anywhere">{profile.retrievalProfile ?? "—"}</code> },
                { label: "safetyProfile", value: <code className="wrap-anywhere">{profile.safetyProfile ?? "—"}</code> },
                { label: "toolProfile", value: <code className="wrap-anywhere">{profile.toolProfile ?? "—"}</code> },
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
                  {metrics.map((m, idx) => {
                    const key = m.key ?? m.metricKey ?? "—";
                    const passed = m.passed;
                    return (
                      <tr key={`${key}-${idx}`}>
                        <td>
                          <code className="wrap-anywhere">{key}</code>
                        </td>
                        <td>
                          <code className="wrap-anywhere">{String(m.value ?? "—")}</code>
                        </td>
                        <td>
                          <code className="wrap-anywhere">{String(m.threshold ?? "—")}</code>
                        </td>
                        <td>
                          {passed === true ? (
                            <Badge tone="success">passed</Badge>
                          ) : passed === false ? (
                            <Badge tone="danger">failed</Badge>
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
                  {gates.map((g, idx) => {
                    const key = g.key ?? g.gateKey ?? "—";
                    const blocking = bool(g.blocking);
                    const passed = g.passed;
                    const blockingFailed = blocking && passed === false;
                    return (
                      <tr key={`${key}-${idx}`} className={blockingFailed ? "row-warning" : undefined}>
                        <td>
                          <code className="wrap-anywhere">{key}</code>
                        </td>
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
                        <td className="truncate">{g.message ?? "—"}</td>
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
                Failed blocking gates are highlighted above. Use the deployment lifecycle panel to publish or activate
                when the profile is ready.
              </p>
            )}
          </Card>
        </>
      )}
    </>
  );
}
