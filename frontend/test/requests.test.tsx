import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import RequestsPage from "@/app/requests/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("RequestsPage", () => {
  it("renders rows, highlights failures, and shows API key column", async () => {
    const projects = [{ id: "p1", name: "Payments", created_at: "", active_key_count: 1, total_request_count: 2 }];
    const requests = {
      items: [
        {
          id: "1",
          request_id: "req_ok",
          project_id: "p1",
          project_name: "Payments",
          api_key_id: "k1",
          api_key_prefix: "cx_live_abcd",
          requested_model: "gpt-4o-mini",
          provider: "openai",
          model: "gpt-4o-mini",
          status: "completed",
          latency_ms: 12,
          prompt_tokens: 1,
          completion_tokens: 1,
          total_tokens: 2,
          estimated_cost: 0.001,
          fallback_used: false,
          error_code: null,
          error_message: null,
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          duration_bucket: "fast",
          cost_bucket: "low",
        },
        {
          id: "2",
          request_id: "req_failed",
          project_id: "p1",
          project_name: "Payments",
          api_key_id: "k2",
          api_key_prefix: "cx_live_efgh",
          requested_model: "conexus-default",
          provider: null,
          model: null,
          status: "failed",
          latency_ms: 0,
          prompt_tokens: null,
          completion_tokens: null,
          total_tokens: null,
          estimated_cost: null,
          fallback_used: false,
          error_code: "ProviderUnavailableError",
          error_message: "timed out",
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          duration_bucket: null,
          cost_bucket: "free_or_unknown",
        },
      ],
      limit: 50,
      offset: 0,
      total: 2,
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/projects")) return jsonResponse(projects);
        if (u.includes("/admin/requests?")) return jsonResponse(requests);
        if (u.includes("/admin/requests/")) return jsonResponse(requests.items[0]);
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<RequestsPage />);

    expect(await screen.findByText("req_ok")).toBeInTheDocument();
    expect(await screen.findByText("req_failed")).toBeInTheDocument();

    // API key prefix should be visible in the table.
    expect(await screen.findByText("cx_live_abcd")).toBeInTheDocument();

    // Failed rows should be visually distinct.
    await waitFor(() => {
      const cell = screen.getByText("req_failed");
      const row = cell.closest("tr");
      expect(row).toHaveClass("row-warning");
    });
  });
});

