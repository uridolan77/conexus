import { describe, expect, it, vi } from "vitest";
import { listAuditLogs } from "@/lib/admin/audit";

describe("listAuditLogs query construction", () => {
  it("uses buildQuery for supported filters", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], limit: 50, offset: 0, total: 0 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", mockFetch);
    vi.stubGlobal("window", {
      location: { href: "" },
      setTimeout: globalThis.setTimeout,
    });

    await listAuditLogs({
      limit: 50,
      offset: 0,
      actor_username: "admin",
      action: "project.create",
      resource_type: "project",
      resource_id: "p1",
    });

    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/admin/audit?");
    expect(url).toContain("limit=50");
    expect(url).toContain("offset=0");
    expect(url).toContain("actor_username=admin");
    expect(url).toContain("action=project.create");
    expect(url).toContain("resource_type=project");
    expect(url).toContain("resource_id=p1");
  });
});

