import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import LimitsPage from "@/app/limits/page";

describe("LimitsPage", () => {
  it("renders and links to Projects", async () => {
    render(<LimitsPage />);
    expect(await screen.findByText("Limits")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Projects" })).toHaveAttribute("href", "/projects");
  });

  it("renders empty state guidance", async () => {
    render(<LimitsPage />);
    expect(await screen.findByText("Manage limits per project")).toBeInTheDocument();
  });
});

