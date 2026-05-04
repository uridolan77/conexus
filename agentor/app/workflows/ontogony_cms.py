"""Ontogony CMS page-generation workflow.

Nodes:
    1. PlanPageNode      — produces title, thesis, outline
    2. GatherSourcesNode — reads source files via ToolClient
    3. WriteDraftNode    — calls Conexus to write the draft
    4. CritiqueDraftNode — calls Conexus as critic, scores the draft
    5. FormatCmsNode     — formats to Astro/TinaCMS markdown + frontmatter
    6. ApprovalNode      — installs a HumanApprovalCheckpoint before writing

State keys written/consumed:
    topic            (in)  topic brief supplied by the caller
    source_paths     (in)  optional list[str] of file paths to read as context
    page_plan        (out) dict with title, thesis, outline
    source_bundle    (out) str concatenation of source file excerpts
    draft            (out) full article markdown from Conexus
    critique         (out) dict with score (0-10) and notes
    cms_output       (out) frontmatter + markdown ready to write to disk
"""
from __future__ import annotations

import json
import textwrap
from typing import TYPE_CHECKING

from app.clients.tool import ToolClient, StubToolClient
from app.executor import NodeExecutor
from app.models import AgentRun, GraphNode, GraphState, HumanApprovalCheckpoint

if TYPE_CHECKING:
    from app.clients.conexus import ConexusClient

_WRITER_MODEL = "conexus-smart"
_CRITIC_MODEL = "conexus-fast"


def _build_nodes(
    conexus: "ConexusClient",
    tool: ToolClient,
) -> list[GraphNode]:
    # ------------------------------------------------------------------ #
    # 1. PlanPageNode                                                       #
    # ------------------------------------------------------------------ #
    async def plan_page(state: GraphState) -> None:
        topic = state.get("topic", "")
        if not topic:
            raise ValueError("'topic' must be set in GraphState before running")

        response = await conexus.chat(
            model=_WRITER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert content strategist for the Ontogony website. "
                        "Return your answer as JSON with keys: "
                        "'title' (string), 'thesis' (string), 'outline' (list of strings)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Plan a page about: {topic}\n"
                        "Return only valid JSON, no prose."
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=512,
        )
        try:
            plan = json.loads(response.content)
        except json.JSONDecodeError:
            # Tolerate a non-JSON response; wrap it so downstream nodes work
            plan = {"title": topic, "thesis": response.content, "outline": []}
        state.set("page_plan", plan)

    # ------------------------------------------------------------------ #
    # 2. GatherSourcesNode                                                  #
    # ------------------------------------------------------------------ #
    async def gather_sources(state: GraphState) -> None:
        paths: list[str] = state.get("source_paths") or []
        if not paths:
            state.set("source_bundle", "")
            return

        excerpts: list[str] = []
        for path in paths:
            result = await tool.invoke("read_file", path=path)
            if result.ok:
                # Limit each file to 2 000 chars to stay within token budgets
                excerpts.append(f"--- {path} ---\n{result.content[:2000]}")
            else:
                excerpts.append(f"--- {path} (error: {result.error}) ---")

        state.set("source_bundle", "\n\n".join(excerpts))

    # ------------------------------------------------------------------ #
    # 3. WriteDraftNode                                                     #
    # ------------------------------------------------------------------ #
    async def write_draft(state: GraphState) -> None:
        plan: dict = state.get("page_plan") or {}
        source_bundle: str = state.get("source_bundle") or ""

        outline_text = "\n".join(
            f"- {item}" for item in plan.get("outline", [])
        )
        source_section = (
            f"\n\nReference material:\n{source_bundle}" if source_bundle else ""
        )

        response = await conexus.chat(
            model=_WRITER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional technical writer for the Ontogony website. "
                        "Write in clear, engaging markdown. "
                        "Do not include frontmatter — that is added later."
                    ),
                },
                {
                    "role": "user",
                    "content": textwrap.dedent(f"""
                        Write a complete page draft.

                        Title: {plan.get("title", "Untitled")}
                        Thesis: {plan.get("thesis", "")}
                        Outline:
                        {outline_text}
                        {source_section}
                    """).strip(),
                },
            ],
            temperature=0.5,
            max_tokens=2048,
        )
        state.set("draft", response.content)

    # ------------------------------------------------------------------ #
    # 4. CritiqueDraftNode                                                  #
    # ------------------------------------------------------------------ #
    async def critique_draft(state: GraphState) -> None:
        draft: str = state.get("draft") or ""
        plan: dict = state.get("page_plan") or {}

        response = await conexus.chat(
            model=_CRITIC_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a critical editor. "
                        "Return JSON with keys: "
                        "'score' (integer 0-10), 'notes' (list of strings). "
                        "Be concise."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Thesis: {plan.get('thesis', '')}\n\n"
                        f"Draft:\n{draft}\n\n"
                        "Score this draft and list specific revision notes. "
                        "Return only valid JSON."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=512,
        )
        try:
            critique = json.loads(response.content)
        except json.JSONDecodeError:
            critique = {"score": None, "notes": [response.content]}
        state.set("critique", critique)

    # ------------------------------------------------------------------ #
    # 5. FormatCmsNode                                                      #
    # ------------------------------------------------------------------ #
    async def format_cms(state: GraphState) -> None:
        plan: dict = state.get("page_plan") or {}
        draft: str = state.get("draft") or ""
        title = plan.get("title", "Untitled")
        thesis = plan.get("thesis", "")

        frontmatter = textwrap.dedent(f"""\
            ---
            title: "{title}"
            description: "{thesis[:160]}"
            draft: true
            ---
        """)
        state.set("cms_output", frontmatter + "\n" + draft)

    # ------------------------------------------------------------------ #
    # 6. ApprovalNode                                                       #
    # ------------------------------------------------------------------ #
    async def approval(state: GraphState) -> None:
        plan: dict = state.get("page_plan") or {}
        critique: dict = state.get("critique") or {}
        title = plan.get("title", "Untitled")
        score = critique.get("score", "n/a")
        notes = critique.get("notes", [])
        notes_text = "\n".join(f"- {n}" for n in notes) if notes else "None"

        checkpoint = HumanApprovalCheckpoint(
            prompt=(
                f"Approve publishing '{title}'?\n"
                f"Critic score: {score}/10\n"
                f"Notes:\n{notes_text}"
            ),
            proposed_action={
                "title": title,
                "cms_output_preview": (state.get("cms_output") or "")[:500],
            },
        )
        state.set("_checkpoint", checkpoint)

    return [
        GraphNode(id="plan_page", name="PlanPageNode", handler=plan_page),
        GraphNode(id="gather_sources", name="GatherSourcesNode", handler=gather_sources),
        GraphNode(id="write_draft", name="WriteDraftNode", handler=write_draft),
        GraphNode(id="critique_draft", name="CritiqueDraftNode", handler=critique_draft),
        GraphNode(id="format_cms", name="FormatCmsNode", handler=format_cms),
        GraphNode(id="approval", name="ApprovalNode", handler=approval),
    ]


class OntogonyCmsWorkflow:
    """Orchestrates the Ontogony CMS page-generation workflow.

    Args:
        conexus: A :class:`~app.clients.conexus.ConexusClient` instance.
        tool:    A :class:`~app.clients.tool.ToolClient` instance.
                 Defaults to :class:`~app.clients.tool.StubToolClient`.
    """

    def __init__(
        self,
        conexus: "ConexusClient",
        tool: ToolClient | None = None,
    ) -> None:
        self._conexus = conexus
        self._tool = tool or StubToolClient()
        self._nodes = _build_nodes(conexus=self._conexus, tool=self._tool)
        self._executor = NodeExecutor(self._nodes)

    async def run(
        self,
        topic: str,
        *,
        source_paths: list[str] | None = None,
        auto_approve: bool = False,
    ) -> AgentRun:
        """Run the workflow for ``topic``.

        Args:
            topic:        The content topic or brief.
            source_paths: Optional list of local file paths to inject as context.
            auto_approve: Skip human approval gate (useful in tests/CI).

        Returns:
            The completed :class:`~app.models.AgentRun`.
        """
        run = AgentRun(workflow_name="ontogony_cms")
        run.state.set("topic", topic)
        if source_paths:
            run.state.set("source_paths", source_paths)

        await self._executor.run(run, auto_approve=auto_approve)
        return run
