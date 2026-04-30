import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import HealthPage from "@/app/health/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("HealthPage", () => {
  it("renders healthy state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.endsWith("/health")) return jsonResponse({ status: "ok" });
        if (u.endsWith("/readyz")) return jsonResponse({ status: "ready", checks: { db: true } });
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<HealthPage />);

    // Auto-refresh runs on mount.
    expect(await screen.findByRole("heading", { level: 2, name: "Health" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText("ok").length).toBeGreaterThan(0);
    });
  });

  it("renders failed readiness state and shows raw JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.endsWith("/health")) return jsonResponse({ status: "ok" });
        if (u.endsWith("/readyz")) {
          return jsonResponse(
            { status: "not_ready", checks: { db: false } },
            { status: 503 },
          );
        }
        return jsonResponse({}, { status: 404 });
      }),
    );

    render(<HealthPage />);

    expect(await screen.findByRole("heading", { level: 3, name: "Readiness" })).toBeInTheDocument();

    // Expand raw json blocks to ensure they're present in DOM.
    expect(await screen.findByText("Raw /readyz JSON")).toBeInTheDocument();
    expect(await screen.findByText("Raw /health JSON")).toBeInTheDocument();
  });
});

