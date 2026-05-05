import { describe, expect, it, vi, afterEach } from "vitest";
import { adminSessionFetch } from "@/lib/api";

describe("adminSessionFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("uses credentials include by default", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 200 }),
    );
    await adminSessionFetch("http://localhost/api/x");
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost/api/x",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("respects explicit credentials on init", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 200 }),
    );
    await adminSessionFetch("http://localhost/api/x", { credentials: "omit" });
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost/api/x",
      expect.objectContaining({ credentials: "omit" }),
    );
  });

  it("redirects to login on 401 in the browser", async () => {
    vi.stubGlobal("window", { location: { href: "" } });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 401 }));
    const res = await adminSessionFetch("http://localhost/api/x");
    expect(res.status).toBe(401);
    expect(window.location.href).toBe("/login");
  });

  it("does not redirect on 401 outside the browser", async () => {
    vi.stubGlobal("window", undefined);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 401 }));
    const res = await adminSessionFetch("http://localhost/api/x");
    expect(res.status).toBe(401);
  });
});
