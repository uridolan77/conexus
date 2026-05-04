import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import DashboardPage from "@/app/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("DashboardPage", () => {
  it("renders M6 dashboard summary and latest errors", async () => {
    const now = new Date().toISOString();
    const projects = [
      { id: "p1", name: "Payments", created_at: now, active_key_count: 1, total_request_count: 2 },
    ];
    const providers = [
      {
        id: "provider1",
        provider: "openai",
        label: "OpenAI",
        key_mask: "sk-...",
        is_active: true,
        revoked_at: null,
        last_test_status: "ok",
        last_test_error: null,
        last_tested_at: now,
        created_at: now,
        updated_at: now,
      },
    ];
    const summary = {
      requests_today: 2,
      success_rate: 0.5,
      failed_requests: 1,
      average_latency_ms: 150,
      estimated_cost_today: 0.01,
      latest_errors: [
        {
          request_id: "req_failed",
          project_id: "p1",
          project_name: "Payments",
          requested_model: "conexus-fast",
          provider: "anthropic",
          model: "claude-sonnet-4-20250514",
          error_code: "provider_timeout",
          error_message: "provider timed out",
          created_at: now,
        },
      ],
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/projects")) return jsonResponse(projects);
        if (u.includes("/admin/providers")) return jsonResponse(providers);
        if (u.includes("/admin/dashboard/summary")) return jsonResponse(summary);
        if (u.includes("/health")) return jsonResponse({ status: "ok" });
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<DashboardPage />);

    expect(await screen.findByText("Requests today")).toBeInTheDocument();
    expect(await screen.findByText("Latest Errors")).toBeInTheDocument();
    expect(await screen.findByText("req_failed")).toBeInTheDocument();
    expect(await screen.findByText("provider_timeout")).toBeInTheDocument();
  });
});
