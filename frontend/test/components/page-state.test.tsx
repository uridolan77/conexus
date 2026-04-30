import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PageState } from "@/components/ui";

describe("PageState", () => {
  it("shows loading label while loading", () => {
    render(<PageState loading loadingLabel="Fetching…"><p>content</p></PageState>);
    expect(screen.getByText("Fetching…")).toBeInTheDocument();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("shows default loading text when no label", () => {
    render(<PageState loading><p>content</p></PageState>);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows error state when error prop is set", () => {
    render(<PageState error="Something went wrong"><p>content</p></PageState>);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("shows empty state when empty is true", () => {
    render(
      <PageState empty emptyTitle="No items" emptyBody="Nothing here yet.">
        <p>content</p>
      </PageState>,
    );
    expect(screen.getByText("No items")).toBeInTheDocument();
    expect(screen.getByText("Nothing here yet.")).toBeInTheDocument();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("shows default empty title and body when not provided", () => {
    render(<PageState empty><p>content</p></PageState>);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.getByText("Nothing to show yet.")).toBeInTheDocument();
  });

  it("renders empty state action when provided", () => {
    render(
      <PageState empty emptyTitle="Empty" action={<button>Create one</button>}>
        <p>content</p>
      </PageState>,
    );
    expect(screen.getByRole("button", { name: "Create one" })).toBeInTheDocument();
  });

  it("renders children when not loading, error, or empty", () => {
    render(<PageState><p>actual content</p></PageState>);
    expect(screen.getByText("actual content")).toBeInTheDocument();
  });
});
