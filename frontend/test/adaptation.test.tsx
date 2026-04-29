import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("next/link", () => {
  return {
    default: ({ href, children, ...rest }: any) => (
      <a href={typeof href === "string" ? href : href?.pathname ?? "#"} {...rest}>
        {children}
      </a>
    ),
  };
});

function setHrefSpy() {
  const original = window.location;
  // jsdom makes location non-configurable by default; redefine for tests.
  Object.defineProperty(window, "location", {
    value: { ...original, href: "http://localhost:3000/" },
    writable: true,
  });
}

function mockFetchSequence(responses: Array<{ status: number; body?: any; contentType?: string }>) {
  const fn = vi.fn();
  for (const r of responses) {
    fn.mockResolvedValueOnce({
      ok: r.status >= 200 && r.status < 300,
      status: r.status,
      headers: new Headers({ "content-type": r.contentType ?? "application/json" }),
      text: async () => (r.body === undefined ? "" : typeof r.body === "string" ? r.body : JSON.stringify(r.body)),
    } as any);
  }
  (globalThis as any).fetch = fn;
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

  it("start run navigates to /adaptation/runs/{runId}", async () => {
    setHrefSpy();
    mockFetchSequence([
      // listPlans initial load
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
      // startRun action
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

  it("plan detail renders runs-for-plan table rows", async () => {
    mockFetchSequence([
      // getPlan
      { status: 200, body: { id: "plan_1", status: "Approved", domainKey: "dk" } },
      // listRunsForPlan
      { status: 200, body: [{ runId: "run_1", status: "Completed", createdAt: "2026-01-01T00:00:00Z" }] },
    ]);

    const { default: PlanDetail } = await import("../app/adaptation/plans/[id]/page");
    render(<PlanDetail params={{ id: "plan_1" }} />);

    expect(await screen.findByText("run_1")).toBeInTheDocument();
    expect(screen.getByText("Runs for this plan")).toBeInTheDocument();
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

