# Agentor

> **Status: experimental spike — blocked on Conexus M4.**
> Do not integrate into production workflows until `POST /v1/chat/completions` is
> fully deployed and project API key auth is working (Conexus milestone M4/M5).

Minimal workflow orchestrator that calls Conexus for LLM inference.

## Scope

Agentor is **not** a general agent framework. It is a thin orchestration layer for
structured multi-node workflows whose LLM calls are routed through Conexus.

### Core objects

- `AgentRun` — a running or completed workflow instance
- `GraphState` — mutable shared state passed between nodes
- `GraphNode` — a named step with an async handler
- `NodeExecutor` — runs nodes sequentially, manages state transitions
- `HumanApprovalCheckpoint` — pauses execution until approved/rejected
- `ConexusClient` — async HTTP client for `/v1/chat/completions`
- `ToolClient` — abstract base for external tool access
- `RunLogService` — append-only in-memory log of node outcomes

## First workflow: Ontogony CMS page generation

1. `PlanPageNode` — produces title, thesis, outline
2. `GatherSourcesNode` — reads provided source files via tool client
3. `WriteDraftNode` — calls Conexus to write draft
4. `CritiqueDraftNode` — calls Conexus as critic, scores draft
5. `FormatCmsNode` — formats to Astro/Tina markdown+frontmatter
6. `ApprovalNode` — human approval gate before writing/PR

## Usage

```python
import asyncio
from agentor_runtime.clients.conexus import ConexusClient
from agentor_runtime.workflows.ontogony_cms import OntogonyCmsWorkflow

async def main():
    async with ConexusClient(base_url="http://localhost:8000", api_key="cx_...") as client:
        workflow = OntogonyCmsWorkflow(conexus=client)
        run = await workflow.run(topic="Why Astro is fast")
        # No files are written automatically. The run pauses at an approval gate.
        # If approved, you can resume and then write `cms_output` to `target_path`.
        print(run.status)
        print(run.state.get("target_path"))
        print(run.state.get("cms_output"))

asyncio.run(main())
```

## Notes

- **Conexus dependency**: Agentor expects Conexus to expose `POST /v1/chat/completions`.
- **Safety**: Agentor does **not** write files before human approval. It only produces
  `run.state["cms_output"]` and `run.state["target_path"]`.
  Writing to disk / opening PRs is intentionally deferred to v0.2.
