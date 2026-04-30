import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import UsagePage from "@/app/usage/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("UsagePage", () => {
  it("renders summary cards from backend responses", async () => {
    const now = new Date().toISOString();
    const summary = {
      window: "30d",
      created_from: now,
      created_to: now,
      currency: "USD",
      total_requests: 10,
      completed_requests: 8,
      failed_requests: 2,
      success_rate: 0.8,
      fallback_count: 1,
      fallback_rate: 0.1,
      total_prompt_tokens: 100,
      total_completion_tokens: 50,
      total_tokens: 150,
      estimated_cost: 0.12,
      avg_latency_ms: 42,
    };
    const byProject = {
      window: "30d",
      created_from: now,
      created_to: now,
      currency: "USD",
      items: [
        {
          project_id: "p1",
          project_name: "Payments",
          total_requests: 10,
          completed_requests: 8,
          failed_requests: 2,
          success_rate: 0.8,
          fallback_count: 1,
          fallback_rate: 0.1,
          total_prompt_tokens: 100,
          total_completion_tokens: 50,
          total_tokens: 150,
          estimated_cost: 0.12,
          avg_latency_ms: 42,
        },
      ],
    };
    const byProvider = {
      window: "30d",
      created_from: now,
      created_to: now,
      currency: "USD",
      items: [
        {
          provider: "openai",
          total_requests: 10,
          completed_requests: 8,
          failed_requests: 2,
          success_rate: 0.8,
          fallback_count: 1,
          fallback_rate: 0.1,
          total_prompt_tokens: 100,
          total_completion_tokens: 50,
          total_tokens: 150,
          estimated_cost: 0.12,
          avg_latency_ms: 42,
        },
      ],
    };
    const timeseries = {
      window: "30d",
      created_from: now,
      created_to: now,
      interval: "day",
      currency: "USD",
      items: [
        {
          bucket_start: now,
          bucket_end: now,
          total_requests: 10,
          completed_requests: 8,
          failed_requests: 2,
          success_rate: 0.8,
          fallback_count: 1,
          fallback_rate: 0.1,
          total_prompt_tokens: 100,
          total_completion_tokens: 50,
          total_tokens: 150,
          estimated_cost: 0.12,
          avg_latency_ms: 42,
        },
      ],
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/usage/summary")) return jsonResponse(summary);
        if (u.includes("/admin/usage/by-project")) return jsonResponse(byProject);
        if (u.includes("/admin/usage/by-provider")) return jsonResponse(byProvider);
        if (u.includes("/admin/usage/timeseries")) return jsonResponse(timeseries);
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<UsagePage />);

    expect(await screen.findByText("Usage")).toBeInTheDocument();
    expect(await screen.findByText("Payments")).toBeInTheDocument();
    expect(await screen.findByText("Estimated Cost")).toBeInTheDocument();
  });
});

