import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import UsagePage from "@/app/usage/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("UsagePage", () => {
  it("renders summary cards and breakdowns from backend responses", async () => {
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
    expect(await screen.findByText("Estimated cost")).toBeInTheDocument();
    expect((await screen.findAllByText("80.0%")).length).toBeGreaterThan(0);
  });

  it("renders cleanly for empty usage and null avg latency", async () => {
    const now = new Date().toISOString();
    const summary = {
      window: "30d",
      created_from: now,
      created_to: now,
      currency: "USD",
      total_requests: 0,
      completed_requests: 0,
      failed_requests: 0,
      success_rate: 0.0,
      fallback_count: 0,
      fallback_rate: 0.0,
      total_prompt_tokens: 0,
      total_completion_tokens: 0,
      total_tokens: 0,
      estimated_cost: 0.0,
      avg_latency_ms: null,
    };
    const emptyBreakdown = {
      window: "30d",
      created_from: now,
      created_to: now,
      currency: "USD",
      items: [],
    };
    const emptyTimeseries = {
      window: "30d",
      created_from: now,
      created_to: now,
      currency: "USD",
      interval: "day",
      items: [],
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/usage/summary")) return jsonResponse(summary);
        if (u.includes("/admin/usage/by-project")) return jsonResponse(emptyBreakdown);
        if (u.includes("/admin/usage/by-provider")) return jsonResponse(emptyBreakdown);
        if (u.includes("/admin/usage/timeseries")) return jsonResponse(emptyTimeseries);
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<UsagePage />);

    expect(await screen.findByText("Usage")).toBeInTheDocument();
    expect(await screen.findByText("No project usage")).toBeInTheDocument();
    expect(await screen.findByText("No provider usage")).toBeInTheDocument();
    expect(await screen.findByText("No usage buckets")).toBeInTheDocument();
    expect(await screen.findByText("Average latency")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("window selector triggers reload", async () => {
    const now = new Date().toISOString();
    const makeSummary = (window: string) => ({
      window,
      created_from: now,
      created_to: now,
      currency: "USD",
      total_requests: 1,
      completed_requests: 1,
      failed_requests: 0,
      success_rate: 1.0,
      fallback_count: 0,
      fallback_rate: 0.0,
      total_prompt_tokens: 1,
      total_completion_tokens: 1,
      total_tokens: 2,
      estimated_cost: 0.0,
      avg_latency_ms: 1,
    });

    const fetchSpy = vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url);
      if (u.includes("/admin/usage/summary") && u.includes("window=30d")) {
        return jsonResponse(makeSummary("30d"));
      }
      if (u.includes("/admin/usage/summary") && u.includes("window=24h")) {
        return jsonResponse(makeSummary("24h"));
      }
      if (u.includes("/admin/usage/by-project")) {
        return jsonResponse({ window: "30d", created_from: now, created_to: now, currency: "USD", items: [] });
      }
      if (u.includes("/admin/usage/by-provider")) {
        return jsonResponse({ window: "30d", created_from: now, created_to: now, currency: "USD", items: [] });
      }
      if (u.includes("/admin/usage/timeseries")) {
        return jsonResponse({ window: "30d", created_from: now, created_to: now, currency: "USD", interval: "day", items: [] });
      }
      return jsonResponse({}, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(<UsagePage />);
    await screen.findByText("Usage");

    fireEvent.change(screen.getByLabelText("Time window"), { target: { value: "24h" } });

    await waitFor(() => {
      const calls = fetchSpy.mock.calls.map((c) => String(c[0]));
      expect(calls.some((u) => u.includes("/admin/usage/summary") && u.includes("window=24h"))).toBe(true);
    });
  });
});

