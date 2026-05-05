from __future__ import annotations

import asyncio
import os

from agentor_runtime.clients.conexus import ConexusClient
from agentor_runtime.executor import NodeExecutor
from agentor_runtime.workflows.ontogony_cms import OntogonyCmsWorkflow


async def main() -> None:
    base_url = os.environ.get("CONEXUS_BASE_URL", "http://localhost:8000")
    api_key = os.environ.get("CONEXUS_API_KEY", "")
    if not api_key:
        raise RuntimeError("Set CONEXUS_API_KEY to run against a real Conexus instance.")

    async with ConexusClient(base_url=base_url, api_key=api_key) as client:
        workflow = OntogonyCmsWorkflow(conexus=client)

        run = await workflow.run(
            topic="Why Astro is fast",
            source_paths=[],
            auto_approve=False,
        )
        print("Status:", run.status)
        print("Target path:", run.state.get("target_path"))

        if run.status.value == "awaiting_approval":
            # Human decision happens out-of-band. This is an example:
            run.checkpoint.approve(note="ok to proceed")

            # Resume after approval using the workflow's executor.
            # (Workflow currently doesn't expose resume; use the executor directly.)
            executor: NodeExecutor = workflow._executor  # type: ignore[attr-defined]
            await executor.resume(run)

        print("Final status:", run.status)
        print(run.state.get("cms_output"))


if __name__ == "__main__":
    asyncio.run(main())

