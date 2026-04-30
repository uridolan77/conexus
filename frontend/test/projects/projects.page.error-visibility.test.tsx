import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ProjectsPage from "@/app/projects/page";
import type {
  ApiKeyRow,
  ProjectLimits,
  ProjectLimitsReservations,
  ProjectLimitsUsage,
  ProjectRow,
  StaleReservationsList,
} from "@/lib/types";

vi.mock("@/lib/admin/projects", () => {
  const project: ProjectRow = {
    id: "proj-1",
    name: "Payments",
    created_at: "2024-01-01T00:00:00Z",
    active_key_count: 1,
    total_request_count: 12,
  };

  const keys: ApiKeyRow[] = [];

  const limits: ProjectLimits = {
    project_id: "proj-1",
    limit_mode: "hard",
    monthly_cost_limit: 100,
    daily_request_limit: 500,
    daily_token_limit: 50000,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  };

  const usage: ProjectLimitsUsage = {
    project_id: "proj-1",
    now: "2024-01-01T00:00:00Z",
    daily: {
      window: "utc_day",
      start_at: "2024-01-01T00:00:00Z",
      reset_at: "2024-01-02T00:00:00Z",
      request_count: 10,
      total_tokens: 1000,
    },
    monthly: {
      window: "utc_month",
      start_at: "2024-01-01T00:00:00Z",
      reset_at: "2024-02-01T00:00:00Z",
      estimated_cost: 12.5,
      currency: "USD",
    },
  };

  const reservations: ProjectLimitsReservations = {
    project_id: "proj-1",
    now: "2024-01-01T00:00:00Z",
    daily: {
      window_start: "2024-01-01T00:00:00Z",
      window_end: "2024-01-02T00:00:00Z",
      request_count_reserved: 12,
      request_count_completed: 10,
      token_count_reserved: 1200,
      token_count_completed: 1000,
    },
    monthly: {
      window_start: "2024-01-01T00:00:00Z",
      window_end: "2024-02-01T00:00:00Z",
      cost_reserved: 15,
      cost_completed: 12.5,
    },
  };

  const stale: StaleReservationsList = {
    now: "2024-01-01T00:00:00Z",
    older_than_seconds: 900,
    total_count: 0,
    oldest_age_seconds: null,
    items: [],
  };

  return {
    listProjects: vi.fn().mockResolvedValue({ ok: true, data: [project] }),
    listProjectKeys: vi.fn().mockResolvedValue({
      ok: false,
      error: { message: "Unable to load keys." },
    }),
    getProjectLimits: vi.fn().mockResolvedValue({ ok: true, data: limits }),
    getProjectLimitsUsage: vi.fn().mockResolvedValue({ ok: true, data: usage }),
    getProjectReservations: vi.fn().mockResolvedValue({ ok: true, data: reservations }),
    getStaleReservations: vi.fn().mockResolvedValue({ ok: true, data: stale }),
  };
});

describe("ProjectsPage error visibility", () => {
  it("shows an error banner when a section fetch fails", async () => {
    render(<ProjectsPage />);

    expect(await screen.findByText("Projects")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Unable to load keys.");
    });

    // The page remains usable instead of being replaced by a global hard-failure state.
    expect(screen.getByText("Payments")).toBeInTheDocument();
  });
});
