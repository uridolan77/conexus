"use client";

import { useEffect, useState } from "react";
import { Card, KeyValueGrid, SectionHeader, StatusBadge } from "@/components/ui";
import { BACKEND_BASE } from "@/lib/api";

export function HealthCard() {
  const [health, setHealth] = useState<{ status: string } | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    async function fetchHealth() {
      try {
        const res = await fetch(`${BACKEND_BASE}/health`, { cache: "no-store" });
        if (res.ok) setHealth((await res.json()) as { status: string });
      } finally {
        setLoaded(true);
      }
    }
    void fetchHealth();
  }, []);

  return (
    <Card>
      <SectionHeader
        title="Backend Health"
        description="Checks the FastAPI service that powers auth, provider setup, projects, and gateway calls."
      />
      {!loaded ? (
        <p className="state-text">Checking backend...</p>
      ) : health ? (
        <KeyValueGrid
          items={[
            {
              label: "Status",
              value: <StatusBadge status={health.status === "ok" ? "ok" : "failed"} />,
            },
            { label: "Endpoint", value: <code>/health</code> },
          ]}
        />
      ) : (
        <KeyValueGrid
          items={[
            { label: "Status", value: <StatusBadge status="failed" /> },
            { label: "Next step", value: "Start the backend and refresh this page." },
          ]}
        />
      )}
    </Card>
  );
}
