"use client";

import { useEffect, useState } from "react";
import { Alert, ErrorState, PageHeader } from "@/components/ui";
import { ProjectCreateCard } from "@/components/projects/ProjectCreateCard";
import { ProjectKeysCard } from "@/components/projects/ProjectKeysCard";
import { ProjectLimitsCard } from "@/components/projects/ProjectLimitsCard";
import { ProjectListCard } from "@/components/projects/ProjectListCard";
import { ProjectUsageCard } from "@/components/projects/ProjectUsageCard";
import {
  getProjectLimits,
  getProjectLimitsUsage,
  getProjectReservations,
  getStaleReservations,
  listProjectKeys,
  listProjects,
} from "@/lib/admin/projects";
import type {
  ApiKeyCreated,
  ApiKeyRow,
  ProjectLimits,
  ProjectLimitsReservations,
  ProjectLimitsUsage,
  ProjectRow,
  StaleReservationsList,
} from "@/lib/types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [keys, setKeys] = useState<ApiKeyRow[]>([]);
  const [latestIssuedKey, setLatestIssuedKey] = useState<ApiKeyCreated | null>(null);
  const [limits, setLimits] = useState<ProjectLimits | null>(null);
  const [limitsUsage, setLimitsUsage] = useState<ProjectLimitsUsage | null>(null);
  const [limitsReservations, setLimitsReservations] = useState<ProjectLimitsReservations | null>(null);
  const [staleReservationsSummary, setStaleReservationsSummary] = useState<StaleReservationsList | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [loadingLimits, setLoadingLimits] = useState(false);
  const [loadingLimitsUsage, setLoadingLimitsUsage] = useState(false);
  const [loadingLimitsReservations, setLoadingLimitsReservations] = useState(false);
  const [loadingStaleReservations, setLoadingStaleReservations] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function fetchProjects(autoSelectFirst = false) {
    setLoadingProjects(true);
    setError(null);
    try {
      const result = await listProjects();
      if (!result.ok) {
        setError(result.error.message);
        return;
      }
      setProjects(result.data);
      if (autoSelectFirst && !selectedProjectId && result.data.length > 0) {
        setSelectedProjectId(result.data[0].id);
      }
    } finally {
      setLoadingProjects(false);
    }
  }

  async function fetchKeys(projectId: string) {
    setLoadingKeys(true);
    try {
      const result = await listProjectKeys(projectId);
      if (result.ok) setKeys(result.data);
    } finally {
      setLoadingKeys(false);
    }
  }

  async function fetchLimits(projectId: string) {
    setLoadingLimits(true);
    try {
      const result = await getProjectLimits(projectId);
      if (result.ok) setLimits(result.data);
    } finally {
      setLoadingLimits(false);
    }
  }

  async function fetchUsage(projectId: string) {
    setLoadingLimitsUsage(true);
    try {
      const result = await getProjectLimitsUsage(projectId);
      if (result.ok) setLimitsUsage(result.data);
    } finally {
      setLoadingLimitsUsage(false);
    }
  }

  async function fetchReservations(projectId: string) {
    setLoadingLimitsReservations(true);
    try {
      const result = await getProjectReservations(projectId);
      if (result.ok) setLimitsReservations(result.data);
    } finally {
      setLoadingLimitsReservations(false);
    }
  }

  async function fetchStale(projectId: string) {
    setLoadingStaleReservations(true);
    try {
      const result = await getStaleReservations(projectId);
      if (result.ok) setStaleReservationsSummary(result.data);
    } finally {
      setLoadingStaleReservations(false);
    }
  }

  useEffect(() => {
    void fetchProjects(true);
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      setLatestIssuedKey(null);
      void fetchKeys(selectedProjectId);
      void fetchLimits(selectedProjectId);
      void fetchUsage(selectedProjectId);
      void fetchReservations(selectedProjectId);
      void fetchStale(selectedProjectId);
    } else {
      setKeys([]);
      setLimits(null);
      setLimitsUsage(null);
      setLimitsReservations(null);
      setStaleReservationsSummary(null);
    }
  }, [selectedProjectId]);

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  return (
    <>
      <PageHeader
        eyebrow="Gateway clients"
        title="Projects"
        description="Projects represent applications or services that call the Conexus gateway. Issue project API keys here and give those keys to gateway clients."
      />

      {error && <ErrorState message={error} />}
      {success && <Alert tone="success">{success}</Alert>}

      <ProjectCreateCard
        onCreated={(project) => {
          setSuccess(`Project "${project.name}" created.`);
          setSelectedProjectId(project.id);
          void fetchProjects();
        }}
      />

      <ProjectListCard
        projects={projects}
        selectedId={selectedProjectId}
        onSelect={setSelectedProjectId}
        loading={loadingProjects}
      />

      <ProjectKeysCard
        projectId={selectedProjectId || null}
        selectedProject={selectedProject}
        keys={keys}
        loadingKeys={loadingKeys}
        latestIssuedKey={latestIssuedKey}
        onKeyIssued={(key) => {
          setLatestIssuedKey(key);
          setSuccess("Project API key issued. Copy it now; it cannot be recovered later.");
          void fetchKeys(selectedProjectId);
          void fetchProjects();
        }}
        onKeyRevoked={() => {
          setSuccess("Project API key revoked.");
          void fetchKeys(selectedProjectId);
          void fetchProjects();
        }}
      />

      {selectedProjectId && (
        <ProjectLimitsCard
          projectId={selectedProjectId}
          limits={limits}
          loading={loadingLimits}
          onSaved={(updated) => {
            setLimits(updated);
            setSuccess("Project limits updated.");
            void fetchProjects();
            void fetchUsage(selectedProjectId);
            void fetchReservations(selectedProjectId);
          }}
        />
      )}

      {selectedProjectId && (
        <ProjectUsageCard
          projectId={selectedProjectId}
          limits={limits}
          usage={limitsUsage}
          reservations={limitsReservations}
          stale={staleReservationsSummary}
          loadingUsage={loadingLimitsUsage}
          loadingReservations={loadingLimitsReservations}
          loadingStale={loadingStaleReservations}
        />
      )}
    </>
  );
}
