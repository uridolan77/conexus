import { describe, expect, it } from "vitest";
import {
  buildChatCompletionPayload,
  parseMaxTokens,
  parseTemperature,
} from "@/lib/admin/playground";

describe("parseTemperature", () => {
  it("accepts empty string (optional)", () => {
    expect(parseTemperature("").ok).toBe(true);
    expect(parseTemperature("  ").ok).toBe(true);
  });

  it("accepts a valid finite number", () => {
    const r = parseTemperature("0.7");
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBe(0.7);
  });

  it("accepts zero", () => {
    const r = parseTemperature("0");
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBe(0);
  });

  it("rejects NaN strings", () => {
    expect(parseTemperature("abc").ok).toBe(false);
    expect(parseTemperature("1.0.0").ok).toBe(false);
  });

  it("rejects Infinity", () => {
    expect(parseTemperature("Infinity").ok).toBe(false);
  });
});

describe("parseMaxTokens", () => {
  it("accepts empty string (optional)", () => {
    expect(parseMaxTokens("").ok).toBe(true);
    expect(parseMaxTokens("  ").ok).toBe(true);
  });

  it("accepts valid positive integer", () => {
    const r = parseMaxTokens("256");
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBe(256);
  });

  it("rejects zero", () => {
    expect(parseMaxTokens("0").ok).toBe(false);
  });

  it("rejects negative integers", () => {
    expect(parseMaxTokens("-1").ok).toBe(false);
  });

  it("rejects floats", () => {
    expect(parseMaxTokens("1.5").ok).toBe(false);
  });

  it("rejects non-numeric strings", () => {
    expect(parseMaxTokens("abc").ok).toBe(false);
  });
});

describe("buildChatCompletionPayload", () => {
  it("builds a minimal payload with user message only", () => {
    const p = buildChatCompletionPayload({ model: "gpt-4o", userMessage: "hello" });
    expect(p.model).toBe("gpt-4o");
    expect(p.messages).toHaveLength(1);
    expect(p.messages[0]).toEqual({ role: "user", content: "hello" });
    expect(p.temperature).toBeUndefined();
    expect(p.max_tokens).toBeUndefined();
  });

  it("includes system message when non-empty", () => {
    const p = buildChatCompletionPayload({
      model: "m",
      userMessage: "hi",
      systemMessage: "You are helpful.",
    });
    expect(p.messages[0]).toEqual({ role: "system", content: "You are helpful." });
    expect(p.messages[1]).toEqual({ role: "user", content: "hi" });
  });

  it("omits system message when empty", () => {
    const p = buildChatCompletionPayload({ model: "m", userMessage: "hi", systemMessage: "" });
    expect(p.messages).toHaveLength(1);
  });

  it("includes temperature when valid", () => {
    const p = buildChatCompletionPayload({ model: "m", userMessage: "hi", temperature: "0.5" });
    expect(p.temperature).toBe(0.5);
  });

  it("omits temperature when empty", () => {
    const p = buildChatCompletionPayload({ model: "m", userMessage: "hi", temperature: "" });
    expect(p.temperature).toBeUndefined();
  });

  it("omits temperature when invalid (the page prevents send, payload reflects raw input)", () => {
    // buildChatCompletionPayload silently omits invalid values — canSend prevents this path in the UI
    const p = buildChatCompletionPayload({ model: "m", userMessage: "hi", temperature: "abc" });
    expect(p.temperature).toBeUndefined();
  });

  it("includes max_tokens when valid", () => {
    const p = buildChatCompletionPayload({ model: "m", userMessage: "hi", maxTokens: "512" });
    expect(p.max_tokens).toBe(512);
  });

  it("omits max_tokens when empty", () => {
    const p = buildChatCompletionPayload({ model: "m", userMessage: "hi", maxTokens: "" });
    expect(p.max_tokens).toBeUndefined();
  });

  it("trims model and messages", () => {
    const p = buildChatCompletionPayload({ model: "  gpt-4o  ", userMessage: "  hello  " });
    expect(p.model).toBe("gpt-4o");
    expect(p.messages[0].content).toBe("hello");
  });
});
