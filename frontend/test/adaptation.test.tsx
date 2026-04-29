import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("next/link", () => {
  return {
    default: ({ href, children, ...rest }: { href?: string; children?: React.ReactNode }) => (
      <a href={typeof href === "string" ? href : "#"} {...rest}>
        {children}
      </a>
    ),
  };
});

function setHrefSpy() {
  Object.defineProperty(window, "location", {
    value: { ...window.location, href: "http://localhost:3000/" },
    writable: true,
  });
}

function mockFetchSequence(responses: Array<{ status: number; body?: unknown; contentType?: string }>) {
  const fn = vi.fn();
  for (const r of responses) {
    fn.mockResolvedValueOnce({
      ok: r.status >= 200 && r.status < 300,
      status: r.status,
      headers: new Headers({ "content-type": r.contentType ?? "application/json" }),
      text: async () => (r.body === undefined ? "" : typeof r.body === "string" ? r.body : JSON.stringify(r.body)),
    } as Response);
  }
  (globalThis as unknown as { fetch: typeof fetch }).fetch = fn as unknown as typeof fetch;
  return fn;
}

describe("Adaptation BO pages", () => {
  it("401 from /admin/adaptation/* redirects to /login", async () => {
    setHrefSpy();
    mockFetchSequence([{ status: 401, body: { detail: "unauthorized" } }]);

    const { default: PlansPage } = await import("../app/adaptation/plans/page");
    render(<PlansPage />);

    await waitFor(() => {
      expect(window.location.href).toBe("/login");
    });
  });

  it("ProblemDetails detail is displayed on list error", async () => {
    mockFetchSequence([
      { status: 400, contentType: "application/problem+json", body: { title: "Bad Request", detail: "invalid filter" } },
    ]);

    const { default: PlansPage } = await import("../app/adaptation/plans/page");
    render(<PlansPage />);

    expect(await screen.findByText("invalid filter")).toBeInTheDocument();
  });

  it("ProblemDetails banner shows traceId when present", async () => {
    mockFetchSequence([
      {
        status: 400,
        contentType: "application/problem+json",
        body: { title: "Bad Request", detail: "bad", status: 400, traceId: "trace-xyz" },
      },
    ]);

    const { default: PlansPage } = await import("../app/adaptation/plans/page");
    render(<PlansPage />);

    expect(await screen.findByText(/trace-xyz/)).toBeInTheDocument();
  });

  it("start run navigates to /adaptation/runs/{runId}", async () => {
    setHrefSpy();
    mockFetchSequence([
      {
        status: 200,
        body: [
          {
            id: "plan_1",
            status: "Approved",
            domainKey: "dk",
            taskDescription: "task",
            recommendedStrategy: "s",
            recipeKey: "r",
            requiresHumanApproval: true,
            createdAt: "2026-01-01T00:00:00Z",
          },
        ],
      },
      { status: 200, body: { runId: "run_123" } },
    ]);

    const { default: PlansPage } = await import("../app/adaptation/plans/page");
    render(<PlansPage />);

    await screen.findByText("dk");
    fireEvent.click(screen.getByText("Start run"));

    await waitFor(() => {
      expect(window.location.href).toBe("/adaptation/runs/run_123");
    });
  });

  it("approve sends POST to /admin/adaptation/plans/{id}/approve", async () => {
    const fetchMock = mockFetchSequence([
      {
        status: 200,
        body: [
          {
            id: "plan_1",
            status: "Draft",
            domainKey: "dk",
            taskDescription: "task",
            recommendedStrategy: "s",
            recipeKey: "r",
            requiresHumanApproval: false,
            createdAt: "2026-01-01T00:00:00Z",
          },
        ],
      },
      { status: 200, body: { ok: true } },
      {
        status: 200,
        body: [
          {
            id: "plan_1",
            status: "Approved",
            domainKey: "dk",
            taskDescription: "task",
            recommendedStrategy: "s",
            recipeKey: "r",
            requiresHumanApproval: false,
            createdAt: "2026-01-01T00:00:00Z",
          },
        ],
      },
    ]);

    const { default: PlansPage } = await import("../app/adaptation/plans/page");
    render(<PlansPage />);

    await screen.findByText("Approve");
    fireEvent.click(screen.getByText("Approve"));

    await waitFor(() => {
      const approveCall = fetchMock.mock.calls.find(
        (call) => typeof call[0] === "string" && call[0].includes("/admin/adaptation/plans/plan_1/approve"),
      );
      expect(approveCall).toBeTruthy();
      expect(approveCall?.[1]).toMatchObject({ method: "POST" });
    });
  });

  it("plan detail renders runs-for-plan table rows", async () => {
    mockFetchSequence([
      { status: 200, body: { id: "plan_1", status: "Approved", domainKey: "dk" } },
      { status: 200, body: [{ runId: "run_1", status: "Completed", createdAt: "2026-01-01T00:00:00Z" }] },
    ]);

    const { default: PlanDetail } = await import("../app/adaptation/plans/[id]/page");
    render(<PlanDetail params={{ id: "plan_1" }} />);

    expect(await screen.findByText("run_1")).toBeInTheDocument();
    expect(screen.getByText("Runs for this plan")).toBeInTheDocument();
  });

  it("run detail shows manifest summary and treats adapter-profile 404 as no profile", async () => {
    mockFetchSequence([
      {
        status: 200,
        body: {
          runId: "run_1",
          id: "run_1",
          status: "Completed",
          steps: [{ stepKey: "s1", executorKey: "e1", status: "completed" }],
        },
      },
      {
        status: 200,
        body: {
          runnerVersion: "rv-1",
          plannerVersion: "pv-1",
          corpusSnapshotId: "cs-1",
          indexManifestId: "im-1",
        },
      },
      { status: 404, body: { title: "Not Found", detail: "no profile" } },
    ]);

    const { default: RunDetail } = await import("../app/adaptation/runs/[id]/page");
    render(<RunDetail params={{ id: "run_1" }} />);

    expect(await screen.findByText("Manifest Summary")).toBeInTheDocument();
    expect(await screen.findByText("rv-1")).toBeInTheDocument();
    expect(await screen.findByText("No profile produced yet")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("profile detail highlights failed blocking gate", async () => {
    mockFetchSequence([
      {
        status: 200,
        body: {
          profileId: "prof_1",
          status: "Rejected",
          approvedForRuntime: false,
          gateResults: [{ gateKey: "safety.blocking", blocking: true, passed: false, message: "unsafe" }],
        },
      },
    ]);

    const { default: ProfileDetail } = await import("../app/adaptation/profiles/[id]/page");
    const { container } = render(<ProfileDetail params={{ id: "prof_1" }} />);

    await screen.findByText("Gate Results");
    const row = container.querySelector("tr.row-warning");
    expect(row).toBeTruthy();
    expect(await screen.findByText("unsafe")).toBeInTheDocument();
  });
});

describe("adaptationApi problem parsing", () => {
  it("parseAdaptationProblem reads trace_id alias", async () => {
    const { parseAdaptationProblem } = await import("../lib/adaptationApi");
    const p = parseAdaptationProblem({
      ok: false,
      error: { title: "T", detail: "D", status: 422, trace_id: "tid-1" },
    });
    expect(p?.traceId).toBe("tid-1");
    expect(p?.detail).toBe("D");
  });
});
