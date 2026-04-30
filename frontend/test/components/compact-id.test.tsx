import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CompactId } from "@/components/ui";

describe("CompactId", () => {
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

  it("renders an em dash for empty values", () => {
    render(<CompactId value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders a shortened ID and copies the full value", async () => {
    render(<CompactId value="gw-e4e28c1234567890e504" prefixLength={9} suffixLength={4} />);
    expect(screen.getByText("gw-e4e28c…e504")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy" }));
    });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("gw-e4e28c1234567890e504");
  });
});

