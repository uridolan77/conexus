import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { adminSessionFetch } from "@/lib/api";

describe("adminSessionFetch", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("redirects to /login on 401 when window is available", async () => {
    const loc = { href: "http://localhost:3000/dashboard" };
    Object.defineProperty(window, "location", {
      configurable: true,
      value: loc,
    });
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "nope" }), { status: 401 }),
    );

    await adminSessionFetch("http://localhost:8000/admin/projects");

    expect(loc.href).toBe("/login");
  });

  it("does not redirect on non-401", async () => {
    const loc = { href: "http://localhost:3000/dashboard" };
    Object.defineProperty(window, "location", {
      configurable: true,
      value: loc,
    });
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "bad" }), { status: 403 }),
    );

    const res = await adminSessionFetch("http://localhost:8000/admin/projects");

    expect(res.status).toBe(403);
    expect(loc.href).toBe("http://localhost:3000/dashboard");
  });

  it("defaults credentials to include", async () => {
    await adminSessionFetch("http://localhost:8000/admin/x");

    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/admin/x", {
      credentials: "include",
    });
  });
});
