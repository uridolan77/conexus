import { describe, expect, it } from "vitest";
import { buildQuery } from "@/lib/api";

describe("buildQuery", () => {
  it("returns empty string with no params", () => {
    expect(buildQuery({})).toBe("");
  });

  it("returns empty string when all values are null", () => {
    expect(buildQuery({ a: null, b: null })).toBe("");
  });

  it("returns empty string when all values are undefined", () => {
    expect(buildQuery({ a: undefined, b: undefined })).toBe("");
  });

  it("returns empty string when all values are empty string", () => {
    expect(buildQuery({ a: "", b: "" })).toBe("");
  });

  it("builds a single-param query", () => {
    expect(buildQuery({ window: "24h" })).toBe("?window=24h");
  });

  it("builds a multi-param query", () => {
    const result = buildQuery({ limit: 50, offset: 0 });
    expect(result).toBe("?limit=50&offset=0");
  });

  it("skips null/undefined/empty but keeps falsy zero and false", () => {
    const result = buildQuery({ a: 0, b: false, c: null, d: undefined, e: "" });
    expect(result).toBe("?a=0&b=false");
  });

  it("encodes special characters in keys and values", () => {
    const result = buildQuery({ "project id": "foo bar" });
    expect(result).toBe("?project%20id=foo%20bar");
  });

  it("handles boolean values", () => {
    expect(buildQuery({ active: true })).toBe("?active=true");
    expect(buildQuery({ active: false })).toBe("?active=false");
  });
});
