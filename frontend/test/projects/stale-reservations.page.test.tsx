import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import StaleReservationsPage from "@/app/projects/stale-reservations/page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

const adminSessionFetch = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...mod,
    adminSessionFetch: (...args: Parameters<typeof mod.adminSessionFetch>) =>
      adminSessionFetch(...args),
  };
});

describe("StaleReservationsPage", () => {
  beforeEach(() => {
    adminSessionFetch.mockReset();
  });

  it("loads stale list and dry-run calls repair endpoint", async () => {
    adminSessionFetch.mockImplementation((input: RequestInfo) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/limits/reservations/stale")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              now: "2020-01-01T00:00:00Z",
              older_than_seconds: 900,
              total_count: 1,
              oldest_age_seconds: 120,
              items: [
                {
                  reservation_id: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                  project_id: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                  created_at: "2020-01-01T00:00:00Z",
                  age_seconds: 120,
                  daily_window_id: "c",
                  monthly_window_id: null,
                  request_slots: 1,
                  tokens_reserved: 10,
                  cost_reserved: 0,
                  gateway_request_id: null,
                  gateway_request_status: null,
                  gateway_request_completed_at: null,
                  repair_kind: "no_gateway_request",
                  recommended_action: "release",
                },
              ],
            }),
            { status: 200 },
          ),
        );
      }
      if (url.includes("/repair/dry-run")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              reservation_id: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
              project_id: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
              repair_kind: "no_gateway_request",
              action: "release_orphan",
              applied: false,
              message: "Would release",
              before: {},
              after: {},
            }),
            { status: 200 },
          ),
        );
      }
      return Promise.resolve(new Response("{}", { status: 500 }));
    });

    render(<StaleReservationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Stale limit reservations")).toBeInTheDocument();
    });

    const dry = await screen.findByRole("button", { name: /Dry-run/i });
    fireEvent.click(dry);

    await waitFor(() => {
      expect(adminSessionFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          "/admin/projects/limits/reservations/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/repair/dry-run",
        ),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("renders empty state when no items", async () => {
    adminSessionFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          now: "2020-01-01T00:00:00Z",
          older_than_seconds: 900,
          total_count: 0,
          oldest_age_seconds: null,
          items: [],
        }),
        { status: 200 },
      ),
    );

    render(<StaleReservationsPage />);

    await waitFor(() => {
      expect(screen.getByText("No stale reservations")).toBeInTheDocument();
    });
  });
});
