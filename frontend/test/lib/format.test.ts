import { describe, expect, it } from "vitest";
import {
  computePercent,
  formatCost,
  formatDateTime,
  formatDurationSeconds,
  formatLatency,
  formatNullable,
  formatPercent,
  formatPercentRatio,
  formatPercentValue,
  formatTokens,
} from "@/lib/format";

describe("formatDateTime", () => {
  it("returns em-dash for null", () => {
    expect(formatDateTime(null)).toBe("—");
  });
  it("returns em-dash for undefined", () => {
    expect(formatDateTime(undefined)).toBe("—");
  });
  it("returns em-dash for empty string", () => {
    expect(formatDateTime("")).toBe("—");
  });
  it("formats a valid ISO string", () => {
    const result = formatDateTime("2024-06-15T10:30:00Z");
    expect(result).not.toBe("—");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
  it("returns the raw string for invalid dates", () => {
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });
});

describe("formatCost", () => {
  it("returns em-dash for null", () => {
    expect(formatCost(null)).toBe("—");
  });
  it("returns em-dash for undefined", () => {
    expect(formatCost(undefined)).toBe("—");
  });
  it("formats zero", () => {
    expect(formatCost(0)).toMatch(/\$0/);
  });
  it("formats a positive value as USD", () => {
    const result = formatCost(1.5);
    expect(result).toContain("1.5");
    expect(result).toContain("$");
  });
});

describe("formatPercent", () => {
  it("returns em-dash for null", () => {
    expect(formatPercent(null)).toBe("—");
  });
  it("formats ratio 0.73 as '73.0%'", () => {
    expect(formatPercent(0.73)).toBe("73.0%");
  });
  it("formats ratio 1 as '100.0%'", () => {
    expect(formatPercent(1)).toBe("100.0%");
  });
  it("formats ratio 0 as '0.0%'", () => {
    expect(formatPercent(0)).toBe("0.0%");
  });
});

describe("formatPercentRatio", () => {
  it("returns em-dash for null", () => {
    expect(formatPercentRatio(null)).toBe("—");
  });
  it("returns em-dash for undefined", () => {
    expect(formatPercentRatio(undefined)).toBe("—");
  });
  it("formats ratio 0.73 as '73.0%'", () => {
    expect(formatPercentRatio(0.73)).toBe("73.0%");
  });
  it("formats ratio values above 1", () => {
    expect(formatPercentRatio(1.25)).toBe("125.0%");
  });
});

describe("formatPercentValue", () => {
  it("formats percent-point values", () => {
    expect(formatPercentValue(73.2)).toBe("73%");
  });
});

describe("formatTokens", () => {
  it("returns em-dash for null", () => {
    expect(formatTokens(null)).toBe("—");
  });
  it("formats 0", () => {
    expect(formatTokens(0)).toBe("0");
  });
  it("formats large numbers with separators", () => {
    const result = formatTokens(1234567);
    expect(result).toMatch(/1[,.]234/);
  });
});

describe("formatLatency", () => {
  it("returns em-dash for null", () => {
    expect(formatLatency(null)).toBe("—");
  });
  it("returns <1ms for sub-millisecond values", () => {
    expect(formatLatency(0.5)).toBe("<1ms");
  });
  it("returns ms for values under 1000", () => {
    expect(formatLatency(250)).toBe("250ms");
  });
  it("returns seconds for values >= 1000", () => {
    expect(formatLatency(1500)).toBe("1.5s");
  });
});

describe("formatNullable", () => {
  it("returns em-dash for null", () => {
    expect(formatNullable(null)).toBe("—");
  });
  it("returns em-dash for undefined", () => {
    expect(formatNullable(undefined)).toBe("—");
  });
  it("returns em-dash for empty string", () => {
    expect(formatNullable("")).toBe("—");
  });
  it("returns the value as string", () => {
    expect(formatNullable("hello")).toBe("hello");
    expect(formatNullable(42)).toBe("42");
  });
  it("uses a custom fallback", () => {
    expect(formatNullable(null, "n/a")).toBe("n/a");
  });
});

describe("formatDurationSeconds", () => {
  it("formats seconds under 60", () => {
    expect(formatDurationSeconds(45)).toBe("45s");
  });
  it("formats minutes", () => {
    expect(formatDurationSeconds(125)).toBe("2m 5s");
  });
  it("formats hours and minutes", () => {
    expect(formatDurationSeconds(3661)).toBe("1h 1m 1s");
  });
  it("formats exact hour", () => {
    expect(formatDurationSeconds(3600)).toBe("1h 0m");
  });
});

describe("computePercent", () => {
  it("returns null for null limit", () => {
    expect(computePercent(50, null)).toBeNull();
  });
  it("returns null for zero limit", () => {
    expect(computePercent(50, 0)).toBeNull();
  });
  it("computes percentage correctly", () => {
    expect(computePercent(50, 100)).toBe(50);
  });
  it("caps at 999", () => {
    expect(computePercent(10000, 1)).toBe(999);
  });
});
