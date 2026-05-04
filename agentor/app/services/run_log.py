"""RunLogService: append-only log of node outcomes for a workflow run.

This is an in-memory implementation. Replace with a DB-backed version when
persistence is required.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models import AgentRun, NodeOutcome, NodeStatus, RunStatus

logger = logging.getLogger(__name__)


class RunLogEntry:
    """A single entry written to the run log."""

    __slots__ = ("run_id", "workflow_name", "event", "timestamp", "detail")

    def __init__(
        self,
        run_id: str,
        workflow_name: str,
        event: str,
        detail: dict[str, object] | None = None,
    ) -> None:
        self.run_id = run_id
        self.workflow_name = workflow_name
        self.event = event
        self.timestamp = datetime.now(timezone.utc)
        self.detail = detail or {}

    def __repr__(self) -> str:
        return (
            f"RunLogEntry(run_id={self.run_id!r}, event={self.event!r}, "
            f"timestamp={self.timestamp.isoformat()})"
        )


class RunLogService:
    """Records workflow events for a single AgentRun.

    Events are kept in memory. Call ``entries_for(run_id)`` to query them.
    """

    def __init__(self) -> None:
        self._log: list[RunLogEntry] = []

    def log_run_started(self, run: AgentRun) -> None:
        self._append(run, "run.started", {"status": run.status.value})

    def log_run_finished(self, run: AgentRun) -> None:
        detail: dict[str, object] = {
            "status": run.status.value,
            "duration_ms": run.duration_ms,
        }
        if run.error:
            detail["error"] = run.error
        self._append(run, "run.finished", detail)

    def log_node_completed(self, run: AgentRun, outcome: NodeOutcome) -> None:
        detail: dict[str, object] = {
            "node_id": outcome.node_id,
            "node_name": outcome.node_name,
            "status": outcome.status.value,
            "duration_ms": outcome.duration_ms,
        }
        if outcome.error:
            detail["error"] = outcome.error
        event = (
            "node.completed"
            if outcome.status == NodeStatus.COMPLETED
            else "node.failed"
        )
        self._append(run, event, detail)

    def log_checkpoint_reached(self, run: AgentRun) -> None:
        if run.checkpoint is None:
            return
        self._append(
            run,
            "checkpoint.awaiting_approval",
            {"prompt": run.checkpoint.prompt},
        )

    def log_checkpoint_resolved(self, run: AgentRun) -> None:
        if run.checkpoint is None:
            return
        approved = run.checkpoint.approved
        self._append(
            run,
            "checkpoint.approved" if approved else "checkpoint.rejected",
            {
                "approved": approved,
                "reviewer_note": run.checkpoint.reviewer_note,
            },
        )

    def entries_for(self, run_id: str) -> list[RunLogEntry]:
        return [e for e in self._log if e.run_id == run_id]

    def all_entries(self) -> list[RunLogEntry]:
        return list(self._log)

    def _append(
        self,
        run: AgentRun,
        event: str,
        detail: dict[str, object] | None = None,
    ) -> None:
        entry = RunLogEntry(
            run_id=run.id,
            workflow_name=run.workflow_name,
            event=event,
            detail=detail,
        )
        self._log.append(entry)
        logger.debug(
            "RunLog [%s] %s %s — %s",
            run.id[:8],
            run.workflow_name,
            event,
            detail or "",
        )
