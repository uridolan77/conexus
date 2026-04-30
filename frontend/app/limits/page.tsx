"use client";

import { Card, EmptyState, LinkButton, PageHeader, SectionHeader } from "@/components/ui";

export default function LimitsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Operations"
        title="Limits"
        description="Central landing page for limit and reservation operations."
      />

      <Card>
        <SectionHeader title="Limit modes" description="How Conexus enforces usage limits per project." />
        <ul>
          <li>
            <strong>disabled</strong>: no limits are enforced.
          </li>
          <li>
            <strong>soft</strong>: requests are allowed but warnings/metadata may be recorded for operator follow-up.
          </li>
          <li>
            <strong>hard</strong>: requests can be blocked when limits are exceeded.
          </li>
        </ul>
      </Card>

      <Card>
        <SectionHeader title="Project limits" description="Limits are configured per project today." />
        <EmptyState
          title="Manage limits per project"
          action={<LinkButton href="/projects" variant="primary">Open Projects</LinkButton>}
        >
          Use the Projects page to configure daily request/token limits and monthly cost limits.
        </EmptyState>
      </Card>

      <Card>
        <SectionHeader title="Stale reservations" description="Repair tooling for unreconciled reservations (if present)." />
        <LinkButton href="/projects/stale-reservations" variant="secondary">
          View stale reservations
        </LinkButton>
      </Card>
    </>
  );
}

