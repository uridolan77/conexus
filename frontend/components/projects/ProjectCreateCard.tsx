"use client";

import { FormEvent, useState } from "react";
import { Alert, Button, Card, Field, FormRow, Input, SectionHeader } from "@/components/ui";
import { createProject } from "@/lib/admin/projects";
import type { ProjectRow } from "@/lib/types";

export function ProjectCreateCard({ onCreated }: { onCreated: (project: ProjectRow) => void }) {
  const [projectName, setProjectName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const name = projectName.trim();
    if (!name) {
      setError("Project name is required.");
      return;
    }
    setError(null);
    setCreating(true);
    try {
      const result = await createProject(name);
      if (!result.ok) {
        setError(result.error.message);
        return;
      }
      setProjectName("");
      onCreated(result.data);
    } finally {
      setCreating(false);
    }
  }

  return (
    <Card>
      <SectionHeader
        title="Create Project"
        description="Use clear names like app, team, or environment. Keys are managed after project creation."
      />
      {error && <Alert tone="danger">{error}</Alert>}
      <form className="stack" onSubmit={handleSubmit}>
        <FormRow>
          <Field label="Project name" hint="Example: payments-prod">
            <Input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="payments"
            />
          </Field>
        </FormRow>
        <div className="inline-actions">
          <Button type="submit" disabled={creating}>
            {creating ? "Creating..." : "Create project"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
