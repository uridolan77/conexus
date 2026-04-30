import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProjectKeysCard } from "@/components/projects/ProjectKeysCard";
import type { ApiKeyCreated, ProjectRow } from "@/lib/types";

const selectedProject: ProjectRow = {
  id: "proj-1",
  name: "payments-prod",
  created_at: "2024-01-01T00:00:00Z",
  active_key_count: 1,
  total_request_count: 42,
};

const latestKey: ApiKeyCreated = {
  id: "key-1",
  project_id: "proj-1",
  label: null,
  prefix: "cnx_abc",
  created_at: "2024-01-01T00:00:00Z",
  revoked_at: null,
  plaintext: "cnx_abc_SUPERSECRETPLAINTEXTVALUE",
};

describe("ProjectKeysCard — key shown once behavior", () => {
  it("does NOT render the plaintext key when latestIssuedKey is null", () => {
    render(
      <ProjectKeysCard
        projectId="proj-1"
        selectedProject={selectedProject}
        keys={[]}
        loadingKeys={false}
        latestIssuedKey={null}
        onKeyIssued={vi.fn()}
        onKeyRevoked={vi.fn()}
      />,
    );
    expect(screen.queryByText(/SUPERSECRETPLAINTEXTVALUE/)).not.toBeInTheDocument();
  });

  it("renders the plaintext key when latestIssuedKey is set", () => {
    render(
      <ProjectKeysCard
        projectId="proj-1"
        selectedProject={selectedProject}
        keys={[]}
        loadingKeys={false}
        latestIssuedKey={latestKey}
        onKeyIssued={vi.fn()}
        onKeyRevoked={vi.fn()}
      />,
    );
    expect(screen.getByText("cnx_abc_SUPERSECRETPLAINTEXTVALUE")).toBeInTheDocument();
  });

  it("renders the 'shown once' warning when key is just issued", () => {
    render(
      <ProjectKeysCard
        projectId="proj-1"
        selectedProject={selectedProject}
        keys={[]}
        loadingKeys={false}
        latestIssuedKey={latestKey}
        onKeyIssued={vi.fn()}
        onKeyRevoked={vi.fn()}
      />,
    );
    // The alert title contains "shown once"
    const matches = screen.getAllByText(/shown once/i);
    expect(matches.length).toBeGreaterThan(0);
  });
});
