"use client";

import { useEffect, useState } from "react";
import { Badge, Button, Card, Field, Input, JsonBlock, SectionHeader } from "@/components/ui";
import { adaptationApi, type AdaptationResult } from "@/lib/adaptationApi";

type LoadState = "idle" | "loading" | "ok" | "404" | "error";

export function DriftOpsPanel({
  profileId,
  onError,
}: {
  profileId: string;
  onError: (r: AdaptationResult<unknown>) => void;
}) {
  const [load, setLoad] = useState<LoadState>("idle");
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [kind, setKind] = useState("LiveQualityDrift");

  async function refresh() {
    setLoad("loading");
    const res = await adaptationApi.getProfileDriftStatus(profileId);
    if (!res.ok) {
      setStatus(null);
      if (res.status === 404) setLoad("404");
      else setLoad("error");
      onError(res);
      return;
    }
    setStatus(res.data);
    setLoad("ok");
  }

  async function check() {
    setBusy(true);
    const res = await adaptationApi.checkProfileDrift(profileId, { kind: kind.trim() || null });
    setBusy(false);
    if (!res.ok) {
      onError(res);
      return;
    }
    await refresh();
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]);

  return (
    <Card>
      <SectionHeader
        title="Drift"
        description="View current drift status and trigger a drift check. Responses are shown as raw JSON."
      />

      <div className="inline-actions" style={{ marginBottom: "var(--space-3)" }}>
        <Badge tone={load === "ok" ? "success" : load === "loading" ? "info" : load === "404" ? "neutral" : "neutral"}>
          {load === "ok" ? "status loaded" : load === "loading" ? "loading" : load === "404" ? "no status (404)" : load === "error" ? "error" : "idle"}
        </Badge>
        <Button type="button" variant="secondary" disabled={busy || load === "loading"} onClick={() => void refresh()}>
          Refresh status
        </Button>
      </div>

      <div className="stack" style={{ maxWidth: 520 }}>
        <Field label="Check kind (optional)">
          <Input value={kind} onChange={(e) => setKind(e.target.value)} placeholder="LiveQualityDrift" />
        </Field>
        <div className="inline-actions">
          <Button type="button" disabled={busy} onClick={() => void check()}>
            Check drift
          </Button>
        </div>
      </div>

      {status ? <JsonBlock value={status} title="Drift status JSON" defaultOpen={false} /> : null}
    </Card>
  );
}

