"use client";

import { useCallback } from "react";

export type UrlFilterKey<T extends Record<string, string>> = keyof T & string;

/** Parse/build/apply URL query params for filter state (no Next router dependency). */
export function useUrlFilters<T extends Record<string, string>>(opts: {
  pathname: string;
  defaults: T;
  keys: readonly UrlFilterKey<T>[];
}) {
  const parseFromSearch = useCallback(
    (search: string): T => {
      const raw = search.startsWith("?") ? search.slice(1) : search;
      const params = new URLSearchParams(raw);
      const next = { ...opts.defaults };
      for (const k of opts.keys) {
        const v = params.get(k);
        if (v !== null) (next as Record<string, string>)[k] = v;
      }
      return next;
    },
    [opts.defaults, opts.keys],
  );

  const toQuery = useCallback(
    (filters: T) => {
      const params = new URLSearchParams();
      for (const k of opts.keys) {
        const value = String(filters[k] ?? "").trim();
        if (value) params.set(k, value);
      }
      return params.toString();
    },
    [opts.keys],
  );

  const replaceUrl = useCallback(
    (filters: T) => {
      const q = toQuery(filters);
      const href = q ? `${opts.pathname}?${q}` : opts.pathname;
      if (typeof window !== "undefined") {
        window.history.replaceState(null, "", href);
      }
    },
    [toQuery, opts.pathname],
  );

  return { parseFromSearch, toQuery, replaceUrl };
}
