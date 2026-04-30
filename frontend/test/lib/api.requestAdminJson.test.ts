import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { deleteAdminJson, getAdminJson, postAdminJson } from "@/lib/api";

// Minimal mock: adminSessionFetch is just fetch under the hood
const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  // suppress 401 redirect — no window.location in node
  vi.stubGlobal("window", {
    location: { href: "" },
    setTimeout: globalThis.setTimeout,
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function emptyResponse(status = 204) {
  return Promise.resolve(new Response("", { status }));
}

describe("getAdminJson — path safety", () => {
  it("rejects absolute http:// paths without fetching", async () => {
    const result = await getAdminJson("http://evil.com/steal");
    expect(result.ok).toBe(false);
    expect(!result.ok && result.error.message).toMatch(/absolute URLs/i);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("rejects absolute https:// paths without fetching", async () => {
    const result = await getAdminJson("https://evil.com/steal");
    expect(result.ok).toBe(false);
    expect(!result.ok && result.error.status).toBe(0);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("rejects non-leading-slash relative paths without fetching", async () => {
    const result = await getAdminJson("admin/projects");
    expect(result.ok).toBe(false);
    expect(!result.ok && result.error.message).toMatch(/must start with.*\//i);
    expect(!result.ok && result.error.message).not.toMatch(/admin\/projects/i);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("accepts relative paths", async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ items: [] }));
    const result = await getAdminJson("/admin/projects");
    expect(result.ok).toBe(true);
  });
});

describe("getAdminJson — empty/void response", () => {
  it("returns ok:true with null data on 200 with empty body", async () => {
    // 204 is a null-body status and rejected by the jsdom Response constructor;
    // test empty-string 200 which covers the same readJsonSafe null-guard path.
    mockFetch.mockReturnValueOnce(
      Promise.resolve(new Response("", { status: 200 })),
    );
    const result = await getAdminJson("/admin/something");
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.data).toBeNull();
  });
});

describe("postAdminJson — signal passthrough", () => {
  it("passes AbortSignal to fetch", async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ id: "1" }));
    const controller = new AbortController();
    await postAdminJson("/admin/projects", { name: "test" }, { signal: controller.signal });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.signal).toBe(controller.signal);
  });
});

describe("deleteAdminJson — network error", () => {
  it("returns ok:false on network failure", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network failure"));
    const result = await deleteAdminJson("/admin/providers/1/revoke");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.message).toBe("Network failure");
  });
});
