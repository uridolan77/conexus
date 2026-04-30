import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DataTable } from "@/components/ui";

type Row = { id: string; name: string };

const columns = [
  { key: "name", header: "Name", render: (row: Row) => row.name },
];

const rows: Row[] = [
  { id: "1", name: "Alpha" },
  { id: "2", name: "Beta" },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(<DataTable columns={columns} rows={rows} aria-label="test table" />);
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("renders row data", () => {
    render(<DataTable columns={columns} rows={rows} aria-label="test table" />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("renders emptyMessage when rows is empty", () => {
    render(
      <DataTable
        columns={columns}
        rows={[]}
        aria-label="test table"
        emptyMessage="No rows found"
      />,
    );
    expect(screen.getByText("No rows found")).toBeInTheDocument();
  });

  it("does not render emptyMessage when rows exist", () => {
    render(
      <DataTable
        columns={columns}
        rows={rows}
        aria-label="test table"
        emptyMessage="No rows found"
      />,
    );
    expect(screen.queryByText("No rows found")).not.toBeInTheDocument();
  });

  it("renders no empty cell when rows is empty and no emptyMessage", () => {
    const { container } = render(
      <DataTable columns={columns} rows={[]} aria-label="test table" />,
    );
    // Only the header row — no body rows
    const rows = container.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(0);
  });
});
