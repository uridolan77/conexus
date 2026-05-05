"""Core domain models for Agentor workflow orchestration."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class GraphState:
    """Mutable shared state passed between nodes in a workflow run."""

    data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, values: dict[str, Any]) -> None:
        self.data.update(values)

    def snapshot(self) -> dict[str, Any]:
        """Return a shallow copy of current state."""
        return dict(self.data)


NodeHandler = Callable[["GraphState"], Coroutine[Any, Any, None]]


@dataclass
class GraphNode:
    """A named step in a workflow with an async handler."""

    id: str
    name: str
    handler: NodeHandler
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("GraphNode.id must not be empty")
        if not self.name:
            raise ValueError("GraphNode.name must not be empty")


@dataclass
class NodeOutcome:
    """Record of a single node execution."""

    node_id: str
    node_name: str
    status: NodeStatus
    started_at: datetime
    finished_at: datetime | None = None
    error: str | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return delta.total_seconds() * 1000


@dataclass
class HumanApprovalCheckpoint:
    """Pause execution until a human approves or rejects a proposed action."""

    prompt: str
    proposed_action: dict[str, Any]
    approved: bool | None = None
    reviewer_note: str | None = None
    decided_at: datetime | None = None

    @property
    def is_decided(self) -> bool:
        return self.approved is not None

    def approve(self, note: str | None = None) -> None:
        self.approved = True
        self.reviewer_note = note
        self.decided_at = datetime.now(timezone.utc)

    def reject(self, note: str | None = None) -> None:
        self.approved = False
        self.reviewer_note = note
        self.decided_at = datetime.now(timezone.utc)


@dataclass
class AgentRun:
    """A running or completed workflow instance."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = ""
    status: RunStatus = RunStatus.PENDING
    state: GraphState = field(default_factory=GraphState)
    node_outcomes: list[NodeOutcome] = field(default_factory=list)
    checkpoint: HumanApprovalCheckpoint | None = None
    next_node_index: int = 0
    paused_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.REJECTED,
        )

    @property
    def duration_ms(self) -> float | None:
        if self.started_at is None or self.finished_at is None:
            return None
        delta = self.finished_at - self.started_at
        return delta.total_seconds() * 1000
