import { describe, expect, it } from "vitest";
import { parseApiError } from "@/lib/api";

describe("parseApiError", () => {
  it("handles null", () => {
    expect(parseApiError(null).message).toBe("Request failed.");
  });

  it("handles undefined", () => {
    expect(parseApiError(undefined).message).toBe("Request failed.");
  });

  it("handles plain string", () => {
    expect(parseApiError("Something went wrong").message).toBe("Something went wrong");
  });

  it("handles Error instance", () => {
    expect(parseApiError(new Error("network error")).message).toBe("network error");
  });

  it("handles FastAPI string detail", () => {
    const err = { detail: "Not found" };
    const result = parseApiError(err);
    expect(result.message).toBe("Not found");
    expect(result.detail).toBe("Not found");
  });

  it("handles FastAPI validation array detail", () => {
    const err = {
      detail: [
        { msg: "field required", loc: ["body", "name"], type: "missing" },
        { msg: "must be positive", loc: ["body", "count"], type: "value_error" },
      ],
    };
    const result = parseApiError(err, 422);
    expect(result.message).toContain("field required");
    expect(result.message).toContain("must be positive");
    expect(result.status).toBe(422);
  });

  it("handles nested { detail: { code, message } }", () => {
    const err = { detail: { code: "LIMIT_EXCEEDED", message: "Monthly cost limit reached" } };
    const result = parseApiError(err, 429);
    expect(result.message).toBe("Monthly cost limit reached");
    expect(result.status).toBe(429);
  });

  it("handles empty validation array gracefully", () => {
    const err = { detail: [] };
    const result = parseApiError(err);
    expect(result.message).toBe("Validation error.");
  });

  it("carries status code through", () => {
    expect(parseApiError("error", 503).status).toBe(503);
  });

  it("handles unknown object shape without throwing", () => {
    const result = parseApiError({ foo: "bar" });
    expect(typeof result.message).toBe("string");
  });
});
