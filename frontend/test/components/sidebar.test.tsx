import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "@/components/bo/Sidebar";
import { NAV_SECTIONS } from "@/lib/navigation";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className, "aria-current": ariaCurrent }: {
    href: string;
    children: React.ReactNode;
    className?: string;
    "aria-current"?: string;
  }) => (
    <a href={href} className={className} aria-current={ariaCurrent}>
      {children}
    </a>
  ),
}));

describe("Sidebar", () => {
  it("renders the brand name", () => {
    render(<Sidebar environment="Local" />);
    expect(screen.getByText("Conexus")).toBeInTheDocument();
  });

  it("renders the environment pill", () => {
    render(<Sidebar environment="Dev" />);
    expect(screen.getByText("Dev")).toBeInTheDocument();
  });

  it("renders all section group labels", () => {
    render(<Sidebar environment="Local" />);
    const groupLabels = document.querySelectorAll(".nav-group-label");
    const groupTitles = Array.from(groupLabels).map((el) => el.textContent);
    for (const section of NAV_SECTIONS) {
      expect(groupTitles).toContain(section.title);
    }
  });

  it("renders all navigation links", () => {
    render(<Sidebar environment="Local" />);
    for (const section of NAV_SECTIONS) {
      for (const item of section.items) {
        // Use getAllByText to handle cases where a label matches a section title too
        const matches = screen.getAllByText(item.label);
        expect(matches.length).toBeGreaterThan(0);
      }
    }
  });

  it("marks the root link as active when pathname is /", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/");
    render(<Sidebar environment="Local" />);
    const dashboardLink = screen.getByRole("link", { name: /Dashboard/i });
    expect(dashboardLink).toHaveAttribute("aria-current", "page");
  });

  it("does not mark Dashboard as active on a subpage", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/projects");
    render(<Sidebar environment="Local" />);
    const dashboardLink = screen.getByRole("link", { name: /Dashboard/i });
    expect(dashboardLink).not.toHaveAttribute("aria-current");
  });

  it("marks projects link as active when on /projects", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/projects");
    render(<Sidebar environment="Local" />);
    const projectsLink = screen.getByRole("link", { name: /Projects/i });
    expect(projectsLink).toHaveAttribute("aria-current", "page");
  });

  it("marks adaptation plans link as active on a nested adaptation route", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/adaptation/plans/some-id");
    render(<Sidebar environment="Local" />);
    const plansLink = screen.getByRole("link", { name: /Adaptation Plans/i });
    expect(plansLink).toHaveAttribute("aria-current", "page");
  });
});
