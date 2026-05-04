"""NodeExecutor: runs a sequence of GraphNodes, manages state and lifecycle."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from agentor_runtime.models import (
    AgentRun,
    GraphNode,
    HumanApprovalCheckpoint,
    NodeOutcome,
    NodeStatus,
    RunStatus,
)

logger = logging.getLogger(__name__)


class ApprovalRequiredError(Exception):
    """Raised when execution reaches an approval checkpoint."""

    def __init__(self, checkpoint: HumanApprovalCheckpoint) -> None:
        super().__init__("Human approval required before continuing")
        self.checkpoint = checkpoint


class ApprovalRejectedError(Exception):
    """Raised when a checkpoint is explicitly rejected."""

    def __init__(self, note: str | None = None) -> None:
        super().__init__(f"Workflow rejected by reviewer: {note}")
        self.note = note


class NodeExecutor:
    """Runs a list of GraphNodes in order, sharing GraphState between them.

    When a node installs a :class:`~agentor_runtime.models.HumanApprovalCheckpoint`,
    execution pauses and the run is left in ``AWAITING_APPROVAL``. The caller is
    responsible for resolving the checkpoint (``approve()`` / ``reject()``) and
    re-executing from the point of interruption. A ``resume()`` helper is not yet
    implemented; re-run with ``auto_approve=True`` for fully automated pipelines.
    """

    def __init__(self, nodes: list[GraphNode]) -> None:
        if not nodes:
            raise ValueError("NodeExecutor requires at least one node")
        self._nodes = nodes

    async def run(self, run: AgentRun, *, auto_approve: bool = False) -> AgentRun:
        """Execute all nodes sequentially.

        Args:
            run: The AgentRun instance. ``run.state`` is mutated in place.
            auto_approve: If True, automatically approve any checkpoint
                          (useful for tests or fully automated pipelines).

        Returns:
            The same ``run`` instance in its terminal state.
        """
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)

        try:
            await self._execute_nodes(run, self._nodes, auto_approve=auto_approve)
        except ApprovalRequiredError:
            # Status already set to AWAITING_APPROVAL inside _execute_nodes
            pass
        except ApprovalRejectedError as exc:
            run.status = RunStatus.REJECTED
            run.error = str(exc)
        except Exception as exc:
            run.status = RunStatus.FAILED
            run.error = str(exc)
            logger.exception("Workflow %s failed in run %s", run.workflow_name, run.id)
        else:
            if run.status == RunStatus.RUNNING:
                run.status = RunStatus.COMPLETED

        # Do not stamp finished_at while awaiting a human decision; the run is not
        # terminal yet and the timestamp would be misleading.
        if run.status != RunStatus.AWAITING_APPROVAL:
            run.finished_at = datetime.now(timezone.utc)
        return run

    async def _execute_nodes(
        self, run: AgentRun, nodes: list[GraphNode], *, auto_approve: bool
    ) -> None:
        for node in nodes:
            if run.is_terminal:
                break

            outcome = NodeOutcome(
                node_id=node.id,
                node_name=node.name,
                status=NodeStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
            run.node_outcomes.append(outcome)
            logger.debug("Run %s: starting node %s (%s)", run.id, node.id, node.name)

            try:
                await node.handler(run.state)

                # Promote a checkpoint written to state by the node handler
                pending_cp = run.state.get("_checkpoint")
                if pending_cp is not None and run.checkpoint is None:
                    run.checkpoint = pending_cp
                    run.state.data.pop("_checkpoint", None)

                # Check if the node installed a checkpoint
                if run.checkpoint is not None and not run.checkpoint.is_decided:
                    if auto_approve:
                        run.checkpoint.approve(note="auto-approved")
                    else:
                        run.status = RunStatus.AWAITING_APPROVAL
                        outcome.status = NodeStatus.COMPLETED
                        outcome.finished_at = datetime.now(timezone.utc)
                        raise ApprovalRequiredError(run.checkpoint)

                if run.checkpoint is not None and run.checkpoint.approved is False:
                    raise ApprovalRejectedError(run.checkpoint.reviewer_note)

                outcome.status = NodeStatus.COMPLETED

            except (ApprovalRequiredError, ApprovalRejectedError):
                raise
            except Exception as exc:
                outcome.status = NodeStatus.FAILED
                outcome.error = str(exc)
                logger.exception(
                    "Run %s: node %s (%s) failed", run.id, node.id, node.name
                )
                raise
            finally:
                if outcome.finished_at is None:
                    outcome.finished_at = datetime.now(timezone.utc)

            logger.debug("Run %s: node %s completed", run.id, node.id)
