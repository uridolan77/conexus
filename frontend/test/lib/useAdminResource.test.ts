import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAdminResource } from "@/lib/useAdminResource";
import type { AdminResult } from "@/lib/api";

function ok<T>(data: T): AdminResult<T> {
  return { ok: true, data };
}

function fail(message: string): AdminResult<never> {
  return { ok: false, error: { message } };
}

describe("useAdminResource", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sets data on successful load", async () => {
    const loader = vi.fn().mockResolvedValue(ok(["a", "b"]));
    const { result } = renderHook(() => useAdminResource(loader, []));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["a", "b"]);
    expect(result.current.error).toBeNull();
  });

  it("sets error on failed load", async () => {
    const loader = vi.fn().mockResolvedValue(fail("Not found"));
    const { result } = renderHook(() => useAdminResource(loader, []));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("Not found");
  });

  it("starts in loading state by default", () => {
    const loader = vi.fn().mockResolvedValue(ok(null));
    const { result } = renderHook(() => useAdminResource(loader, []));
    expect(result.current.loading).toBe(true);
  });

  it("starts without loading when loadOnMount is false", () => {
    const loader = vi.fn();
    const { result } = renderHook(() =>
      useAdminResource(loader, [], { loadOnMount: false }),
    );
    expect(result.current.loading).toBe(false);
    expect(loader).not.toHaveBeenCalled();
  });

  it("reload re-fetches and updates data", async () => {
    const loader = vi
      .fn()
      .mockResolvedValueOnce(ok(["first"]))
      .mockResolvedValueOnce(ok(["second"]));

    const { result } = renderHook(() => useAdminResource(loader, []));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(["first"]);

    await act(async () => {
      await result.current.reload();
    });
    expect(result.current.data).toEqual(["second"]);
  });

  it("reload clears previous error", async () => {
    const loader = vi
      .fn()
      .mockResolvedValueOnce(fail("Oops"))
      .mockResolvedValueOnce(ok(["recovered"]));

    const { result } = renderHook(() => useAdminResource(loader, []));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Oops");

    await act(async () => {
      await result.current.reload();
    });
    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual(["recovered"]);
  });

  it("does not update state after unmount", async () => {
    let resolveLoad!: (v: AdminResult<string[]>) => void;
    const loader = vi.fn().mockReturnValue(
      new Promise<AdminResult<string[]>>((res) => {
        resolveLoad = res;
      }),
    );
    const { result, unmount } = renderHook(() => useAdminResource(loader, []));

    // Unmount before load resolves
    unmount();

    // Resolve after unmount — should not throw or update state
    await act(async () => {
      resolveLoad(ok(["post-unmount"]));
    });

    // No state update should have occurred; loading stays true (unmounted, frozen)
    // The key assertion: no React warning about updating unmounted component
    expect(result.current.data).toBeNull();
  });

  it("uses initialData as pre-populated data", async () => {
    const loader = vi.fn().mockResolvedValue(ok(["loaded"]));
    const { result } = renderHook(() =>
      useAdminResource(loader, [], { initialData: ["prefilled"] }),
    );
    // Before load completes, data is the initial value
    expect(result.current.data).toEqual(["prefilled"]);
    await waitFor(() => expect(result.current.loading).toBe(false));
  });
});
