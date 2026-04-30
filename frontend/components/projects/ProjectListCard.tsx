"use client";

import {
  Button,
  Card,
  EmptyState,
  LoadingState,
  SectionHeader,
  StatusBadge,
  Table,
} from "@/components/ui";
import { formatDate } from "@/lib/api";
import type { ProjectRow } from "@/lib/types";

export function ProjectListCard({
  projects,
  selectedId,
  onSelect,
  loading,
}: {
  projects: ProjectRow[];
  selectedId: string;
  onSelect: (id: string) => void;
  loading: boolean;
}) {
  return (
    <Card>
      <SectionHeader
        title="Project List"
        description="Select a project to inspect and manage its gateway API keys."
      />
      {loading ? (
        <LoadingState label="Loading projects..." />
      ) : projects.length === 0 ? (
        <EmptyState title="No projects yet">
          Create a project to start issuing API keys for gateway clients.
        </EmptyState>
      ) : (
        <Table aria-label="Projects">
          <thead>
            <tr>
              <th>Name</th>
              <th>Active keys</th>
              <th>Total requests</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr
                key={project.id}
                className={project.id === selectedId ? "row-muted" : undefined}
              >
                <td>{project.name}</td>
                <td>{project.active_key_count}</td>
                <td>{project.total_request_count}</td>
                <td>{formatDate(project.created_at)}</td>
                <td>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => onSelect(project.id)}
                  >
                    {project.id === selectedId ? "Selected" : "Manage keys"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}
