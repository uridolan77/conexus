import { describe, expect, it } from "vitest";
import { buildChatCompletionPayload } from "@/lib/admin/playground";

describe("buildChatCompletionPayload", () => {
  it("omits empty system message", () => {
    const payload = buildChatCompletionPayload({
      model: "conexus-fast",
      systemMessage: "   ",
      userMessage: "Hello",
    });
    expect(payload.messages).toHaveLength(1);
    expect(payload.messages[0]).toEqual({ role: "user", content: "Hello" });
  });

  it("includes non-empty system message", () => {
    const payload = buildChatCompletionPayload({
      model: "conexus-fast",
      systemMessage: "You are helpful.",
      userMessage: "Hello",
    });
    expect(payload.messages).toHaveLength(2);
    expect(payload.messages[0]).toEqual({ role: "system", content: "You are helpful." });
    expect(payload.messages[1]).toEqual({ role: "user", content: "Hello" });
  });

  it("validates max tokens (only positive integer)", () => {
    expect(
      buildChatCompletionPayload({
        model: "conexus-fast",
        userMessage: "Hello",
        maxTokens: "0",
      }).max_tokens,
    ).toBeUndefined();

    expect(
      buildChatCompletionPayload({
        model: "conexus-fast",
        userMessage: "Hello",
        maxTokens: "-1",
      }).max_tokens,
    ).toBeUndefined();

    expect(
      buildChatCompletionPayload({
        model: "conexus-fast",
        userMessage: "Hello",
        maxTokens: "12.5",
      }).max_tokens,
    ).toBeUndefined();

    expect(
      buildChatCompletionPayload({
        model: "conexus-fast",
        userMessage: "Hello",
        maxTokens: "256",
      }).max_tokens,
    ).toBe(256);
  });

  it("validates temperature (only valid number)", () => {
    expect(
      buildChatCompletionPayload({
        model: "conexus-fast",
        userMessage: "Hello",
        temperature: "nope",
      }).temperature,
    ).toBeUndefined();

    expect(
      buildChatCompletionPayload({
        model: "conexus-fast",
        userMessage: "Hello",
        temperature: "0.2",
      }).temperature,
    ).toBeCloseTo(0.2);
  });
});

