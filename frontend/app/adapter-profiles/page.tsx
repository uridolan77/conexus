"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  DetailDrawer,
  EmptyState,
  ErrorState,
  JsonBlock,
  KeyValueGrid,
  LoadingState,
  PageHeader,
  SectionHeader,
  Table,
} from "@/components/ui";
import { formatDateTime, formatNullable } from "@/lib/format";
import { redactSensitiveObject } from "@/lib/redaction";
import {
  getAdapterProfile,
  listAdapterProfileActivations,
  listAdapterProfiles,
} from "@/lib/admin/adapterProfiles";
import type {
  GatewayAdapterProfileActivationRow,
  GatewayAdapterProfileDetail,
  GatewayAdapterProfileRow,
} from "@/lib/types";

const WARNING_TEXT =
  "Adapter profile registration is supported. Canary, promote, rollback, and traffic splitting may still be staged depending on backend configuration. This page shows gateway registry state, not guaranteed live traffic behavior.";

const DEFAULT_LIMIT = 50;

export default function AdapterProfilesPage() {
  const [rows, setRows] = useState<GatewayAdapterProfileRow[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string>("");
  const [detail, setDetail] = useState<GatewayAdapterProfileDetail | null>(null);
  const [activations, setActivations] = useState<GatewayAdapterProfileActivationRow[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  async function loadList(nextOffset: number) {
    setLoading(true);
    setError(null);
    try {
      const result = await listAdapterProfiles({ limit: DEFAULT_LIMIT, offset: nextOffset });
      if (!result.ok) {
        setError(result.error.message);
        setRows([]);
        setTotal(null);
        return;
      }
      setRows(result.data.items);
      setTotal(result.data.total);
      setOffset(result.data.offset);
    } finally {
      setLoading(false);
    }
  }

  async function loadDetail(gatewayProfileId: string) {
    setDetailLoading(true);
    setDetailError(null);
    setDetail(null);
    setActivations([]);
    setSelectedId(gatewayProfileId);
    setOpen(true);
    try {
      const [detailRes, actRes] = await Promise.all([
        getAdapterProfile(gatewayProfileId),
        listAdapterProfileActivations(gatewayProfileId),
      ]);
      if (!detailRes.ok) {
        setDetailError(detailRes.error.message);
        return;
      }
      if (!actRes.ok) {
        setDetailError(actRes.error.message);
        setDetail(detailRes.data);
        return;
      }
      setDetail(detailRes.data);
      setActivations(actRes.data);
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    void loadList(0);
  }, []);

  const canPrev = offset > 0;
  const canNext = total != null ? offset + DEFAULT_LIMIT < total : false;

  const rangeLabel = useMemo(() => {
    if (total == null) return "—";
    if (total === 0) return "0";
    const start = Math.min(total, offset + 1);
    const end = Math.min(total, offset + rows.length);
    return `${start}–${end} of ${total}`;
  }, [total, offset, rows.length]);

  return (
    <>
      <PageHeader
        eyebrow="Routing"
        title="Adapter Profiles"
        description="Read-only registry of adapter profiles stored in Conexus."
      />

      <Alert tone="warning">{WARNING_TEXT}</Alert>

      {error && <ErrorState message={error} />}

      <Card>
        <SectionHeader
          title="Registry"
          description={`Showing ${rangeLabel}`}
        />

        {loading ? (
          <LoadingState label="Loading adapter profiles..." />
        ) : rows.length === 0 ? (
          <EmptyState title="No adapter profiles registered">
            No gateway adapter profiles were found in the registry.
          </EmptyState>
        ) : (
          <>
            <Table aria-label="Gateway adapter profiles">
              <thead>
                <tr>
                  <th>gateway_profile_id</th>
                  <th>adapter_profile_id</th>
                  <th>domain_key</th>
                  <th>status</th>
                  <th>composite_score</th>
                  <th>profile_version</th>
                  <th>evidence_hash</th>
                  <th>semantic_context_hash</th>
                  <th>slod_model_version</th>
                  <th>created_at</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.gateway_profile_id}>
                    <td><code className="wrap-anywhere">{r.gateway_profile_id}</code></td>
                    <td><code className="wrap-anywhere">{r.adapter_profile_id}</code></td>
                    <td><code className="wrap-anywhere">{r.domain_key}</code></td>
                    <td>{r.status}</td>
                    <td>{formatNullable(r.composite_score)}</td>
                    <td>{formatNullable(r.profile_version)}</td>
                    <td><code className="wrap-anywhere">{formatNullable(r.evidence_hash)}</code></td>
                    <td><code className="wrap-anywhere">{formatNullable(r.semantic_context_hash)}</code></td>
                    <td>{formatNullable(r.slod_model_version)}</td>
                    <td>{formatDateTime(r.created_at)}</td>
                    <td>
                      <Button type="button" variant="secondary" onClick={() => void loadDetail(r.gateway_profile_id)}>
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>

            <div className="inline-actions pagination-actions">
              <Button type="button" variant="secondary" disabled={!canPrev} onClick={() => void loadList(Math.max(0, offset - DEFAULT_LIMIT))}>
                Previous
              </Button>
              <span className="muted">Offset {offset}</span>
              <Button type="button" variant="secondary" disabled={!canNext} onClick={() => void loadList(offset + DEFAULT_LIMIT)}>
                Next
              </Button>
            </div>
          </>
        )}
      </Card>

      <DetailDrawer
        open={open}
        onClose={() => setOpen(false)}
        title="Adapter profile detail"
      >
        {detailLoading ? (
          <LoadingState label="Loading adapter profile..." />
        ) : detailError ? (
          <ErrorState message={detailError} />
        ) : detail ? (
          <div className="stack">
            <KeyValueGrid
              items={[
                { label: "gateway_profile_id", value: <code className="wrap-anywhere">{detail.gateway_profile_id}</code> },
                { label: "adapter_profile_id", value: <code className="wrap-anywhere">{detail.adapter_profile_id}</code> },
                { label: "domain_key", value: <code className="wrap-anywhere">{detail.domain_key}</code> },
                { label: "status", value: detail.status },
                { label: "composite_score", value: formatNullable(detail.composite_score) },
                { label: "profile_version", value: formatNullable(detail.profile_version) },
                { label: "evidence_hash", value: <code className="wrap-anywhere">{formatNullable(detail.evidence_hash)}</code> },
                { label: "semantic_context_hash", value: <code className="wrap-anywhere">{formatNullable(detail.semantic_context_hash)}</code> },
                { label: "slod_model_version", value: formatNullable(detail.slod_model_version) },
                { label: "source_run_id", value: formatNullable(detail.source_run_id) },
                { label: "source_plan_id", value: formatNullable(detail.source_plan_id) },
                { label: "created_at", value: formatDateTime(detail.created_at) },
                { label: "updated_at", value: formatDateTime(detail.updated_at) },
                { label: "published_at", value: detail.published_at ? formatDateTime(detail.published_at) : "—" },
              ]}
            />

            <Card className="card-muted">
              <SectionHeader title="Activation history" description="Read-only activation events for this gateway profile id." />
              {activations.length === 0 ? (
                <EmptyState title="No activations">No activation history found.</EmptyState>
              ) : (
                <Table aria-label="Adapter profile activations">
                  <thead>
                    <tr>
                      <th>created_at</th>
                      <th>status</th>
                      <th>canary_percent</th>
                      <th>previous_gateway_profile_id</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activations.map((a) => (
                      <tr key={a.id}>
                        <td>{formatDateTime(a.created_at)}</td>
                        <td>{a.status}</td>
                        <td>{formatNullable(a.canary_percent)}</td>
                        <td><code className="wrap-anywhere">{formatNullable(a.previous_gateway_profile_id)}</code></td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card>

            <JsonBlock value={redactSensitiveObject(detail.metadata)} title="Metadata JSON" defaultOpen={false} />
          </div>
        ) : (
          <EmptyState title="Select a profile">Pick a row from the table to view details.</EmptyState>
        )}
      </DetailDrawer>
    </>
  );
}

