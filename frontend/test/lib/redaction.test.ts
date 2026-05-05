import { describe, expect, it } from "vitest";
import { redactSensitiveObject, redactSensitiveString } from "@/lib/redaction";

describe("redactSensitiveObject", () => {
  it("returns null as-is", () => {
    expect(redactSensitiveObject(null)).toBeNull();
  });

  it("returns primitives unchanged", () => {
    expect(redactSensitiveObject("hello")).toBe("hello");
    expect(redactSensitiveObject(42)).toBe(42);
    expect(redactSensitiveObject(true)).toBe(true);
  });

  it("redacts api_key", () => {
    const result = redactSensitiveObject({ api_key: "sk-abc123" }) as Record<string, unknown>;
    expect(result.api_key).toBe("[REDACTED]");
  });

  it("redacts apikey (no underscore)", () => {
    const result = redactSensitiveObject({ apikey: "sk-abc" }) as Record<string, unknown>;
    expect(result.apikey).toBe("[REDACTED]");
  });

  it("redacts token", () => {
    const result = redactSensitiveObject({ token: "tok_xyz" }) as Record<string, unknown>;
    expect(result.token).toBe("[REDACTED]");
  });

  it("redacts secret", () => {
    const result = redactSensitiveObject({ secret: "mysecret" }) as Record<string, unknown>;
    expect(result.secret).toBe("[REDACTED]");
  });

  it("redacts password", () => {
    const result = redactSensitiveObject({ password: "hunter2" }) as Record<string, unknown>;
    expect(result.password).toBe("[REDACTED]");
  });

  it("redacts authorization", () => {
    const result = redactSensitiveObject({ authorization: "Bearer tok" }) as Record<string, unknown>;
    expect(result.authorization).toBe("[REDACTED]");
  });

  it("redacts bearer", () => {
    const result = redactSensitiveObject({ bearer: "tok" }) as Record<string, unknown>;
    expect(result.bearer).toBe("[REDACTED]");
  });

  it("redacts key (standalone)", () => {
    const result = redactSensitiveObject({ key: "mykey" }) as Record<string, unknown>;
    expect(result.key).toBe("[REDACTED]");
  });

  it("preserves non-sensitive keys", () => {
    const result = redactSensitiveObject({ name: "prod", score: 0.9 }) as Record<string, unknown>;
    expect(result.name).toBe("prod");
    expect(result.score).toBe(0.9);
  });

  it("recurses into nested objects", () => {
    const input = { outer: { api_key: "secret", label: "ok" } };
    const result = redactSensitiveObject(input) as { outer: Record<string, unknown> };
    expect(result.outer.api_key).toBe("[REDACTED]");
    expect(result.outer.label).toBe("ok");
  });

  it("recurses into arrays", () => {
    const input = [{ token: "t1" }, { name: "safe" }];
    const result = redactSensitiveObject(input) as Array<Record<string, unknown>>;
    expect(result[0].token).toBe("[REDACTED]");
    expect(result[1].name).toBe("safe");
  });

  it("does not mutate the original object", () => {
    const input = { api_key: "original" };
    redactSensitiveObject(input);
    expect(input.api_key).toBe("original");
  });

  it("handles cycles without throwing", () => {
    const a: Record<string, unknown> = { safe: "value" };
    a.self = a;
    expect(() => redactSensitiveObject(a)).not.toThrow();
  });
});

describe("redactSensitiveString", () => {
  it("redacts Bearer tokens", () => {
    const result = redactSensitiveString("Authorization: Bearer sk-abc123def456");
    expect(result).toContain("[REDACTED]");
    expect(result).not.toContain("sk-abc123def456");
  });

  it("redacts sk- prefixed keys", () => {
    const result = redactSensitiveString("key is sk-verylongapikey1234");
    expect(result).toContain("[REDACTED]");
    expect(result).not.toContain("sk-verylongapikey1234");
  });

  it("redacts cnx_ prefixed keys", () => {
    const result = redactSensitiveString("cnx_live_supersecretkey123");
    expect(result).toContain("[REDACTED]");
    expect(result).not.toContain("cnx_live_supersecretkey123");
  });

  it("redacts sk-ant-api keys", () => {
    const raw = "key=sk-ant-api03-abcdefghijklmnop1234567890AB";
    const result = redactSensitiveString(raw);
    expect(result).toContain("[REDACTED]");
    expect(result).not.toContain("sk-ant-api03");
  });

  it("redacts JWT-like three-part tokens", () => {
    const jwt =
      "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3j_VNHQgqUkeBPuuvhdsWBDHLBKkvp8";
    const result = redactSensitiveString(`Authorization ${jwt}`);
    expect(result).toContain("[REDACTED]");
    expect(result).not.toContain("eyJhbGciOiJIUzI1NiJ9");
  });

  it("leaves safe strings unchanged", () => {
    const safe = "model=gpt-4o-mini provider=openai";
    expect(redactSensitiveString(safe)).toBe(safe);
  });
});
