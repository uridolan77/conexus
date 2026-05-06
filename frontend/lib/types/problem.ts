export type StepStatus = "not-run" | "running" | "passed" | "failed";

export type StepResult =
  | { ok: true; data: unknown }
  | { ok: false; status?: number; error: unknown };
