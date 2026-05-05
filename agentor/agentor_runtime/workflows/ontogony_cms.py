"""Ontogony CMS page-generation workflow.

Nodes:
    1. PlanPageNode      — Conexus JSON plan (collection, title, slug, summary, thesis,
                           register, outline, cites, whereNext)
    2. GatherSourcesNode — ``read_source_file`` per path; ``source_bundle`` + ``source_manifest``
    3. WriteDraftNode    — Conexus draft markdown
    4. CritiqueDraftNode — Conexus JSON critique (clarity, rigor, hallucination_risk, style_fit,
                           overall, blocking_issues, revision_notes, approved_for_human_review)
    5. FormatCmsNode     — essay frontmatter (YAML) + body; ``target_path`` under ``src/content/essays/``
    6. ApprovalNode      — :class:`~agentor_runtime.models.HumanApprovalCheckpoint` before any write

State keys (main):
    topic, source_paths (in)
    page_plan, source_bundle, source_manifest, draft, critique, target_path, cms_output (out)

Convention: ``page_plan["collection"]`` is ``"essays"`` (plural), matching Astro content dir
``src/content/essays/``. Singular "essay" in docs refers to the content type, not this field.
"""
from __future__ import annotations

import re
import json
import textwrap
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from agentor_runtime.clients.tool import ToolClient, StubToolClient
from agentor_runtime.executor import NodeExecutor
from agentor_runtime.models import AgentRun, GraphNode, GraphState, HumanApprovalCheckpoint

if TYPE_CHECKING:
    from agentor_runtime.clients.conexus import ConexusClient

_WRITER_MODEL = "conexus-smart"
_CRITIC_MODEL = "conexus-fast"

# Plural matches ``src/content/essays/``; do not use singular "essay" here.
_DEFAULT_COLLECTION = "essays"
_VALID_REGISTERS = {"R1", "R2", "R3", "R4"}


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "untitled"


def _estimate_reading_time_minutes(markdown: str, *, wpm: int = 200) -> int:
    # Very rough: count word-like tokens in the markdown.
    words = len(re.findall(r"\b\w+\b", markdown))
    return max(1, (words + wpm - 1) // wpm)


def _where_next_item_valid(item: dict) -> bool:
    kind = item.get("kind")
    slug = item.get("slug")
    return (
        isinstance(kind, str)
        and kind.strip() != ""
        and isinstance(slug, str)
        and slug.strip() != ""
    )


def _normalize_where_next(items: object) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(items, list):
        return normalized

    for item in items:
        if not isinstance(item, dict) or not _where_next_item_valid(item):
            continue

        normalized_item = {
            "kind": str(item["kind"]).strip(),
            "slug": str(item["slug"]).strip(),
        }
        for optional_key in ("title", "why"):
            value = item.get(optional_key)
            if isinstance(value, str) and value.strip():
                normalized_item[optional_key] = value.strip()
        normalized.append(normalized_item)

    return normalized


def _normalize_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def _normalize_page_plan(plan: dict, *, topic: str, raw_fallback: str) -> dict:
    title = str(plan.get("title") or topic)
    slug = str(plan.get("slug") or _slugify(title))
    thesis = str(plan.get("thesis") or raw_fallback)
    summary = str(plan.get("summary") or thesis)[:200]
    register = plan.get("register")

    return {
        "collection": _DEFAULT_COLLECTION,
        "title": title,
        "slug": slug,
        "summary": summary,
        "thesis": thesis,
        "register": register if register in _VALID_REGISTERS else None,
        "outline": _normalize_string_list(plan.get("outline")),
        "cites": _normalize_string_list(plan.get("cites")),
        "whereNext": _normalize_where_next(plan.get("whereNext")),
    }


def _extract_first_json_object(text: str) -> str | None:
    """Best-effort extraction of the first top-level JSON object from text."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_json_response(text: str) -> tuple[dict, str | None]:
    """Parse JSON with progressively more tolerant fallbacks.

    Returns (parsed_dict, warning_or_None). Never raises JSONDecodeError.
    """
    raw = text.strip()
    if not raw:
        return {}, "Empty response"

    try:
        parsed = json.loads(raw)
        return (parsed if isinstance(parsed, dict) else {"value": parsed}), None
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            return (parsed if isinstance(parsed, dict) else {"value": parsed}), "Parsed fenced JSON"
        except json.JSONDecodeError:
            pass

    candidate = _extract_first_json_object(raw)
    if candidate:
        try:
            parsed = json.loads(candidate)
            return (parsed if isinstance(parsed, dict) else {"value": parsed}), "Extracted first JSON object"
        except json.JSONDecodeError:
            pass

    return {"raw": raw}, "Failed to parse JSON; stored raw text"


def _yaml_quote(s: str) -> str:
    # Use double quotes with minimal escaping.
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def dump_frontmatter_yaml(data: dict) -> str:
    """Minimal YAML serializer for safe frontmatter (dict + scalars/lists)."""
    lines: list[str] = ["---"]
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, list) and not value:
            lines.append(f"{key}: []")
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, str):
            lines.append(f"{key}: {_yaml_quote(value)}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, str):
                    lines.append(f"  - {_yaml_quote(item)}")
                elif isinstance(item, dict):
                    # Minimal nested mapping support for list items: each value is scalar-ish.
                    lines.append("  -")
                    for k, v in item.items():
                        if v is None:
                            continue
                        if isinstance(v, bool):
                            vv = "true" if v else "false"
                        elif isinstance(v, (int, float)):
                            vv = str(v)
                        else:
                            vv = _yaml_quote(str(v))
                        lines.append(f"    {k}: {vv}")
                else:
                    lines.append(f"  - {_yaml_quote(str(item))}")
        else:
            lines.append(f"{key}: {_yaml_quote(str(value))}")
    lines.append("---")
    return "\n".join(lines) + "\n"


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
                        "'collection' (string), 'title' (string), 'slug' (string), "
                        "'summary' (string), 'thesis' (string), 'register' (string, optional; use R1-R4), "
                        "'outline' (list of strings), 'cites' (list of strings), "
                        "'whereNext' (list of objects; each MUST have non-empty string "
                        "'kind' (content type, e.g. essay, concept) and 'slug'; optional "
                        "'title', 'why'; invalid entries are ignored). "
                        "Set collection='essays' (Astro folder name under src/content/)."
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
        plan, warn = parse_json_response(response.content)
        if warn:
            state.set("_warnings.plan_page", warn)

        plan = _normalize_page_plan(plan, topic=topic, raw_fallback=response.content)
        state.set("page_plan", plan)

    # ------------------------------------------------------------------ #
    # 2. GatherSourcesNode                                                  #
    # ------------------------------------------------------------------ #
    async def gather_sources(state: GraphState) -> None:
        paths: list[str] = state.get("source_paths") or []
        if not paths:
            state.set("source_bundle", "")
            state.set("source_manifest", [])
            return

        excerpts: list[str] = []
        manifest: list[dict] = []
        for path in paths:
            result = await tool.read_source_file(path)
            if result.ok:
                # Limit each file to 2 000 chars to stay within token budgets
                excerpts.append(f"--- {path} ---\n{result.content[:2000]}")
                manifest.append({"path": path, "ok": True, "error": None})
            else:
                excerpts.append(f"--- {path} (error: {result.error}) ---")
                manifest.append({"path": path, "ok": False, "error": result.error})

        state.set("source_bundle", "\n\n".join(excerpts))
        state.set("source_manifest", manifest)

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
                        "'clarity' (0-10), 'rigor' (0-10), 'hallucination_risk' (0-10), "
                        "'style_fit' (0-10), 'overall' (0-10), "
                        "'blocking_issues' (list of strings), "
                        "'revision_notes' (list of strings), "
                        "'approved_for_human_review' (boolean). "
                        "Be concise and specific."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Thesis: {plan.get('thesis', '')}\n\n"
                        f"Draft:\n{draft}\n\n"
                        "Critique this draft with the schema above. "
                        "Return only valid JSON."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=512,
        )
        critique, warn = parse_json_response(response.content)
        if warn:
            state.set("_warnings.critique_draft", warn)

        critique.setdefault("clarity", None)
        critique.setdefault("rigor", None)
        critique.setdefault("hallucination_risk", None)
        critique.setdefault("style_fit", None)
        critique.setdefault("overall", None)
        critique.setdefault("blocking_issues", [])
        critique.setdefault("revision_notes", [])
        critique.setdefault("approved_for_human_review", False)
        state.set("critique", critique)

    # ------------------------------------------------------------------ #
    # 5. FormatCmsNode                                                      #
    # ------------------------------------------------------------------ #
    async def format_cms(state: GraphState) -> None:
        plan: dict = state.get("page_plan") or {}
        draft: str = state.get("draft") or ""
        normalized_plan = _normalize_page_plan(plan, topic="Untitled", raw_fallback=draft)
        title = normalized_plan["title"]
        summary = str(normalized_plan["summary"])[:280]
        slug = normalized_plan["slug"]
        cites = normalized_plan["cites"]
        register = normalized_plan["register"]
        where_next = normalized_plan["whereNext"]

        now = datetime.now(timezone.utc).isoformat()
        reading_time = _estimate_reading_time_minutes(draft)

        frontmatter_obj = {
            "title": title,
            "summary": summary,
            "status": "draft",
            "register": register,
            "readingTime": reading_time,
            "cites": cites,
            "whereNext": where_next,
            "createdAt": now,
            "updatedAt": now,
        }
        target_path = f"src/content/essays/{slug}.mdx"
        state.set("target_path", target_path)

        frontmatter = dump_frontmatter_yaml(frontmatter_obj)
        state.set("cms_output", frontmatter + "\n" + draft.lstrip())

    # ------------------------------------------------------------------ #
    # 6. ApprovalNode                                                       #
    # ------------------------------------------------------------------ #
    async def approval(state: GraphState) -> None:
        plan: dict = state.get("page_plan") or {}
        critique: dict = state.get("critique") or {}
        title = plan.get("title", "Untitled")
        overall = critique.get("overall", "n/a")
        blocking = critique.get("blocking_issues", []) or []
        notes = critique.get("revision_notes", []) or []
        blocking_text = "\n".join(f"- {n}" for n in blocking) if blocking else "None"
        notes_text = "\n".join(f"- {n}" for n in notes) if notes else "None"

        checkpoint = HumanApprovalCheckpoint(
            prompt=(
                f"Approve publishing '{title}'?\n"
                f"Critic overall: {overall}/10\n"
                f"Blocking issues:\n{blocking_text}\n"
                f"Revision notes:\n{notes_text}"
            ),
            proposed_action={
                "title": title,
                "target_path": state.get("target_path"),
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
    """Orchestrates Ontogony CMS **essay** drafts for Astro/Tina (v0.1).

    Pipeline: plan (JSON) → gather sources → draft markdown → critic JSON →
    frontmatter + body → human approval. Outputs ``cms_output`` and
    ``target_path`` (``src/content/essays/{slug}.mdx``); disk writes and PRs are
    out of scope until v0.2.

    **Naming:** ``page_plan["collection"]`` is always ``"essays"`` (plural),
    matching ``src/content/essays/``. Use ``whereNext[].kind`` for the logical
    content type (e.g. ``"essay"``, ``"concept"``).

    Args:
        conexus: LLM gateway client implementing ``chat`` (e.g. :class:`~agentor_runtime.clients.conexus.ConexusClient` or :class:`~agentor_runtime.clients.mock_conexus.MockConexusClient`).
        tool: Filesystem or stub tool for ``read_source_file``. Defaults to :class:`~agentor_runtime.clients.tool.StubToolClient`.
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
            The :class:`~agentor_runtime.models.AgentRun` (may be ``AWAITING_APPROVAL``).
        """
        run = AgentRun(workflow_name="ontogony_cms")
        run.state.set("topic", topic)
        if source_paths:
            run.state.set("source_paths", source_paths)

        await self._executor.run(run, auto_approve=auto_approve)
        return run

    async def resume(self, run: AgentRun, *, auto_approve: bool = False) -> AgentRun:
        """Continue after :attr:`~agentor_runtime.models.AgentRun.checkpoint` approval/rejection."""
        return await self._executor.resume(run, auto_approve=auto_approve)
