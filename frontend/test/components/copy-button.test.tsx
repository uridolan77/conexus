import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CopyButton } from "@/components/ui";

describe("CopyButton", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders with default label", () => {
    render(<CopyButton value="test" />);
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });

  it("renders with custom label", () => {
    render(<CopyButton value="test" label="Copy key" />);
    expect(screen.getByRole("button", { name: "Copy key" })).toBeInTheDocument();
  });

  it("calls clipboard.writeText with the value when clicked", async () => {
    render(<CopyButton value="secret-value" />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button"));
    });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("secret-value");
  });

  it("shows 'Copied' feedback after click", async () => {
    render(<CopyButton value="secret-value" />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button"));
    });
    expect(screen.getByRole("button")).toHaveTextContent("Copied");
  });

  it("uses execCommand fallback when clipboard rejects", async () => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockRejectedValue(new Error("not allowed")) },
      writable: true,
      configurable: true,
    });
    const execCommand = vi.fn().mockReturnValue(true);
    document.execCommand = execCommand;

    render(<CopyButton value="fallback-test" />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button"));
    });

    await waitFor(() => {
      expect(execCommand).toHaveBeenCalledWith("copy");
    });
  });
});
