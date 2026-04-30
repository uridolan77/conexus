"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Field,
  FormRow,
  Input,
  LoadingState,
  SectionHeader,
} from "@/components/ui";
import { formatDate } from "@/lib/api";
import { saveProjectLimits } from "@/lib/admin/projects";
import type { ProjectLimits } from "@/lib/types";

function parseOptionalInt(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed) || Number.isNaN(parsed) || parsed < 0) {
    throw new Error("Invalid non-negative integer.");
  }
  return parsed;
}

function parseOptionalFloat(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number.parseFloat(trimmed);
  if (!Number.isFinite(parsed) || Number.isNaN(parsed) || parsed < 0) {
    throw new Error("Invalid non-negative number.");
  }
  return parsed;
}

export function ProjectLimitsCard({
  projectId,
  limits,
  loading,
  onSaved,
}: {
  projectId: string;
  limits: ProjectLimits | null;
  loading: boolean;
  onSaved: (limits: ProjectLimits) => void;
}) {
  const [limitMode, setLimitMode] = useState<ProjectLimits["limit_mode"]>("disabled");
  const [monthlyCostLimit, setMonthlyCostLimit] = useState("");
  const [dailyRequestLimit, setDailyRequestLimit] = useState("");
  const [dailyTokenLimit, setDailyTokenLimit] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!limits) return;
    setLimitMode(limits.limit_mode);
    setMonthlyCostLimit(limits.monthly_cost_limit == null ? "" : String(limits.monthly_cost_limit));
    setDailyRequestLimit(limits.daily_request_limit == null ? "" : String(limits.daily_request_limit));
    setDailyTokenLimit(limits.daily_token_limit == null ? "" : String(limits.daily_token_limit));
  }, [limits]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    let payload: {
      limit_mode: ProjectLimits["limit_mode"];
      monthly_cost_limit: number | null;
      daily_request_limit: number | null;
      daily_token_limit: number | null;
    };
    try {
      payload = {
        limit_mode: limitMode,
        monthly_cost_limit: parseOptionalFloat(monthlyCostLimit),
        daily_request_limit: parseOptionalInt(dailyRequestLimit),
        daily_token_limit: parseOptionalInt(dailyTokenLimit),
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid limits.");
      return;
    }

    setSaving(true);
    try {
      const result = await saveProjectLimits(projectId, payload);
      if (!result.ok) {
        setError(result.error.message);
        return;
      }
      onSaved(result.data);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="card-muted">
      <SectionHeader
        title="Project Limits"
        description="Configure protective limits to prevent accidental runaway usage. Hard limits block before provider calls; soft limits are visible-only for now."
      />
      {error && <Alert tone="danger">{error}</Alert>}
      {loading ? (
        <LoadingState label="Loading limits..." />
      ) : (
        <form className="stack" onSubmit={handleSubmit}>
          <FormRow>
            <Field
              label="Limit mode"
              hint="disabled = no enforcement, soft = visible-only (M8A), hard = blocks before provider call"
            >
              <select
                className="input"
                value={limitMode}
                onChange={(e) => setLimitMode(e.target.value as ProjectLimits["limit_mode"])}
              >
                <option value="disabled">disabled</option>
                <option value="soft">soft</option>
                <option value="hard">hard</option>
              </select>
            </Field>
          </FormRow>

          <FormRow>
            <Field
              label="Monthly cost limit (USD)"
              hint="Nullable. Uses UTC calendar month boundaries."
            >
              <Input
                value={monthlyCostLimit}
                onChange={(e) => setMonthlyCostLimit(e.target.value)}
                placeholder="e.g. 25"
              />
            </Field>
          </FormRow>

          <FormRow>
            <Field
              label="Daily request limit"
              hint="Nullable. Counts all gateway requests, including failed. UTC day boundaries."
            >
              <Input
                value={dailyRequestLimit}
                onChange={(e) => setDailyRequestLimit(e.target.value)}
                placeholder="e.g. 1000"
              />
            </Field>
          </FormRow>

          <FormRow>
            <Field
              label="Daily token limit"
              hint="Nullable. Sums total_tokens for the UTC day; null token rows are ignored."
            >
              <Input
                value={dailyTokenLimit}
                onChange={(e) => setDailyTokenLimit(e.target.value)}
                placeholder="e.g. 500000"
              />
            </Field>
          </FormRow>

          <div className="inline-actions">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save limits"}
            </Button>
            {limits?.updated_at ? (
              <span className="muted">Last updated: {formatDate(limits.updated_at)}</span>
            ) : null}
          </div>
        </form>
      )}
    </Card>
  );
}
