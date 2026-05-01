"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  FormRow,
  Input,
  JsonBlock,
  PageHeader,
  SectionHeader,
  Select,
  UnconfiguredServiceState,
} from "@/components/ui";
import { AdaptationErrorBanner } from "@/components/adaptation/AdaptationErrorBanner";
import { adaptationApi, isAdaptationServiceUnconfigured, type AdaptationResult } from "@/lib/adaptationApi";

type DiagnosticsFilters = {
  since: string;
  limit: string;
  lockTimeoutSeconds: string;
  includeOutboxChecks: string;
};

const defaultFilters: DiagnosticsFilters = {
  since: "",
  limit: "50",
  lockTimeoutSeconds: "300",
  includeOutboxChecks: "true",
};

type RepairInput = {
  issueKindsText: string;
  runId: string;
  workItemId: string;
  lockTimeoutSeconds: string;
  reason: string;
};

const defaultRepair: RepairInput = {
  issueKindsText: "QUEUED_RUN_MISSING_WORK_ITEM",
  runId: "",
  workItemId: "",
  lockTimeoutSeconds: "300",
  reason: "post-deploy check",
};

function parseIssueKinds(value: string): string[] | null {
  const raw = value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (raw.length === 0) return null;
  return raw;
}

export default function AdaptationQueuePage() {
  const [filters, setFilters] = useState<DiagnosticsFilters>(defaultFilters);
  const [diag, setDiag] = useState<Record<string, unknown> | null>(null);
  const [dryRun, setDryRun] = useState<Record<string, unknown> | null>(null);
  const [applyRes, setApplyRes] = useState<Record<string, unknown> | null>(null);
  const [repair, setRepair] = useState<RepairInput>(defaultRepair);
  const [busy, setBusy] = useState(false);
  const [lastError, setLastError] = useState<AdaptationResult<unknown> | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const unconfigured = lastError ? isAdaptationServiceUnconfigured(lastError) : false;

  const canApply = confirmText.trim() === "APPLY";

  const repairPayload = useMemo(() => {
    const issueKinds = parseIssueKinds(repair.issueKindsText);
    const payload: Record<string, unknown> = {};
    if (issueKinds) payload.issueKinds = issueKinds;
    if (repair.runId.trim()) payload.runId = repair.runId.trim();
    if (repair.workItemId.trim()) payload.workItemId = repair.workItemId.trim();
    const lts = Number.parseInt(repair.lockTimeoutSeconds, 10);
    if (!Number.isNaN(lts) && lts > 0) payload.lockTimeoutSeconds = lts;
    if (repair.reason.trim()) payload.reason = repair.reason.trim();
    return payload;
  }, [repair]);

  async function loadDiagnostics(event?: FormEvent) {
    event?.preventDefault();
    setBusy(true);
    setLastError(null);
    const params = new URLSearchParams();
    if (filters.since.trim()) params.set("since", filters.since.trim());
    if (filters.limit.trim()) params.set("limit", filters.limit.trim());
    if (filters.lockTimeoutSeconds.trim()) params.set("lockTimeoutSeconds", filters.lockTimeoutSeconds.trim());
    if (filters.includeOutboxChecks.trim()) params.set("includeOutboxChecks", filters.includeOutboxChecks.trim());
    const res = await adaptationApi.getQueueDiagnostics(params);
    setBusy(false);
    if (!res.ok) {
      setDiag(null);
      setLastError(res);
      return;
    }
    setDiag(res.data);
  }

  async function runDryRun() {
    setBusy(true);
    setLastError(null);
    const res = await adaptationApi.queueRepairDryRun(repairPayload);
    setBusy(false);
    if (!res.ok) {
      setDryRun(null);
      setLastError(res);
      return;
    }
    setDryRun(res.data);
    setApplyRes(null);
    setConfirmText("");
  }

  async function apply() {
    if (!canApply) return;
    setBusy(true);
    setLastError(null);
    const res = await adaptationApi.queueRepairApply(repairPayload);
    setBusy(false);
    if (!res.ok) {
      setApplyRes(null);
      setLastError(res);
      return;
    }
    setApplyRes(res.data);
  }

  return (
    <>
      <PageHeader
        eyebrow="Adaptation"
        title="Queue"
        description="Diagnostics and repair tools for drift/queue issues. Repairs are routed through the Conexus admin proxy."
      />

      {unconfigured ? (
        <UnconfiguredServiceState
          serviceName="Adaptation service"
          envVarName="ADAPTATION_API_BASE_URL"
          expectedLocalValue="http://localhost:5000"
          onRetry={() => void loadDiagnostics()}
        />
      ) : (
        <>
          {lastError && <AdaptationErrorBanner result={lastError} />}

          <Card>
            <SectionHeader title="Queue diagnostics" description="Query params are forwarded to the adaptation service." />
            <form className="stack" onSubmit={loadDiagnostics}>
              <FormRow>
                <Field label="since (optional)">
                  <Input
                    value={filters.since}
                    onChange={(e) => setFilters({ ...filters, since: e.target.value })}
                    placeholder="2026-01-01T00:00:00Z"
                  />
                </Field>
                <Field label="limit">
                  <Input value={filters.limit} onChange={(e) => setFilters({ ...filters, limit: e.target.value })} />
                </Field>
              </FormRow>
              <FormRow>
                <Field label="lockTimeoutSeconds">
                  <Input
                    value={filters.lockTimeoutSeconds}
                    onChange={(e) => setFilters({ ...filters, lockTimeoutSeconds: e.target.value })}
                  />
                </Field>
                <Field label="includeOutboxChecks">
                  <Select
                    value={filters.includeOutboxChecks}
                    onChange={(e) => setFilters({ ...filters, includeOutboxChecks: e.target.value })}
                  >
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </Select>
                </Field>
              </FormRow>
              <div className="inline-actions">
                <Button type="submit" disabled={busy}>
                  Load diagnostics
                </Button>
              </div>
            </form>

            {diag ? <JsonBlock value={diag} title="Diagnostics JSON" defaultOpen={false} /> : null}
            {!diag ? <EmptyState title="No diagnostics loaded">Load diagnostics to view the raw response.</EmptyState> : null}
          </Card>

          <Card>
            <SectionHeader
              title="Queue repair"
              description="Start with dry-run. Apply requires explicit confirmation text and should be used carefully."
            />

        <div className="stack">
          <FormRow>
            <Field label="issueKinds (comma-separated)">
              <Input
                value={repair.issueKindsText}
                onChange={(e) => setRepair({ ...repair, issueKindsText: e.target.value })}
                placeholder="QUEUED_RUN_MISSING_WORK_ITEM"
              />
            </Field>
            <Field label="lockTimeoutSeconds (optional)">
              <Input
                value={repair.lockTimeoutSeconds}
                onChange={(e) => setRepair({ ...repair, lockTimeoutSeconds: e.target.value })}
              />
            </Field>
          </FormRow>
          <FormRow>
            <Field label="runId (optional)">
              <Input value={repair.runId} onChange={(e) => setRepair({ ...repair, runId: e.target.value })} />
            </Field>
            <Field label="workItemId (optional)">
              <Input
                value={repair.workItemId}
                onChange={(e) => setRepair({ ...repair, workItemId: e.target.value })}
              />
            </Field>
          </FormRow>
          <Field label="reason (optional)">
            <Input value={repair.reason} onChange={(e) => setRepair({ ...repair, reason: e.target.value })} />
          </Field>

          <div className="inline-actions">
            <Button type="button" disabled={busy} onClick={() => void runDryRun()}>
              Run dry-run
            </Button>
            {dryRun ? <Badge tone="info">dry-run ready</Badge> : <Badge tone="neutral">dry-run not run</Badge>}
          </div>

          {dryRun ? <JsonBlock value={dryRun} title="Repair dry-run JSON" defaultOpen={false} /> : null}

          <div className="stack" style={{ maxWidth: 420 }}>
            <Field label='Type "APPLY" to enable repair apply'>
              <Input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} placeholder="APPLY" />
            </Field>
            <div className="inline-actions">
              <Button type="button" disabled={busy || !dryRun || !canApply} onClick={() => void apply()}>
                Apply repair
              </Button>
              {!dryRun ? (
                <span className="muted">Run dry-run first.</span>
              ) : !canApply ? (
                <span className="muted">Confirmation required.</span>
              ) : (
                <span className="muted">Ready.</span>
              )}
            </div>
          </div>

          {applyRes ? <JsonBlock value={applyRes} title="Repair apply JSON" defaultOpen={false} /> : null}
        </div>
          </Card>
        </>
      )}
    </>
  );
}

