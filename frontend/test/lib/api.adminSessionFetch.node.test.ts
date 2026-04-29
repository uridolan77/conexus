/** @vitest-environment node */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { adminSessionFetch } from "@/lib/api";

describe("adminSessionFetch (no browser)", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 401 })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("401 returns response without throwing when window is undefined", async () => {
    const res = await adminSessionFetch("http://localhost:8000/admin/projects");
    expect(res.status).toBe(401);
  });
});
