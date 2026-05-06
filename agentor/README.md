# Agentor

Minimal workflow orchestrator that routes LLM work through **Conexus** (`POST /v1/chat/completions`).

**Status:** v0.1 foundation — suitable for experiments and CMS draft generation. File writes and PR automation stay deferred to v0.2.

## Scope

Agentor is **not** a general agent framework. It is a thin orchestration layer for structured multi-node workflows whose LLM calls go through Conexus.

### Core objects

- `AgentRun` — a running or completed workflow instance
- `GraphState` — mutable shared state passed between nodes
- `GraphNode` — a named step with an async handler
- `NodeExecutor` — runs nodes sequentially, manages state transitions
- `HumanApprovalCheckpoint` — pauses execution until approved/rejected
- `ConexusClient` — async HTTP client for `/v1/chat/completions`
- `MockConexusClient` — in-memory canned responses (tests & local demos)
- `ToolClient` — abstract base for external tool access
- `RunLogService` — append-only in-memory log of node outcomes

## First workflow: Ontogony CMS page generation

1. **PlanPageNode** — Conexus returns JSON: title, slug, summary, thesis, register, outline, cites, `whereNext`
2. **GatherSourcesNode** — reads optional source files via the tool client
3. **WriteDraftNode** — Conexus produces draft markdown
4. **CritiqueDraftNode** — Conexus returns critic JSON (scores, notes, approval flag)
5. **FormatCmsNode** — YAML frontmatter + body; `target_path` = `src/content/essays/{slug}.mdx`
6. **ApprovalNode** — human checkpoint before any external write

### Collection naming (essay vs essays)

- **Content type** (and `whereNext[].kind`): singular labels such as `essay`, `concept`.
- **Astro content folder / plan field `collection`:** `essays` (plural), i.e. `src/content/essays/`. The workflow normalizes the planner field to `essays`.

### `whereNext` validation

Each list item must be an object with non-empty string **`kind`** and **`slug`**. Optional `title` and `why`. Rows that are not objects, or lack valid `kind`/`slug`, are **dropped** during normalization (they never reach frontmatter).

## Usage

### Real Conexus

```python
import asyncio
from agentor_runtime.clients.conexus import ConexusClient
from agentor_runtime.workflows.ontogony_cms import OntogonyCmsWorkflow

async def main():
    async with ConexusClient(base_url="http://localhost:8000", api_key="cx_...") as client:
        workflow = OntogonyCmsWorkflow(conexus=client)
        run = await workflow.run(topic="Why Astro is fast")
        # No files are written automatically. The run pauses at an approval gate.
        # If approved, resume and then write `cms_output` to `target_path` yourself.
        print(run.status)
        print(run.state.get("target_path"))
        print(run.state.get("cms_output"))

asyncio.run(main())
```

### Mock Conexus (no server)

```bash
cd agentor
python examples/run_ontogony_cms_mock.py
```

Requires no `CONEXUS_API_KEY`. Uses `MockConexusClient` with fixed JSON/plan/draft/critique responses.

## Notes

- **Conexus dependency:** Conexus must expose `POST /v1/chat/completions` with a project API key when using `ConexusClient`.
- **Safety:** Agentor does **not** write files before human approval. It only produces `run.state["cms_output"]` and `run.state["target_path"]`.
