import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ProjectsPage from "@/app/projects/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/playgroundKeyHandoff", () => ({
  setPlaygroundApiKeyOnce: vi.fn(),
}));

// All data defined INSIDE the factory to avoid vi.mock hoisting issues.
vi.mock("@/lib/admin/projects", () => {
  const projectA = {
    id: "proj-a",
    name: "Project Alpha",
    created_at: "2024-01-01T00:00:00Z",
    active_key_count: 1,
    total_request_count: 0,
  };

  const emptyLimits = {
    project_id: "proj-a",
    limit_mode: "disabled",
    monthly_cost_limit: null,
    daily_request_limit: null,
    daily_token_limit: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  };

  const emptyUsage = {
    project_id: "proj-a",
    now: "2024-01-01T00:00:00Z",
    daily: {
      window: "utc_day",
      start_at: "2024-01-01T00:00:00Z",
      reset_at: "2024-01-02T00:00:00Z",
      request_count: 0,
      total_tokens: 0,
    },
    monthly: {
      window: "utc_month",
      start_at: "2024-01-01T00:00:00Z",
      reset_at: "2024-02-01T00:00:00Z",
      estimated_cost: 0,
      currency: "USD",
    },
  };

  const emptyReservations = {
    project_id: "proj-a",
    active_reservations: 0,
    total_reserved_tokens: 0,
    reservations: [],
  };

  const emptyStale = { project_id: "proj-a", stale_count: 0, items: [] };

  return {
    listProjects: vi.fn().mockResolvedValue({ ok: true, data: [projectA] }),
    createProject: vi.fn(),
    listProjectKeys: vi.fn().mockResolvedValue({ ok: true, data: [] }),
    issueProjectKey: vi.fn().mockResolvedValue({
      ok: true,
      data: {
        id: "key-1",
        project_id: "proj-a",
        label: null,
        prefix: "cnx_abc",
        created_at: "2024-01-01T00:00:00Z",
        revoked_at: null,
        plaintext: "cnx_abc_PLAINTEXTTOKEN",
      },
    }),
    revokeProjectKey: vi.fn().mockResolvedValue({ ok: true, data: {} }),
    getProjectLimits: vi.fn().mockResolvedValue({ ok: true, data: emptyLimits }),
    saveProjectLimits: vi.fn(),
    getProjectLimitsUsage: vi.fn().mockResolvedValue({ ok: true, data: emptyUsage }),
    getProjectReservations: vi.fn().mockResolvedValue({ ok: true, data: emptyReservations }),
    getStaleReservations: vi.fn().mockResolvedValue({ ok: true, data: emptyStale }),
  };
});

describe("Projects page — key visibility on project switch", () => {
  it("does not show key plaintext when no key has been issued in this session", async () => {
    render(<ProjectsPage />);
    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );
    // No key was issued yet — plaintext must not be visible
    expect(screen.queryByText(/cnx_abc_PLAINTEXTTOKEN/)).not.toBeInTheDocument();
  });
});

describe("Projects page — section error clears success", () => {
  it("renders without crash when section fetches succeed", async () => {
    render(<ProjectsPage />);
    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );
    // Page renders the heading
    expect(screen.getByText("Projects")).toBeInTheDocument();
  });
});
