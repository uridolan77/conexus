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
            "collection": "essays",
            "title": "Why Astro is fast",
            "slug": "why-astro-is-fast",
            "summary": "Astro ships zero JS by default.",
            "thesis": "Astro ships zero JS by default.",
            "register": "R2",
            "outline": ["Islands architecture", "Static-first", "Zero JS default"],
            "cites": ["docs/astro.md"],
            "whereNext": [
                {"kind": "essay", "slug": "static-site-generation", "title": "SSG", "why": "Next read"}
            ],
        }
    )


def _critique_response(score: int = 8) -> str:
    return json.dumps(
        {
            "clarity": score,
            "rigor": score,
            "hallucination_risk": 2,
            "style_fit": score,
            "overall": score,
            "blocking_issues": [],
            "revision_notes": ["Good structure", "Add examples"],
            "approved_for_human_review": True,
        }
    )


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
    assert 'status: "draft"' in cms
    assert 'title: "Why Astro is fast"' in cms
    assert 'summary: "Astro ships zero JS by default."' in cms
    assert 'register: "R2"' in cms
    assert "readingTime: " in cms
    assert 'createdAt: "' in cms
    assert 'updatedAt: "' in cms
    assert 'cites:' in cms
    assert 'whereNext:' in cms
    assert run.state.get("target_path") == "src/content/essays/why-astro-is-fast.mdx"


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
    assert run.state.get("target_path") is not None


async def test_workflow_includes_source_content():
    conexus = MockConexusClient()
    tool = StubToolClient()
    tool.register(
        "read_source_file",
        ToolResult(tool_name="read_source_file", content="Astro docs excerpt here."),
        path="docs/astro.md",
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
    manifest = run.state.get("source_manifest")
    assert manifest == [{"path": "docs/astro.md", "ok": True, "error": None}]


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


async def test_parse_json_response_fallback_handles_fenced_json():
    conexus = MockConexusClient()
    plan_resp = make_conexus_response(
        content="Here you go:\n```json\n" + _plan_response() + "\n```\nThanks!"
    )
    draft_resp = make_conexus_response(content="Draft.")
    critique_resp = make_conexus_response(content=_critique_response(6))

    call_idx = [-1]

    async def _ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = _ordered_chat  # type: ignore[method-assign]
    workflow = OntogonyCmsWorkflow(conexus=conexus)
    run = await workflow.run("Astro", auto_approve=True)

    assert run.status == RunStatus.COMPLETED
    plan = run.state.get("page_plan")
    assert plan is not None
    assert plan.get("slug") == "why-astro-is-fast"


async def test_frontmatter_escapes_quotes_and_colons():
    conexus = MockConexusClient()
    plan = {
        "collection": "essays",
        "title": 'A "quote": test',
        "slug": "a-quote-test",
        "summary": 'Summary with "quotes": and colon.',
        "thesis": "x",
        "register": "neutral",
        "outline": [],
        "cites": ["a:b", 'x "y"'],
        "whereNext": [{"kind": "essay", "slug": "next-step", "title": "Next:step", "why": 'Because "reasons"'}],
    }
    plan_resp = make_conexus_response(content=json.dumps(plan))
    draft_resp = make_conexus_response(content="Draft.")
    critique_resp = make_conexus_response(content=_critique_response(6))

    call_idx = [-1]

    async def _ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = _ordered_chat  # type: ignore[method-assign]
    workflow = OntogonyCmsWorkflow(conexus=conexus)
    run = await workflow.run("Astro", auto_approve=True)

    cms = run.state.get("cms_output")
    assert cms is not None
    assert 'title: "A \\"quote\\": test"' in cms
    assert 'summary: "Summary with \\"quotes\\": and colon."' in cms
    assert '  - "a:b"' in cms
    assert '  - "x \\"y\\""' in cms
    # invalid register should be omitted
    assert "register:" not in cms
    # object whereNext should not be stringified
    assert "kind:" in cms
    assert 'slug: "next-step"' in cms
    assert 'title: "Next:step"' in cms
    assert 'why: "Because \\"reasons\\""' in cms


async def test_where_next_drops_entries_without_kind_and_slug():
    """Invalid whereNext rows must not appear in frontmatter."""
    conexus = MockConexusClient()
    plan = {
        "collection": "essays",
        "title": "T",
        "slug": "t",
        "summary": "S",
        "thesis": "x",
        "register": "R1",
        "outline": [],
        "cites": [],
        "whereNext": [
            {"kind": "essay", "slug": "valid-slug", "title": "OK", "why": "w"},
            {"kind": "", "slug": "ignored", "title": "x"},
            {"kind": "essay", "slug": "", "title": "y"},
            {"title": "no kind or slug"},
        ],
    }
    plan_resp = make_conexus_response(content=json.dumps(plan))
    draft_resp = make_conexus_response(content="Draft.")
    critique_resp = make_conexus_response(content=_critique_response(6))
    call_idx = [-1]

    async def _ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = _ordered_chat  # type: ignore[method-assign]
    workflow = OntogonyCmsWorkflow(conexus=conexus)
    run = await workflow.run("T", auto_approve=True)
    cms = run.state.get("cms_output")
    assert cms is not None
    assert 'slug: "valid-slug"' in cms
    assert 'slug: "ignored"' not in cms


async def test_plan_is_normalized_to_schema_safe_lists_and_collection():
    conexus = MockConexusClient()
    plan = {
        "collection": "essay",
        "title": "Normalized",
        "slug": "normalized",
        "summary": "Summary",
        "thesis": "Thesis",
        "register": "R9",
        "outline": ["Keep me", "", 42, "  Also keep  "],
        "cites": ["docs/a.md", "", {"bad": True}, " docs/b.md "],
        "whereNext": [
            {"kind": "essay", "slug": "good", "title": " Good ", "why": " Why "},
            {"kind": "essay", "slug": ""},
            "bad",
        ],
    }
    plan_resp = make_conexus_response(content=json.dumps(plan))
    draft_resp = make_conexus_response(content="Draft.")
    critique_resp = make_conexus_response(content=_critique_response(7))
    call_idx = [-1]

    async def _ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = _ordered_chat  # type: ignore[method-assign]
    workflow = OntogonyCmsWorkflow(conexus=conexus)
    run = await workflow.run("Normalized", auto_approve=True)

    plan_state = run.state.get("page_plan")
    assert plan_state is not None
    assert plan_state["collection"] == "essays"
    assert plan_state["register"] is None
    assert plan_state["outline"] == ["Keep me", "Also keep"]
    assert plan_state["cites"] == ["docs/a.md", "docs/b.md"]
    assert plan_state["whereNext"] == [
        {"kind": "essay", "slug": "good", "title": "Good", "why": "Why"}
    ]

    cms = run.state.get("cms_output")
    assert cms is not None
    assert '  - "docs/a.md"' in cms
    assert '  - "docs/b.md"' in cms
    assert 'slug: "good"' in cms
    assert 'slug: ""' not in cms
