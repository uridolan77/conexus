"use client";

import { FormEvent, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CompactId,
  ConfirmAction,
  CopyButton,
  EmptyState,
  Field,
  FormRow,
  Input,
  KeyValueGrid,
  LoadingState,
  SectionHeader,
  StatusBadge,
  Table,
} from "@/components/ui";
import { formatDate } from "@/lib/api";
import { issueProjectKey, revokeProjectKey } from "@/lib/admin/projects";
import type { ApiKeyCreated, ApiKeyRow, ProjectRow } from "@/lib/types";

export function ProjectKeysCard({
  projectId,
  selectedProject,
  keys,
  loadingKeys,
  latestIssuedKey,
  onKeyIssued,
  onKeyRevoked,
}: {
  projectId: string | null;
  selectedProject: ProjectRow | undefined;
  keys: ApiKeyRow[];
  loadingKeys: boolean;
  latestIssuedKey: ApiKeyCreated | null;
  onKeyIssued: (key: ApiKeyCreated) => void;
  onKeyRevoked: () => void;
}) {
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [issuingKey, setIssuingKey] = useState(false);
  const [revokingKeyId, setRevokingKeyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleIssueKey(e: FormEvent) {
    e.preventDefault();
    if (!projectId) return;
    setError(null);
    setIssuingKey(true);
    try {
      const result = await issueProjectKey(projectId, newKeyLabel.trim() || undefined);
      if (!result.ok) {
        setError(result.error.message);
        return;
      }
      setNewKeyLabel("");
      onKeyIssued(result.data);
    } finally {
      setIssuingKey(false);
    }
  }

  async function handleRevokeKey(keyId: string) {
    if (!projectId) return;
    setError(null);
    setRevokingKeyId(keyId);
    try {
      const result = await revokeProjectKey(projectId, keyId);
      if (!result.ok) {
        setError(result.error.message);
        return;
      }
      onKeyRevoked();
    } finally {
      setRevokingKeyId(null);
    }
  }

  return (
    <Card>
      <SectionHeader
        title="Project API Keys"
        description={
          selectedProject
            ? `Keys for ${selectedProject.name}. Plaintext keys are shown once immediately after creation.`
            : "Select a project to manage keys."
        }
      />
      {!projectId ? (
        <EmptyState title="Select a project">
          Project API keys authenticate gateway clients. Choose a project above to issue or revoke keys.
        </EmptyState>
      ) : (
        <>
          {error && <Alert tone="danger">{error}</Alert>}
          <form className="stack" onSubmit={handleIssueKey}>
            <FormRow>
              <Field label="Key label" hint="Optional. Use labels like prod, staging, or CI.">
                <Input
                  value={newKeyLabel}
                  onChange={(e) => setNewKeyLabel(e.target.value)}
                  placeholder="prod"
                />
              </Field>
            </FormRow>
            <div className="inline-actions">
              <Button type="submit" disabled={issuingKey}>
                {issuingKey ? "Issuing..." : "Issue key"}
              </Button>
            </div>
          </form>

          {latestIssuedKey && (
            <Alert tone="warning" title="New project API key shown once">
              <div className="stack">
                <p>
                  Copy this key now. Conexus will only show the prefix later and the plaintext value cannot be recovered.
                </p>
                <pre>{latestIssuedKey.plaintext}</pre>
                <div className="inline-actions">
                  <CopyButton value={latestIssuedKey.plaintext} label="Copy key" />
                </div>
              </div>
            </Alert>
          )}

          {selectedProject && (
            <KeyValueGrid
              items={[
                { label: "Project ID", value: <CompactId value={selectedProject.id} /> },
                { label: "Active keys", value: selectedProject.active_key_count },
                { label: "Total requests", value: selectedProject.total_request_count },
              ]}
            />
          )}

          {loadingKeys ? (
            <LoadingState label="Loading project keys..." />
          ) : keys.length === 0 ? (
            <EmptyState title="No keys for this project">
              Issue a key when a client is ready to call the gateway. Store the plaintext value outside Conexus immediately.
            </EmptyState>
          ) : (
            <Table aria-label="Project API keys">
              <thead>
                <tr>
                  <th>Prefix</th>
                  <th>Label</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Revoked</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr key={key.id} className={key.revoked_at ? "row-muted" : undefined}>
                    <td><code>{key.prefix}</code></td>
                    <td>{key.label ?? "-"}</td>
                    <td>
                      <StatusBadge status={key.revoked_at ? "revoked" : "active"} />
                    </td>
                    <td>{formatDate(key.created_at)}</td>
                    <td>{formatDate(key.revoked_at)}</td>
                    <td>
                      <ConfirmAction
                        message={`Revoke key ${key.prefix}? This client will no longer be able to call the gateway with it.`}
                        onConfirm={() => void handleRevokeKey(key.id)}
                        disabled={Boolean(key.revoked_at)}
                      >
                        {revokingKeyId === key.id ? "Revoking..." : "Revoke"}
                      </ConfirmAction>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </>
      )}
    </Card>
  );
}
