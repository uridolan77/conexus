"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DependencyList, Dispatch, SetStateAction } from "react";
import type { AdminResult } from "@/lib/api";

export type ResourceState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setData: Dispatch<SetStateAction<T | null>>;
};

/**
 * Lightweight data-fetching hook for admin pages.
 *
 * - Prevents state updates after unmount.
 * - Guards against stale responses overwriting newer responses via a generation counter.
 * - Does not cache; does not redirect on 401 (the API layer handles that).
 * - No external dependencies.
 *
 * Usage:
 *   const { data, loading, error, reload } = useAdminResource(
 *     () => listProjects(),
 *     [],
 *   );
 */
export function useAdminResource<T>(
  loader: () => Promise<AdminResult<T>>,
  deps: DependencyList,
  options?: {
    /** Pre-populate data before the first load. */
    initialData?: T | null;
    /** Set to false to skip the automatic load on mount / dep change. Default: true. */
    loadOnMount?: boolean;
  },
): ResourceState<T> {
  const [data, setData] = useState<T | null>(options?.initialData ?? null);
  const [loading, setLoading] = useState(options?.loadOnMount !== false);
  const [error, setError] = useState<string | null>(null);

  // Tracks whether the component is still mounted.
  const mountedRef = useRef(true);
  // Monotonically increasing counter; lets us discard results from stale invocations.
  const generationRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(async () => {
    const gen = ++generationRef.current;
    setLoading(true);
    setError(null);
    try {
      const result = await loader();
      if (!mountedRef.current || gen !== generationRef.current) return;
      if (!result.ok) {
        setError(result.error.message);
      } else {
        setData(result.data);
      }
    } catch (err) {
      if (!mountedRef.current || gen !== generationRef.current) return;
      setError(err instanceof Error ? err.message : "Request failed.");
    } finally {
      if (mountedRef.current && gen === generationRef.current) {
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (options?.loadOnMount === false) {
      setLoading(false);
      return;
    }
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  return { data, loading, error, reload: load, setData };
}
