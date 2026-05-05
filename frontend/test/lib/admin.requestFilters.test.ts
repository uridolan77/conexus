import { describe, expect, it } from "vitest";

import {
  activeRequestFiltersSummary,
  asRequestSortBy,
  asRequestSortDir,
  defaultRequestFilters,
  requestFiltersFromSearch,
  requestFiltersToQuery,
} from "@/lib/admin/requestFilters";

describe("request filter helpers", () => {
  it("round-trips filter query params used by the requests page", () => {
    const filters = requestFiltersFromSearch(
      "?limit=25&request_id=req_1&status=failed&fallback_used=true&sort_by=latency_ms&sort_dir=asc",
    );

    expect(filters.limit).toBe("25");
    expect(filters.request_id).toBe("req_1");
    expect(filters.status).toBe("failed");
    expect(filters.fallback_used).toBe("true");
    expect(asRequestSortBy(filters.sort_by)).toBe("latency_ms");
    expect(asRequestSortDir(filters.sort_dir)).toBe("asc");

    const query = requestFiltersToQuery(filters, 50);
    expect(query.get("limit")).toBe("25");
    expect(query.get("offset")).toBe("50");
    expect(query.get("request_id")).toBe("req_1");
  });

  it("keeps summary compact and ASCII-only", () => {
    const summary = activeRequestFiltersSummary({
      ...defaultRequestFilters,
      provider: "openai",
      min_latency_ms: "10",
      max_latency_ms: "100",
    });

    expect(summary).toContain("prov=openai");
    expect(summary).toContain("lat=10-100ms");
    expect(summary).not.toContain("—");
    expect(summary).not.toContain("–");
  });
});
