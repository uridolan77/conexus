import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import PlaygroundPage from "@/app/playground/page";

vi.mock("@/lib/playgroundKeyHandoff", () => ({
  takePlaygroundApiKeyOnce: vi.fn().mockReturnValue(null),
}));

function jsonResponse(body: unknown, status = 200, headers?: Record<string, string>) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json", ...(headers ?? {}) },
    }),
  );
}

describe("Playground page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not use localStorage/sessionStorage", () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    render(<PlaygroundPage />);
    expect(setItem).not.toHaveBeenCalled();
  });

  it("uses cx_live key placeholder", () => {
    render(<PlaygroundPage />);
    expect(screen.getByPlaceholderText("cx_live_...")).toBeInTheDocument();
  });

  it("shows invalid temperature error and disables Send", () => {
    render(<PlaygroundPage />);

    fireEvent.change(screen.getByPlaceholderText("cx_live_..."), {
      target: { value: "cx_live_deadbeef_00000000000000000000000000000000" },
    });

    const temp = screen.getByPlaceholderText("0.2");
    fireEvent.change(temp, { target: { value: "nope" } });

    expect(screen.getByText("Temperature must be a finite number.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send request" })).toBeDisabled();
  });

  it("shows invalid max tokens error and disables Send", () => {
    render(<PlaygroundPage />);

    fireEvent.change(screen.getByPlaceholderText("cx_live_..."), {
      target: { value: "cx_live_deadbeef_00000000000000000000000000000000" },
    });

    const maxTokens = screen.getByPlaceholderText("256");
    fireEvent.change(maxTokens, { target: { value: "0" } });

    expect(screen.getByText("Max tokens must be a positive integer.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send request" })).toBeDisabled();
  });

  it("renders request id and assistant content on success", async () => {
    const mockFetch = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        {
          id: "resp_1",
          model: "gpt-x",
          provider: "openai",
          fallback_used: false,
          choices: [{ index: 0, message: { role: "assistant", content: "Hello!" }, finish_reason: "stop" }],
          usage: { prompt_tokens: 1, completion_tokens: 2, total_tokens: 3 },
        },
        200,
        { "X-Conexus-Request-Id": "req_123" },
      ),
    );

    render(<PlaygroundPage />);

    // Fill required fields
    const keyInput = screen.getByPlaceholderText("cx_live_...") as HTMLInputElement;
    fireEvent.change(keyInput, {
      target: { value: "cx_live_deadbeef_00000000000000000000000000000000" },
    });

    const sendButton = screen.getByRole("button", { name: "Send request" });
    fireEvent.click(sendButton);

    await waitFor(() => expect(screen.getByText("Result")).toBeInTheDocument());
    expect(screen.getByText("req_123")).toBeInTheDocument();
    expect(screen.getByText("Hello!")).toBeInTheDocument();
  });

  it("renders safe error and does not echo api key", async () => {
    const mockFetch = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        { detail: "Invalid API key: cx_live_deadbeef_00000000000000000000000000000000" },
        401,
        { "X-Conexus-Request-Id": "req_bad" },
      ),
    );

    render(<PlaygroundPage />);

    const keyInput = screen.getByPlaceholderText("cx_live_...") as HTMLInputElement;
    const apiKey = "cx_live_deadbeef_00000000000000000000000000000000";
    fireEvent.change(keyInput, { target: { value: apiKey } });

    const sendButton = screen.getByRole("button", { name: "Send request" });
    fireEvent.click(sendButton);

    await waitFor(() => expect(screen.getByText("Troubleshooting")).toBeInTheDocument());

    // Request id shows, but key is redacted from error output
    expect(screen.getByText("req_bad")).toBeInTheDocument();
    expect(screen.queryByText(apiKey)).not.toBeInTheDocument();
  });

  it("redacts API key from nested raw JSON debug output", async () => {
    const mockFetch = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
    const apiKey = "cx_live_deadbeef_00000000000000000000000000000000";
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: {
            message: "Unauthorized",
            nested: {
              note: `token=${apiKey}`,
            },
          },
        },
        401,
        { "X-Conexus-Request-Id": "req_nested" },
      ),
    );

    render(<PlaygroundPage />);
    fireEvent.change(screen.getByPlaceholderText("cx_live_..."), {
      target: { value: apiKey },
    });

    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() => expect(screen.getByText("req_nested")).toBeInTheDocument());

    // The debug JSON should not contain the key, even nested
    expect(screen.queryByText(apiKey)).not.toBeInTheDocument();
  });
});

describe("Playground page — key handoff", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("prefills API key and shows handoff notice when handoff key is present", async () => {
    const handoff = await import("@/lib/playgroundKeyHandoff");
    vi.mocked(handoff.takePlaygroundApiKeyOnce).mockReturnValueOnce("cx_live_handoff_secret");

    render(<PlaygroundPage />);

    const keyInput = await screen.findByPlaceholderText("cx_live_...") as HTMLInputElement;
    await waitFor(() => expect(keyInput.value).toBe("cx_live_handoff_secret"));
    expect(screen.getByText(/loaded from one-time handoff/i)).toBeInTheDocument();
  });

  it("does not prefill or show notice when no handoff key", async () => {
    render(<PlaygroundPage />);

    const keyInput = screen.getByPlaceholderText("cx_live_...") as HTMLInputElement;
    expect(keyInput.value).toBe("");
    expect(screen.queryByText(/loaded from one-time handoff/i)).not.toBeInTheDocument();
  });

  it("does not use localStorage/sessionStorage when handoff key is loaded", async () => {
    const handoff = await import("@/lib/playgroundKeyHandoff");
    vi.mocked(handoff.takePlaygroundApiKeyOnce).mockReturnValueOnce("cx_live_handoff_secret");
    const setItem = vi.spyOn(Storage.prototype, "setItem");

    render(<PlaygroundPage />);
    await waitFor(() => expect((screen.getByPlaceholderText("cx_live_...") as HTMLInputElement).value).toBe("cx_live_handoff_secret"));

    expect(setItem).not.toHaveBeenCalled();
  });
});

