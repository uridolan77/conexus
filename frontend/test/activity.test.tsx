import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import ActivityPage from "@/app/activity/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("ActivityPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("shows empty state when no audit logs", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/audit?")) {
          return jsonResponse({ items: [], limit: 50, offset: 0, total: 0 });
        }
        return jsonResponse({}, { status: 404 });
      }),
    );
    vi.spyOn(window.history, "replaceState");
    window.history.replaceState({}, "", "/activity");

    render(<ActivityPage />);
    expect(await screen.findByText("No audit logs found")).toBeInTheDocument();
  });

  it("renders a row and opens detail drawer", async () => {
    const row = {
      id: "a1",
      actor_admin_user_id: "u1",
      actor_username: "admin",
      action: "project_api_key.issue",
      resource_type: "project_api_key",
      resource_id: "k1",
      metadata: { ok: true },
      created_at: new Date().toISOString(),
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/audit?")) {
          return jsonResponse({ items: [row], limit: 50, offset: 0, total: 1 });
        }
        return jsonResponse({}, { status: 404 });
      }),
    );
    vi.spyOn(window.history, "replaceState");
    window.history.replaceState({}, "", "/activity");

    render(<ActivityPage />);

    expect(await screen.findByText("project_api_key.issue")).toBeInTheDocument();
    const view = await screen.findByRole("button", { name: "View" });
    view.click();

    await waitFor(() => expect(screen.getByText("Audit detail")).toBeInTheDocument());
    expect(screen.getByText("Debug JSON")).toBeInTheDocument();
  });
});

