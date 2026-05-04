"""Tests for the Ontogony CMS workflow."""
import json

import pytest

from agentor_runtime.clients.tool import StubToolClient, ToolResult
from agentor_runtime.models import RunStatus
from agentor_runtime.workflows.ontogony_cms import OntogonyCmsWorkflow
from tests.conftest import MockConexusClient, make_conexus_response


def _plan_response() -> str:
    return json.dumps(
        {
            "title": "Why Astro is fast",
            "thesis": "Astro ships zero JS by default.",
            "outline": ["Islands architecture", "Static-first", "Zero JS default"],
        }
    )


def _critique_response(score: int = 8) -> str:
    return json.dumps({"score": score, "notes": ["Good structure", "Add examples"]})


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_workflow_completes_with_auto_approve():
    conexus = MockConexusClient()
    # PlanPageNode + WriteDraftNode + CritiqueDraftNode all get responses
    plan_resp = make_conexus_response(content=_plan_response(), model="conexus-smart")
    draft_resp = make_conexus_response(content="# Why Astro is fast\n\nAstro ships zero JS.")
    critique_resp = make_conexus_response(content=_critique_response(9))
    format_resp = make_conexus_response(content="formatted")  # FormatCmsNode does not call Conexus

    # The mock returns the same default for all calls; set a rich default
    conexus.set_default(plan_resp)
    # Override by call order via side effects via calls list inspection isn't needed
    # because we use per-model responses
    conexus.set_response("conexus-smart", plan_resp)
    conexus.set_response("conexus-fast", critique_resp)

    # Override the draft model response too
    _orig_chat = conexus.chat
    call_idx = [-1]

    async def _ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = _ordered_chat  # type: ignore[method-assign]

    workflow = OntogonyCmsWorkflow(conexus=conexus)
    run = await workflow.run("Why Astro is fast", auto_approve=True)

    assert run.status == RunStatus.COMPLETED
    assert run.state.get("page_plan") is not None
    assert run.state.get("draft") is not None
    assert run.state.get("critique") is not None
    assert run.state.get("cms_output") is not None

    cms = run.state.get("cms_output")
    assert "---" in cms  # frontmatter present
    assert "draft: true" in cms


async def test_workflow_pauses_at_approval_without_auto_approve():
    conexus = MockConexusClient()
    call_idx = [-1]
    plan_resp = make_conexus_response(content=_plan_response())
    draft_resp = make_conexus_response(content="Some draft text.")
    critique_resp = make_conexus_response(content=_critique_response(7))

    async def _ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = _ordered_chat  # type: ignore[method-assign]

    workflow = OntogonyCmsWorkflow(conexus=conexus)
    run = await workflow.run("Why Astro is fast", auto_approve=False)

    assert run.status == RunStatus.AWAITING_APPROVAL
    assert run.checkpoint is not None
    assert run.checkpoint.approved is None


async def test_workflow_includes_source_content():
    conexus = MockConexusClient()
    tool = StubToolClient()
    tool.register(
        "read_file",
        ToolResult(tool_name="read_file", content="Astro docs excerpt here."),
    )

    call_idx = [-1]
    plan_resp = make_conexus_response(content=_plan_response())
    draft_resp = make_conexus_response(content="Draft with sources.")
    critique_resp = make_conexus_response(content=_critique_response(8))

    async def _ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = _ordered_chat  # type: ignore[method-assign]

    workflow = OntogonyCmsWorkflow(conexus=conexus, tool=tool)
    run = await workflow.run(
        "Why Astro is fast",
        source_paths=["docs/astro.md"],
        auto_approve=True,
    )

    assert run.status == RunStatus.COMPLETED
    source_bundle = run.state.get("source_bundle")
    assert source_bundle is not None
    assert "Astro docs excerpt here." in source_bundle


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


async def test_workflow_fails_when_topic_missing():
    conexus = MockConexusClient()
    workflow = OntogonyCmsWorkflow(conexus=conexus)
    # Don't set topic — the PlanPageNode should raise ValueError
    run = await workflow.run("", auto_approve=True)

    assert run.status == RunStatus.FAILED
    assert run.error is not None


async def test_workflow_node_outcomes_recorded():
    conexus = MockConexusClient()
    call_idx = [-1]
    plan_resp = make_conexus_response(content=_plan_response())
    draft_resp = make_conexus_response(content="Draft.")
    critique_resp = make_conexus_response(content=_critique_response(6))

    async def _ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = _ordered_chat  # type: ignore[method-assign]

    workflow = OntogonyCmsWorkflow(conexus=conexus)
    run = await workflow.run("Astro", auto_approve=True)

    node_ids = [o.node_id for o in run.node_outcomes]
    assert "plan_page" in node_ids
    assert "write_draft" in node_ids
    assert "critique_draft" in node_ids
    assert "format_cms" in node_ids
    assert "approval" in node_ids
