"""Tests for NodeExecutor and core models."""
import pytest

from agentor_runtime.executor import ApprovalRejectedError, ApprovalRequiredError, NodeExecutor
from agentor_runtime.models import (
    AgentRun,
    GraphNode,
    GraphState,
    HumanApprovalCheckpoint,
    NodeStatus,
    RunStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_node(node_id: str, *, fail: bool = False, raises: Exception | None = None):
    async def handler(state: GraphState) -> None:
        state.set(f"visited_{node_id}", True)
        if raises:
            raise raises
        if fail:
            raise RuntimeError(f"Node {node_id} failed")

    return GraphNode(id=node_id, name=node_id.capitalize(), handler=handler)


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


async def test_single_node_completes():
    node = make_node("a")
    executor = NodeExecutor([node])
    run = AgentRun(workflow_name="test")

    await executor.run(run)

    assert run.status == RunStatus.COMPLETED
    assert run.state.get("visited_a") is True
    assert len(run.node_outcomes) == 1
    assert run.node_outcomes[0].status == NodeStatus.COMPLETED


async def test_multiple_nodes_all_complete():
    nodes = [make_node("a"), make_node("b"), make_node("c")]
    executor = NodeExecutor(nodes)
    run = AgentRun(workflow_name="test")

    await executor.run(run)

    assert run.status == RunStatus.COMPLETED
    assert run.state.get("visited_a") is True
    assert run.state.get("visited_b") is True
    assert run.state.get("visited_c") is True
    assert all(o.status == NodeStatus.COMPLETED for o in run.node_outcomes)


async def test_node_failure_marks_run_failed():
    nodes = [make_node("a"), make_node("b", fail=True), make_node("c")]
    executor = NodeExecutor(nodes)
    run = AgentRun(workflow_name="test")

    await executor.run(run)

    assert run.status == RunStatus.FAILED
    assert "b" in run.error.lower() or "failed" in run.error.lower()
    # node c should not have run
    assert run.state.get("visited_c") is None
    # node b outcome should be FAILED
    b_outcome = next(o for o in run.node_outcomes if o.node_id == "b")
    assert b_outcome.status == NodeStatus.FAILED


async def test_run_timing_recorded():
    node = make_node("a")
    executor = NodeExecutor([node])
    run = AgentRun(workflow_name="test")

    await executor.run(run)

    assert run.started_at is not None
    assert run.finished_at is not None
    assert run.duration_ms is not None
    assert run.duration_ms >= 0


# ---------------------------------------------------------------------------
# Checkpoint behaviour
# ---------------------------------------------------------------------------


def make_checkpoint_node(node_id: str):
    async def handler(state: GraphState) -> None:
        state.set(
            "_checkpoint",
            HumanApprovalCheckpoint(
                prompt="Approve?",
                proposed_action={"action": "write"},
            ),
        )

    return GraphNode(id=node_id, name=node_id.capitalize(), handler=handler)


async def test_checkpoint_pauses_without_auto_approve():
    nodes = [make_node("a"), make_checkpoint_node("gate"), make_node("b")]
    executor = NodeExecutor(nodes)
    run = AgentRun(workflow_name="test")

    # run without auto-approve: should raise ApprovalRequiredError inside
    # executor, which sets run.status = AWAITING_APPROVAL
    await executor.run(run)

    assert run.status == RunStatus.AWAITING_APPROVAL
    assert run.checkpoint is not None
    # node b should not have run
    assert run.state.get("visited_b") is None


async def test_checkpoint_auto_approve_continues():
    nodes = [make_node("a"), make_checkpoint_node("gate"), make_node("b")]
    executor = NodeExecutor(nodes)
    run = AgentRun(workflow_name="test")

    await executor.run(run, auto_approve=True)

    assert run.status == RunStatus.COMPLETED
    assert run.state.get("visited_b") is True
    assert run.checkpoint is not None
    assert run.checkpoint.approved is True


async def test_checkpoint_rejected_marks_run_rejected():
    async def reject_handler(state: GraphState) -> None:
        cp = HumanApprovalCheckpoint(
            prompt="Approve?",
            proposed_action={"action": "write"},
        )
        cp.reject(note="not good enough")
        state.set("_checkpoint", cp)

    nodes = [
        GraphNode(id="gate", name="Gate", handler=reject_handler),
        make_node("b"),
    ]
    executor = NodeExecutor(nodes)
    run = AgentRun(workflow_name="test")

    await executor.run(run)

    assert run.status == RunStatus.REJECTED
    assert run.state.get("visited_b") is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_executor_requires_at_least_one_node():
    with pytest.raises(ValueError):
        NodeExecutor([])


async def test_node_outcome_duration_populated():
    node = make_node("a")
    executor = NodeExecutor([node])
    run = AgentRun(workflow_name="test")

    await executor.run(run)

    outcome = run.node_outcomes[0]
    assert outcome.started_at is not None
    assert outcome.finished_at is not None
    assert outcome.duration_ms is not None
    assert outcome.duration_ms >= 0


async def test_awaiting_approval_run_has_no_finished_at():
    """Runs paused at a checkpoint must not have finished_at set."""
    nodes = [make_checkpoint_node("gate"), make_node("b")]
    executor = NodeExecutor(nodes)
    run = AgentRun(workflow_name="test")

    await executor.run(run)

    assert run.status == RunStatus.AWAITING_APPROVAL
    assert run.finished_at is None, (
        "finished_at must remain None while the run is AWAITING_APPROVAL"
    )


# ---------------------------------------------------------------------------
# TODO: resume behavior
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="resume() not yet implemented — see NodeExecutor docstring")
async def test_resume_after_approval_continues_remaining_nodes():
    """After approving a checkpoint, remaining nodes should execute.

    Implement when NodeExecutor gains a resume(run) method that re-enters
    execution after the paused node using the existing run state.
    """
    nodes = [make_node("a"), make_checkpoint_node("gate"), make_node("b")]
    executor = NodeExecutor(nodes)
    run = AgentRun(workflow_name="test")

    await executor.run(run)
    assert run.status == RunStatus.AWAITING_APPROVAL

    # Human approves
    run.checkpoint.approve(note="looks good")

    # TODO: call executor.resume(run) when implemented
    # await executor.resume(run)
    # assert run.status == RunStatus.COMPLETED
    # assert run.state.get("visited_b") is True
