import { describe, expect, it, vi } from "vitest";
import { listRequests } from "@/lib/admin/requests";

describe("listRequests query construction", () => {
  it("uses buildQuery for filters and includes offset/limit", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], limit: 50, offset: 25, total: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", mockFetch);
    vi.stubGlobal("window", {
      location: { href: "" },
      setTimeout: globalThis.setTimeout,
    });

    await listRequests({
      limit: 50,
      offset: 25,
      project_id: "p1",
      status: "failed",
      request_id: "req_123",
      error_code: "provider_timeout",
    });

    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/admin/requests?");
    expect(url).toContain("limit=50");
    expect(url).toContain("offset=25");
    expect(url).toContain("project_id=p1");
    expect(url).toContain("status=failed");
    expect(url).toContain("request_id=req_123");
    expect(url).toContain("error_code=provider_timeout");
  });
});

