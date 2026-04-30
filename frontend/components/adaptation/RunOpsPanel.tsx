"use client";

import { useState } from "react";
import { Badge, Button, Card, Field, Input, SectionHeader, Textarea } from "@/components/ui";
import { adaptationApi, type AdaptationResult } from "@/lib/adaptationApi";

function newIdempotencyKey(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export function RunOpsPanel({
  runId,
  runStatus,
  onRefresh,
  onError,
  onSuccess,
}: {
  runId: string;
  runStatus: string | null | undefined;
  onRefresh: () => Promise<void>;
  onError: (r: AdaptationResult<unknown>) => void;
  onSuccess: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const status = (runStatus ?? "").trim();
  const statusLower = status.toLowerCase();
  const terminal = statusLower === "completed" || statusLower === "failed" || statusLower === "cancelled";

  async function run(action: () => Promise<AdaptationResult<unknown>>, success: string) {
    setBusy(true);
    const res = await action();
    setBusy(false);
    if (!res.ok) {
      onError(res);
      return;
    }
    setCancelOpen(false);
    setCancelReason("");
    onSuccess(success);
    await onRefresh();
  }

  return (
    <Card>
      <SectionHeader
        title="Run operations"
        description="These actions go through the Conexus admin proxy (identity injected server-side)."
      />

      <div className="inline-actions" style={{ marginBottom: "var(--space-3)" }}>
        <span className="muted">status:</span>
        <Badge tone={terminal ? "neutral" : "info"}>{status || "—"}</Badge>
      </div>

      <div className="stack">
        <div className="inline-actions">
          {!cancelOpen ? (
            <Button type="button" disabled={busy || terminal} onClick={() => setCancelOpen(true)}>
              Cancel run
            </Button>
          ) : (
            <div className="stack" style={{ maxWidth: 520 }}>
              <p className="muted">
                Cancelling is irreversible. Provide a short operator reason for audit/debugging.
              </p>
              <Field label="Cancel reason (optional)">
                <Textarea
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  rows={3}
                  placeholder="operator cancelled from BO"
                />
              </Field>
              <div className="inline-actions">
                <Button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    void run(
                      () => adaptationApi.cancelRun(runId, { reason: cancelReason.trim() || null }),
                      "Run cancellation requested.",
                    )
                  }
                >
                  Confirm cancel
                </Button>
                <Button type="button" variant="secondary" disabled={busy} onClick={() => setCancelOpen(false)}>
                  Back
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="inline-actions">
          <Button
            type="button"
            disabled={busy}
            onClick={() =>
              void run(
                () => adaptationApi.retryRun(runId, { idempotencyKey: newIdempotencyKey() }),
                "Run retry requested.",
              )
            }
          >
            Retry run
          </Button>

          <Button
            type="button"
            variant="secondary"
            disabled={busy}
            onClick={() =>
              void run(
                () => adaptationApi.resumeRun(runId, { idempotencyKey: newIdempotencyKey() }),
                "Run resume requested.",
              )
            }
          >
            Resume run
          </Button>
        </div>
      </div>
    </Card>
  );
}

