import { describe, expect, it } from "vitest";
import { formatDate } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

describe("formatDate", () => {
  it("delegates to formatDateTime for valid values", () => {
    const iso = "2024-06-15T10:30:00Z";
    expect(formatDate(iso)).toBe(formatDateTime(iso));
  });

  it("uses em-dash fallback for null/undefined", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
  });

  it("returns original value for invalid date strings", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });
});
