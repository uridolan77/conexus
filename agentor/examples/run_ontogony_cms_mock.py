"""Run OntogonyCmsWorkflow end-to-end with a mock Conexus (no server, no API key).

Use this to inspect ``cms_output`` and ``target_path`` without calling a real gateway.
"""

from __future__ import annotations

import asyncio
import json

from agentor_runtime.clients.mock_conexus import MockConexusClient, make_conexus_response
from agentor_runtime.models import RunStatus
from agentor_runtime.workflows.ontogony_cms import OntogonyCmsWorkflow


def _plan_json() -> str:
    return json.dumps(
        {
            "collection": "essays",
            "title": "Why Astro is fast",
            "slug": "why-astro-is-fast",
            "summary": "Astro ships zero JS by default.",
            "thesis": "Astro ships zero JS by default.",
            "register": "R2",
            "outline": ["Islands architecture", "Static-first"],
            "cites": ["docs/astro.md"],
            "whereNext": [
                {
                    "kind": "essay",
                    "slug": "static-site-generation",
                    "title": "SSG",
                    "why": "Natural follow-on",
                }
            ],
        }
    )


def _critique_json() -> str:
    return json.dumps(
        {
            "clarity": 8,
            "rigor": 8,
            "hallucination_risk": 2,
            "style_fit": 8,
            "overall": 8,
            "blocking_issues": [],
            "revision_notes": ["Good structure"],
            "approved_for_human_review": True,
        }
    )


async def main() -> None:
    conexus = MockConexusClient()
    plan_resp = make_conexus_response(content=_plan_json(), model="conexus-smart")
    draft_resp = make_conexus_response(
        content="# Why Astro is fast\n\nAstro ships zero JS by default.\n",
        model="conexus-smart",
    )
    critique_resp = make_conexus_response(content=_critique_json(), model="conexus-fast")

    call_idx = [-1]

    async def ordered_chat(model, messages, **kwargs):
        call_idx[0] += 1
        responses = [plan_resp, draft_resp, critique_resp]
        if call_idx[0] < len(responses):
            return responses[call_idx[0]]
        return make_conexus_response()

    conexus.chat = ordered_chat  # type: ignore[method-assign]

    workflow = OntogonyCmsWorkflow(conexus=conexus)
    run = await workflow.run("Why Astro is fast", auto_approve=True)

    assert run.status == RunStatus.COMPLETED
    print("status:", run.status.value)
    print("target_path:", run.state.get("target_path"))
    print("--- cms_output (first 1200 chars) ---")
    out = run.state.get("cms_output") or ""
    print(out[:1200])
    if len(out) > 1200:
        print(f"... ({len(out) - 1200} more chars)")


if __name__ == "__main__":
    asyncio.run(main())
