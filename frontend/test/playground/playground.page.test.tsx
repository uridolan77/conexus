import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import PlaygroundPage from "@/app/playground/page";

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
    const keyInput = screen.getByPlaceholderText("cnx_...") as HTMLInputElement;
    fireEvent.change(keyInput, { target: { value: "cnx_secret_key" } });

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
        { detail: "Invalid API key: cnx_secret_key" },
        401,
        { "X-Conexus-Request-Id": "req_bad" },
      ),
    );

    render(<PlaygroundPage />);

    const keyInput = screen.getByPlaceholderText("cnx_...") as HTMLInputElement;
    fireEvent.change(keyInput, { target: { value: "cnx_secret_key" } });

    const sendButton = screen.getByRole("button", { name: "Send request" });
    fireEvent.click(sendButton);

    await waitFor(() => expect(screen.getByText("Troubleshooting")).toBeInTheDocument());

    // Request id shows, but key is redacted from error output
    expect(screen.getByText("req_bad")).toBeInTheDocument();
    expect(screen.queryByText("cnx_secret_key")).not.toBeInTheDocument();
  });
});

