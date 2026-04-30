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
  it("Adaptation plans list renders rows from mocked API", async () => {
    mockFetchSequence([
      {
        status: 200,
        body: [
          {
            id: "plan_a",
            status: "Draft",
            domainKey: "domain-alpha",
            taskDescription: "First task",
            recommendedStrategy: "strat-a",
            recipeKey: "recipe-a",
            requiresHumanApproval: true,
            createdAt: "2026-01-01T00:00:00Z",
          },
          {
            id: "plan_b",
            status: "Approved",
            domainKey: "domain-beta",
            taskDescription: "Second task",
            recommendedStrategy: "strat-b",
            recipeKey: "recipe-b",
            requiresHumanApproval: false,
            createdAt: "2026-01-02T00:00:00Z",
          },
        ],
      },
    ]);

    const { default: PlansPage } = await import("../app/adaptation/plans/page");
    render(<PlansPage />);

    expect(await screen.findByText("domain-alpha")).toBeInTheDocument();
    expect(screen.getByText("domain-beta")).toBeInTheDocument();
    expect(screen.getByText("First task")).toBeInTheDocument();
    expect(screen.getByText("Second task")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /adaptation plans/i })).toBeInTheDocument();
  });

  it("Adaptation plan detail renders planning reasons", async () => {
    mockFetchSequence([
      {
        status: 200,
        body: {
          id: "plan_1",
          status: "Draft",
          domainKey: "dk",
          planningReasons: [
            { severity: "info", code: "PLAN-001", message: "Chose default recipe" },
            { severity: "warn", code: "PLAN-002", message: "Limited corpus" },
          ],
        },
      },
      { status: 200, body: [] },
    ]);

    const { default: PlanDetail } = await import("../app/adaptation/plans/[id]/page");
    render(<PlanDetail params={{ id: "plan_1" }} />);

    expect(await screen.findByText("Planner reasons")).toBeInTheDocument();
    expect(screen.getByText("PLAN-001")).toBeInTheDocument();
    expect(screen.getByText("Chose default recipe")).toBeInTheDocument();
    expect(screen.getByText("PLAN-002")).toBeInTheDocument();
    expect(screen.getByText("Limited corpus")).toBeInTheDocument();
  });

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

  it("StartRun calls POST .../run and navigates to /adaptation/runs/{runId}", async () => {
    setHrefSpy();
    const fetchMock = mockFetchSequence([
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

    const runCall = fetchMock.mock.calls.find(
      (call) => typeof call[0] === "string" && call[0].includes("/admin/adaptation/plans/plan_1/run"),
    );
    expect(runCall).toBeTruthy();
    expect(runCall?.[1]).toMatchObject({ method: "POST" });
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
      { status: 404, body: { title: "Not Found", detail: "no evidence" } },
    ]);

    const { default: RunDetail } = await import("../app/adaptation/runs/[id]/page");
    render(<RunDetail params={{ id: "run_1" }} />);

    expect(await screen.findByText("Manifest Summary")).toBeInTheDocument();
    expect(await screen.findByText("rv-1")).toBeInTheDocument();
    expect(await screen.findByText("No profile produced yet")).toBeInTheDocument();
    expect(await screen.findByText(/No evaluation evidence projection is available/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("run detail loads evaluation evidence when present", async () => {
    mockFetchSequence([
      {
        status: 200,
        body: {
          runId: "run_1",
          id: "run_1",
          status: "Completed",
          steps: [],
        },
      },
      { status: 200, body: { runnerVersion: "rv-1" } },
      { status: 404, body: { title: "Not Found", detail: "no profile" } },
      {
        status: 200,
        body: {
          id: "ev1",
          runId: "run_1",
          planId: "p1",
          domainKey: "dk",
          evalSetId: "es",
          createdAt: "2026-01-01T00:00:00Z",
          compositeScore: 0.9,
          projectionVersion: "v1",
          evidenceHash: "h",
          metrics: [],
          gates: [],
          securitySummary: {},
          questions: [],
        },
      },
    ]);

    const { default: RunDetail } = await import("../app/adaptation/runs/[id]/page");
    render(<RunDetail params={{ id: "run_1" }} />);

    expect(await screen.findByText("Evaluation evidence")).toBeInTheDocument();
    expect(await screen.findByText("ev1")).toBeInTheDocument();
  });

  it("AdapterProfileDetail highlights failed blocking gate", async () => {
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
      { status: 200, body: [] },
      { status: 200, body: [] },
      { status: 200, body: { adapterProfileId: "prof_1", registered: false } },
    ]);

    const { default: ProfileDetail } = await import("../app/adaptation/profiles/[id]/page");
    const { container } = render(<ProfileDetail params={{ id: "prof_1" }} />);

    await screen.findByText("Gate Results");
    const row = container.querySelector("tr.row-warning");
    expect(row).toBeTruthy();
    expect(await screen.findByText("unsafe")).toBeInTheDocument();
  });

  it("profile detail Approved shows publish control", async () => {
    mockFetchSequence([
      {
        status: 200,
        body: {
          profileId: "prof_1",
          status: "Approved",
          approvedForRuntime: true,
          domainKey: "dk",
          gateResults: [],
        },
      },
      { status: 200, body: [] },
      { status: 200, body: [] },
      { status: 200, body: { adapterProfileId: "prof_1", registered: false } },
      {
        status: 200,
        body: {
          profileId: "other",
          domainKey: "dk",
        },
      },
    ]);

    const { default: ProfileDetail } = await import("../app/adaptation/profiles/[id]/page");
    render(<ProfileDetail params={{ id: "prof_1" }} />);

    expect(await screen.findByText("Publish profile")).toBeInTheDocument();
  });

  it("Adaptation queue page loads diagnostics and renders JSON", async () => {
    mockFetchSequence([{ status: 200, body: { ok: true, queueDepth: 3 } }]);

    const { default: QueuePage } = await import("../app/adaptation/queue/page");
    render(<QueuePage />);

    fireEvent.click(await screen.findByText("Load diagnostics"));

    expect(await screen.findByText(/queueDepth/i)).toBeInTheDocument();
  });
});

describe("adaptationApi deployment client", () => {
  it("publishProfile posts only notes in JSON body", async () => {
    const calls: unknown[] = [];
    const fetchMock = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      calls.push({ url, body: init?.body });
      return {
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        text: async () =>
          JSON.stringify({
            adapterProfileId: "a1",
            gatewayProfileId: "g1",
            status: "Published",
          }),
      } as Response;
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    const { adaptationApi } = await import("../lib/adaptationApi");
    const res = await adaptationApi.publishProfile("p1", { notes: "hello" });
    expect(res.ok).toBe(true);
    const posted = calls.find((c) => typeof c === "object" && c && (c as { url: string }).url.includes("/publish")) as {
      body?: string;
    };
    expect(posted?.body).toBe(JSON.stringify({ notes: "hello" }));
  });

  it("activateCanary posts only canaryPercent", async () => {
    const bodies: string[] = [];
    const fetchMock = vi.fn().mockImplementation(async (_url: string, init?: RequestInit) => {
      if (init?.body && typeof init.body === "string") bodies.push(init.body);
      return {
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        text: async () =>
          JSON.stringify({
            activationId: "act1",
            adapterProfileId: "a1",
            status: "Canary",
          }),
      } as Response;
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    const { adaptationApi } = await import("../lib/adaptationApi");
    const res = await adaptationApi.activateCanary("p1", { canaryPercent: 12 });
    expect(res.ok).toBe(true);
    expect(bodies.some((b) => b === JSON.stringify({ canaryPercent: 12 }))).toBe(true);
  });

  it("rollbackProfile posts only reason", async () => {
    const bodies: string[] = [];
    const fetchMock = vi.fn().mockImplementation(async (_url: string, init?: RequestInit) => {
      if (init?.body && typeof init.body === "string") bodies.push(init.body);
      return {
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        text: async () => JSON.stringify({ adapterProfileId: "a1", status: "RolledBack" }),
      } as Response;
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    const { adaptationApi } = await import("../lib/adaptationApi");
    const res = await adaptationApi.rollbackProfile("p1", { reason: "bad" });
    expect(res.ok).toBe(true);
    expect(bodies.some((b) => b === JSON.stringify({ reason: "bad" }))).toBe(true);
  });

  it("queue repair does not include requestedByUserId in body", async () => {
    const postedBodies: string[] = [];
    const fetchMock = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      if (typeof init?.body === "string" && url.includes("/admin/adaptation/runs/queue/repair")) {
        postedBodies.push(init.body);
      }
      return {
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        text: async () => JSON.stringify({ ok: true }),
      } as Response;
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    const { adaptationApi } = await import("../lib/adaptationApi");
    const res = await adaptationApi.queueRepairApply({
      requestedByUserId: "attacker",
      requested_by_user_id: "attacker2",
      issueKinds: ["QUEUED_RUN_MISSING_WORK_ITEM"],
    });
    expect(res.ok).toBe(true);
    expect(postedBodies.length).toBeGreaterThan(0);
    const parsed = JSON.parse(postedBodies[0] ?? "{}") as Record<string, unknown>;
    expect(parsed.requestedByUserId).toBeUndefined();
    expect((parsed as Record<string, unknown>).requested_by_user_id).toBeUndefined();
    expect(parsed.issueKinds).toEqual(["QUEUED_RUN_MISSING_WORK_ITEM"]);
  });

  it("retryRun sends Idempotency-Key header", async () => {
    const captured: Array<{ url: string; headers?: HeadersInit }> = [];
    const fetchMock = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      captured.push({ url, headers: init?.headers });
      return {
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        text: async () => JSON.stringify({ ok: true }),
      } as Response;
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    const { adaptationApi } = await import("../lib/adaptationApi");
    const res = await adaptationApi.retryRun("run_1", { idempotencyKey: "idem-1" });
    expect(res.ok).toBe(true);
    const call = captured.find((c) => c.url.includes("/admin/adaptation/runs/run_1/retry"));
    expect(call).toBeTruthy();
    const hdrs = call?.headers as Record<string, string> | undefined;
    expect(hdrs?.["Idempotency-Key"]).toBe("idem-1");
  });

  it("resumeRun sends Idempotency-Key header", async () => {
    const captured: Array<{ url: string; headers?: HeadersInit }> = [];
    const fetchMock = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      captured.push({ url, headers: init?.headers });
      return {
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        text: async () => JSON.stringify({ ok: true }),
      } as Response;
    });
    (globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch;

    const { adaptationApi } = await import("../lib/adaptationApi");
    const res = await adaptationApi.resumeRun("run_1", { idempotencyKey: "idem-2" });
    expect(res.ok).toBe(true);
    const call = captured.find((c) => c.url.includes("/admin/adaptation/runs/run_1/resume"));
    expect(call).toBeTruthy();
    const hdrs = call?.headers as Record<string, string> | undefined;
    expect(hdrs?.["Idempotency-Key"]).toBe("idem-2");
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
