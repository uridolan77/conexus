"use client";

import { useState } from "react";
import { Badge, Button, Card, Field, Input, KeyValueGrid, SectionHeader, Table, Textarea } from "@/components/ui";
import type { AdapterProfile, AdapterProfileActivation } from "@/lib/adaptationTypes";
import { adaptationApi, type AdaptationResult } from "@/lib/adaptationApi";
import { formatDate } from "@/lib/api";
import { CopyableId } from "@/components/adaptation/CopyableId";

function normStatus(s: string | undefined) {
  return (s ?? "").trim().toLowerCase();
}

export function DeploymentActionPanel({
  profile,
  profileId,
  activations,
  activeForDomain,
  onRefresh,
  onDeploymentError,
  onDeploymentSuccess,
}: {
  profile: AdapterProfile;
  profileId: string;
  activations: AdapterProfileActivation[];
  activeForDomain: AdapterProfile | null;
  onRefresh: () => Promise<void>;
  onDeploymentError: (r: AdaptationResult<unknown>) => void;
  onDeploymentSuccess: (msg: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishNotes, setPublishNotes] = useState("");
  const [canaryOpen, setCanaryOpen] = useState(false);
  const [canaryPct, setCanaryPct] = useState("10");
  const [promoteOpen, setPromoteOpen] = useState(false);
  const [rollbackOpen, setRollbackOpen] = useState(false);
  const [rollbackReason, setRollbackReason] = useState("");

  const st = normStatus(profile.status);
  const activeId = activeForDomain?.profileId ?? activeForDomain?.id ?? null;
  const isActiveForDomain =
    activeId && (activeId === profileId || activeId === (profile.profileId ?? profile.id));

  const showPublish = st === "approved";
  const showCanary = st === "published";
  const showPromoteRollback = st === "canary";
  const showRollbackActive = st === "active";
  const terminal = st === "rolledback" || st === "retired";

  async function run(
    action: () => Promise<AdaptationResult<unknown>>,
    success: string,
  ) {
    setBusy(true);
    const res = await action();
    setBusy(false);
    if (!res.ok) {
      onDeploymentError(res);
      return;
    }
    onDeploymentSuccess(success);
    setPublishOpen(false);
    setCanaryOpen(false);
    setPromoteOpen(false);
    setRollbackOpen(false);
    setPublishNotes("");
    setRollbackReason("");
    await onRefresh();
  }

  return (
    <Card>
      <SectionHeader
        title="Deployment lifecycle"
        description="Publish, canary, promote, and rollback go through the Conexus admin proxy (identity injected server-side)."
      />
      <KeyValueGrid
        items={[
          {
            label: "status",
            value: <Badge tone={terminal ? "neutral" : "info"}>{profile.status ?? "—"}</Badge>,
          },
          {
            label: "approvedForRuntime",
            value:
              profile.approvedForRuntime === true ? (
                <Badge tone="success">true</Badge>
              ) : (
                <Badge tone="neutral">false</Badge>
              ),
          },
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
          {
            label: "active profile for domain",
            value: activeForDomain ? (
              <div className="inline-actions">
                {isActiveForDomain ? (
                  <Badge tone="success">This profile is active</Badge>
                ) : (
                  <>
                    <span className="muted">Other profile active:</span>
                    {activeId ? (
                      <CopyableId value={activeId} />
                    ) : (
                      "—"
                    )}
                  </>
                )}
              </div>
            ) : (
              <span className="muted">—</span>
            ),
          },
        ]}
      />

      <h4 style={{ marginTop: "var(--space-5)", marginBottom: "var(--space-2)" }}>Activation history</h4>
      {activations.length === 0 ? (
        <p className="muted">No activations returned for this profile.</p>
      ) : (
        <Table aria-label="Activation history">
          <thead>
            <tr>
              <th>Id</th>
              <th>Status</th>
              <th>Canary %</th>
              <th>Created</th>
              <th>Activated</th>
              <th>Rolled back</th>
              <th>Rollback reason</th>
            </tr>
          </thead>
          <tbody>
            {activations.map((a) => (
              <tr key={a.id || `${a.adapterProfileId}-${a.createdAt}`}>
                <td>
                  <code className="wrap-anywhere">{a.id || "—"}</code>
                </td>
                <td>{a.status}</td>
                <td>{a.canaryPercent}</td>
                <td>{formatDate(a.createdAt)}</td>
                <td>{formatDate(a.activatedAt ?? undefined)}</td>
                <td>{formatDate(a.rolledBackAt ?? undefined)}</td>
                <td className="truncate">{a.rollbackReason ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {terminal ? (
        <p className="muted" style={{ marginTop: "var(--space-4)" }}>
          No deployment actions available for this status.
        </p>
      ) : (
        <div className="stack" style={{ marginTop: "var(--space-4)" }}>
          {showPublish && (
            <div className="inline-actions">
              {!publishOpen ? (
                <Button type="button" disabled={busy} onClick={() => setPublishOpen(true)}>
                  Publish profile
                </Button>
              ) : (
                <div className="stack" style={{ maxWidth: 480 }}>
                  <p className="muted">
                    This registers the adapter profile with the gateway registration service. It does not necessarily shift
                    production traffic unless activation follows.
                  </p>
                  <Field label="Notes (optional)">
                    <Textarea
                      value={publishNotes}
                      onChange={(e) => setPublishNotes(e.target.value)}
                      rows={3}
                      placeholder="Operator note"
                    />
                  </Field>
                  <div className="inline-actions">
                    <Button
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        void run(
                          () =>
                            adaptationApi.publishProfile(profileId, {
                              notes: publishNotes.trim() || null,
                            }),
                          "Profile published.",
                        )
                      }
                    >
                      Confirm publish
                    </Button>
                    <Button type="button" variant="secondary" disabled={busy} onClick={() => setPublishOpen(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {showCanary && (
            <div className="inline-actions">
              {!canaryOpen ? (
                <Button type="button" disabled={busy} onClick={() => setCanaryOpen(true)}>
                  Activate canary
                </Button>
              ) : (
                <div className="stack" style={{ maxWidth: 360 }}>
                  <Field label="Canary percent (1–50)">
                    <Input
                      type="number"
                      min={1}
                      max={50}
                      value={canaryPct}
                      onChange={(e) => setCanaryPct(e.target.value)}
                    />
                  </Field>
                  <div className="inline-actions">
                    <Button
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        const n = Number.parseInt(canaryPct, 10);
                        if (Number.isNaN(n) || n < 1 || n > 50) {
                          onDeploymentError({
                            ok: false,
                            error: { detail: "Canary percent must be between 1 and 50." },
                          });
                          return;
                        }
                        void run(
                          () => adaptationApi.activateCanary(profileId, { canaryPercent: n }),
                          "Canary activated.",
                        );
                      }}
                    >
                      Confirm activate {canaryPct}% canary
                    </Button>
                    <Button type="button" variant="secondary" disabled={busy} onClick={() => setCanaryOpen(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {showPromoteRollback && (
            <div className="inline-actions">
              {!promoteOpen && !rollbackOpen ? (
                <>
                  <Button type="button" disabled={busy} onClick={() => setPromoteOpen(true)}>
                    Promote to active
                  </Button>
                  <Button type="button" variant="danger" disabled={busy} onClick={() => setRollbackOpen(true)}>
                    Rollback
                  </Button>
                </>
              ) : null}
              {promoteOpen && (
                <div className="stack" style={{ maxWidth: 480 }}>
                  <p className="muted">Promote this canary profile to full active for the domain?</p>
                  <div className="inline-actions">
                    <Button
                      type="button"
                      disabled={busy}
                      onClick={() => void run(() => adaptationApi.promoteProfile(profileId), "Profile promoted to active.")}
                    >
                      Confirm promote
                    </Button>
                    <Button type="button" variant="secondary" disabled={busy} onClick={() => setPromoteOpen(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
              {rollbackOpen && (
                <div className="stack" style={{ maxWidth: 480 }}>
                  <Field label="Rollback reason (required)">
                    <Textarea
                      value={rollbackReason}
                      onChange={(e) => setRollbackReason(e.target.value)}
                      rows={3}
                      placeholder="Why rollback is needed"
                    />
                  </Field>
                  <div className="inline-actions">
                    <Button
                      type="button"
                      variant="danger"
                      disabled={busy}
                      onClick={() => {
                        const r = rollbackReason.trim();
                        if (!r) {
                          onDeploymentError({
                            ok: false,
                            error: { detail: "Rollback reason is required." },
                          });
                          return;
                        }
                        void run(() => adaptationApi.rollbackProfile(profileId, { reason: r }), "Rollback requested.");
                      }}
                    >
                      Confirm rollback
                    </Button>
                    <Button type="button" variant="secondary" disabled={busy} onClick={() => setRollbackOpen(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {showRollbackActive && (
            <div className="inline-actions">
              {!rollbackOpen ? (
                <Button type="button" variant="danger" disabled={busy} onClick={() => setRollbackOpen(true)}>
                  Rollback
                </Button>
              ) : (
                <div className="stack" style={{ maxWidth: 480 }}>
                  <Field label="Rollback reason (required)">
                    <Textarea
                      value={rollbackReason}
                      onChange={(e) => setRollbackReason(e.target.value)}
                      rows={3}
                      placeholder="Why rollback is needed"
                    />
                  </Field>
                  <div className="inline-actions">
                    <Button
                      type="button"
                      variant="danger"
                      disabled={busy}
                      onClick={() => {
                        const r = rollbackReason.trim();
                        if (!r) {
                          onDeploymentError({
                            ok: false,
                            error: { detail: "Rollback reason is required." },
                          });
                          return;
                        }
                        void run(() => adaptationApi.rollbackProfile(profileId, { reason: r }), "Rollback requested.");
                      }}
                    >
                      Confirm rollback
                    </Button>
                    <Button type="button" variant="secondary" disabled={busy} onClick={() => setRollbackOpen(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
