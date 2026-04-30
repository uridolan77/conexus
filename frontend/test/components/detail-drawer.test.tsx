import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DetailDrawer } from "@/components/ui";

describe("DetailDrawer", () => {
  it("does not render when closed", () => {
    render(
      <DetailDrawer open={false} onClose={vi.fn()} title="Test Drawer">
        <p>drawer content</p>
      </DetailDrawer>,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders when open", () => {
    render(
      <DetailDrawer open onClose={vi.fn()} title="Test Drawer">
        <p>drawer content</p>
      </DetailDrawer>,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("drawer content")).toBeInTheDocument();
    expect(screen.getByText("Test Drawer")).toBeInTheDocument();
  });

  it("closes when close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <DetailDrawer open onClose={onClose} title="Test Drawer">
        <p>content</p>
      </DetailDrawer>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes when backdrop is clicked", () => {
    const onClose = vi.fn();
    const { container } = render(
      <DetailDrawer open onClose={onClose} title="Test Drawer">
        <p>content</p>
      </DetailDrawer>,
    );
    const backdrop = container.querySelector(".drawer-backdrop") as HTMLElement;
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes on Escape key", () => {
    const onClose = vi.fn();
    render(
      <DetailDrawer open onClose={onClose} title="Test Drawer">
        <p>content</p>
      </DetailDrawer>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not call onClose for non-Escape keys", () => {
    const onClose = vi.fn();
    render(
      <DetailDrawer open onClose={onClose} title="Test Drawer">
        <p>content</p>
      </DetailDrawer>,
    );
    fireEvent.keyDown(document, { key: "Enter" });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("uses aria-labelledby pointing to the title", () => {
    render(
      <DetailDrawer open onClose={vi.fn()} title="My Drawer">
        <p>body</p>
      </DetailDrawer>,
    );
    const dialog = screen.getByRole("dialog");
    const labelId = dialog.getAttribute("aria-labelledby");
    expect(labelId).toBeTruthy();
    const titleEl = document.getElementById(labelId!);
    expect(titleEl?.textContent).toBe("My Drawer");
  });
});
