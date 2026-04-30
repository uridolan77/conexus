import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AdapterProfilesPage from "@/app/adapter-profiles/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

const WARNING =
  "Adapter profile registration is supported. Canary, promote, rollback, and traffic splitting may still be staged depending on backend configuration. This page shows gateway registry state, not guaranteed live traffic behavior.";

describe("AdapterProfilesPage", () => {
  it("renders required warning banner", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/adapter-profiles?")) {
          return jsonResponse({ items: [], limit: 50, offset: 0, total: 0 });
        }
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<AdapterProfilesPage />);
    expect(await screen.findByText(WARNING)).toBeInTheDocument();
  });

  it("renders a registered row and shows drawer metadata + activations", async () => {
    const row = {
      gateway_profile_id: "gw_1",
      adapter_profile_id: "ap_1",
      domain_key: "example.com",
      status: "Registered",
      composite_score: 0.9,
      profile_version: "v1",
      evidence_hash: "e1",
      semantic_context_hash: "s1",
      slod_model_version: "m1",
      created_at: new Date().toISOString(),
    };
    const detail = {
      ...row,
      source_run_id: "run_1",
      source_plan_id: "plan_1",
      metadata: { hello: "world" },
      updated_at: new Date().toISOString(),
      published_at: null,
    };
    const activations = [
      {
        id: "act_1",
        domain_key: "example.com",
        gateway_profile_id: "gw_1",
        status: "Active",
        canary_percent: null,
        previous_gateway_profile_id: null,
        created_at: new Date().toISOString(),
        activated_at: null,
        promoted_at: null,
        rolled_back_at: null,
        metadata: { note: "ok" },
      },
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/adapter-profiles?")) {
          return jsonResponse({ items: [row], limit: 50, offset: 0, total: 1 });
        }
        if (u.includes("/admin/adapter-profiles/gw_1/activations")) {
          return jsonResponse(activations);
        }
        if (u.includes("/admin/adapter-profiles/gw_1")) {
          return jsonResponse(detail);
        }
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<AdapterProfilesPage />);
    expect(await screen.findByText("gw_1")).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "View" }));

    await waitFor(() => expect(screen.getByText("Adapter profile detail")).toBeInTheDocument());
    expect(screen.getByText("Metadata JSON")).toBeInTheDocument();
    expect(screen.getByText("Activation history")).toBeInTheDocument();
    expect(await screen.findByText("Active")).toBeInTheDocument();
  });
});

