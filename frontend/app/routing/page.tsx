"use client";

import { useEffect, useState } from "react";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  KeyValueGrid,
  LoadingState,
  PageHeader,
  SectionHeader,
  Table,
} from "@/components/ui";
import { BACKEND_BASE, formatApiError, readJsonSafe } from "@/lib/api";
import type { RoutingPolicy } from "@/lib/types";

export default function RoutingPage() {
  const [policy, setPolicy] = useState<RoutingPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPolicy() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${BACKEND_BASE}/admin/routing/policy`, {
          credentials: "include",
          cache: "no-store",
        });
        const body = await readJsonSafe(res);
        if (res.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!res.ok) {
          setError(formatApiError(body));
          return;
        }
        setPolicy(body as RoutingPolicy);
      } catch {
        setError("Unable to load routing policy. Check that the backend is reachable.");
      } finally {
        setLoading(false);
      }
    }

    void loadPolicy();
  }, []);

  return (
    <>
      <PageHeader
        eyebrow="Routing policy"
        title="Routing"
        description="View how Conexus resolves aliases and concrete provider models today. This page is read-only until project-level policies are introduced."
      />

      {error && <ErrorState message={error} />}

      {loading ? (
        <Card>
          <LoadingState label="Loading routing policy..." />
        </Card>
      ) : policy ? (
        <>
          <Card>
            <SectionHeader
              title="Default Policy"
              description="Current gateway behavior is static and shared by all projects."
            />
            <KeyValueGrid
              items={[
                { label: "Policy ID", value: <code>{policy.id}</code> },
                { label: "Name", value: policy.name },
                { label: "Mode", value: <Badge tone="info">{policy.mode}</Badge> },
                { label: "Default alias", value: <code>{policy.default_alias}</code> },
              ]}
            />
          </Card>

          <Card>
            <SectionHeader
              title="Alias Routes"
              description="Conexus aliases try the primary provider first, then fall back to the fallback provider on retryable provider failures."
            />
            {policy.aliases.length === 0 ? (
              <EmptyState title="No aliases configured">
                Concrete provider models still route directly by model prefix.
              </EmptyState>
            ) : (
              <Table aria-label="Routing aliases">
                <thead>
                  <tr>
                    <th>Alias</th>
                    <th>Primary provider/model</th>
                    <th>Fallback provider/model</th>
                  </tr>
                </thead>
                <tbody>
                  {policy.aliases.map((route) => (
                    <tr key={route.alias}>
                      <td>
                        <code>{route.alias}</code>
                      </td>
                      <td>
                        <strong>{route.primary_provider}</strong>
                        <br />
                        <code>{route.primary_model}</code>
                      </td>
                      <td>
                        <strong>{route.fallback_provider}</strong>
                        <br />
                        <code>{route.fallback_model}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <SectionHeader
              title="Direct Routes"
              description="Concrete provider model names bypass alias fallback and route directly to the matching provider."
            />
            <Table aria-label="Direct routing prefixes">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Model prefixes</th>
                  <th>Alias fallback</th>
                </tr>
              </thead>
              <tbody>
                {policy.direct_routes.map((route) => (
                  <tr key={route.provider}>
                    <td>
                      <strong>{route.provider}</strong>
                    </td>
                    <td>
                      {route.model_prefixes.map((prefix) => (
                        <code key={prefix}>{prefix} </code>
                      ))}
                    </td>
                    <td>{route.fallback_enabled ? "Enabled" : "Disabled"}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </>
      ) : null}
    </>
  );
}
