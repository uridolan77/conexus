import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ProvidersPage from "@/app/providers/page";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

function providerRow(overrides: Record<string, unknown> = {}) {
  return {
    id: "provider-1",
    provider: "openai",
    label: "Primary OpenAI",
    key_mask: "sk-t...cret",
    is_active: true,
    revoked_at: null,
    last_test_status: "failed",
    last_test_error: "bad key [redacted]",
    last_tested_at: "2026-05-04T00:00:00Z",
    created_at: "2026-05-04T00:00:00Z",
    updated_at: "2026-05-04T00:00:00Z",
    api_key_encrypted: "encrypted-secret-that-must-not-render",
    api_key: "plaintext-secret-that-must-not-render",
    ...overrides,
  };
}

describe("ProvidersPage", () => {
  it("lists provider masks and never renders plaintext or encrypted secrets", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        const u = String(url);
        if (u.includes("/admin/providers")) {
          return jsonResponse([providerRow()]);
        }
        return jsonResponse({}, { status: 404 });
      }),
    );

    const { container } = render(<ProvidersPage />);

    expect(await screen.findByText("Primary OpenAI")).toBeInTheDocument();
    expect(screen.getByText("sk-t...cret")).toBeInTheDocument();
    expect(screen.getByText("bad key [redacted]")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("plaintext-secret-that-must-not-render");
    expect(container).not.toHaveTextContent("encrypted-secret-that-must-not-render");
  });

  it("saves provider keys, clears the secret input, tests, and disables", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      if (u.endsWith("/admin/providers") && (!init || init.method === undefined)) {
        return jsonResponse([providerRow()]);
      }
      if (u.endsWith("/admin/providers") && init?.method === "POST") {
        expect(String(init.body)).toContain("sk-live-secret");
        return jsonResponse(providerRow(), { status: 201 });
      }
      if (u.endsWith("/admin/providers/provider-1/test")) {
        return jsonResponse({ status: "ok", latency_ms: 12, error: null });
      }
      if (u.endsWith("/admin/providers/provider-1/disable")) {
        return jsonResponse(
          providerRow({ is_active: false, revoked_at: "2026-05-04T00:01:00Z" }),
        );
      }
      return jsonResponse({}, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ProvidersPage />);
    expect(await screen.findByText("Primary OpenAI")).toBeInTheDocument();

    const secretInput = screen.getByPlaceholderText(
      "Paste provider API key",
    ) as HTMLInputElement;
    fireEvent.change(screen.getByPlaceholderText("Primary"), {
      target: { value: "Primary OpenAI" },
    });
    fireEvent.change(secretInput, { target: { value: "sk-live-secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Save provider" }));

    await waitFor(() => expect(secretInput.value).toBe(""));
    expect(await screen.findByText(/Provider credential saved/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Test" }));
    expect(await screen.findByText("12ms")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disable" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/admin/providers/provider-1/disable"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});
