import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RoutingPage from "@/app/routing/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("RoutingPage", () => {
  it("renders policy table", async () => {
    const policy = {
      id: "pol_1",
      name: "default",
      mode: "static",
      default_alias: "conexus-default",
      aliases: [
        {
          alias: "conexus-default",
          primary_provider: "openai",
          primary_model: "gpt-4o-mini",
          fallback_provider: "anthropic",
          fallback_model: "claude-3-5-sonnet",
        },
      ],
      direct_routes: [
        { provider: "openai", model_prefixes: ["gpt-"], fallback_enabled: false },
      ],
    };
    const candidates = [
      {
        provider: "openai",
        source: "bo_config",
        config_id: "p1",
        label: "main",
        key_mask: "sk-…abcd",
        is_active: true,
        last_test_status: "passed",
        last_tested_at: "2026-01-01T00:00:00Z",
      },
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/routing/policy")) return jsonResponse(policy);
        if (u.includes("/admin/routing/provider-candidates")) return jsonResponse(candidates);
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<RoutingPage />);
    expect(await screen.findByText("Routing")).toBeInTheDocument();
    expect(await screen.findByText("Alias Routes")).toBeInTheDocument();
    expect((await screen.findAllByText("conexus-default")).length).toBeGreaterThan(0);
  });

  it("renders provider candidates", async () => {
    const policy = {
      id: "pol_1",
      name: "default",
      mode: "static",
      default_alias: "conexus-default",
      aliases: [],
      direct_routes: [],
    };
    const candidates = [
      {
        provider: "openai",
        source: "bo_config",
        config_id: "p1",
        label: "main",
        key_mask: "sk-…abcd",
        is_active: true,
        last_test_status: "passed",
        last_tested_at: "2026-01-01T00:00:00Z",
      },
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/routing/policy")) return jsonResponse(policy);
        if (u.includes("/admin/routing/provider-candidates")) return jsonResponse(candidates);
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<RoutingPage />);
    expect(await screen.findByText("Provider Candidates")).toBeInTheDocument();
    expect(await screen.findByText("openai")).toBeInTheDocument();
  });

  it("renders warning when provider candidates are missing", async () => {
    const policy = {
      id: "pol_1",
      name: "default",
      mode: "static",
      default_alias: "conexus-default",
      aliases: [],
      direct_routes: [],
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/routing/policy")) return jsonResponse(policy);
        if (u.includes("/admin/routing/provider-candidates")) return jsonResponse({ detail: "nope" }, { status: 500 });
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<RoutingPage />);
    expect(await screen.findByText(/Verify backend wiring before production/i)).toBeInTheDocument();
  });
});

