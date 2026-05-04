# 10 — Agentor, MCP, Aigent, and MCProToCall Integration

## Integration timing

Do not start Agentor/MCP integration until Conexus can:

```text
receive /v1/chat/completions
call provider
record request
record usage/cost
show request in BO
```

That is the boundary that prevents another unfinished framework.

## Agentor v0 scope

Agentor v0 is not the old `agentor` repo wholesale. It is a minimal orchestrator.

### Core objects

```python
@dataclass
class AgentRun:
    id: str
    workflow_name: str
    status: str
    state: dict

@dataclass
class GraphNode:
    id: str
    name: str
    handler: Callable

@dataclass
class HumanApprovalCheckpoint:
    prompt: str
    proposed_action: dict
    approved: bool | None
```

### Runtime services

```text
ConexusClient
ToolClient / McpClient
RunLogService
CheckpointService
```

## First workflow: Ontogony CMS page generation

### Nodes

1. `PlanPageNode`
   - Input: topic/brief
   - Output: title, thesis, outline, target page type

2. `GatherSourcesNode`
   - Uses tool client to read/search Ontogony notes/content
   - Output: source bundle with paths and excerpts

3. `WriteDraftNode`
   - Calls Conexus
   - Output: draft article

4. `CritiqueDraftNode`
   - Calls Conexus as critic
   - Output: score and revision notes

5. `ReviseDraftNode`
   - Optional if score below threshold

6. `FormatCmsNode`
   - Output: Astro/Tina markdown/frontmatter

7. `ApprovalNode`
   - Human must approve before write/PR

8. `WriteOrPrNode`
   - Tool call to write draft or create PR

## How old `agentor` contributes

Use as concept source for:

```text
async lifecycle
agent input/output contracts
tool registration/execution
routing ideas
logging/resilience ideas
memory as later plugin
```

Do not copy:

```text
RL agents
PPO/DQN
market/consensus coordination
large memory subsystems
semantic router unless needed
full plugin framework
```

## How `Aigent` contributes

Use as naming/domain source for:

```text
IAgent lifecycle
IAction / ActionResult
EnvironmentState
AgentCapabilities
message bus abstraction
safety settings
BDI vocabulary
```

Do not copy into current stack. It is C# and overlaps with Agentor.

## How `MCProToCall` contributes

`MCProToCall` is the best candidate for a future .NET MCP tool layer.

Use for:

```text
ProgressPlay SQL/schema tools
secure enterprise tool servers
JSON-RPC client/server pattern
TLS/JWT/RBAC ideas
schema validation
rate limiting
```

Do not put it inside Conexus core.

## MCP tool categories

### Ontogony tools

```text
read_content_file(path)
search_content(query)
write_draft(path, content)
run_check()
create_pr(branch, title, body)
```

### GitHub/repo tools

```text
list_files(repo, path)
read_file(repo, path)
create_branch(repo, name)
commit_file(repo, path, content)
open_pr(repo, branch, title, body)
```

### SQL/schema tools

```text
list_connections()
extract_schema(connection_id)
sample_table(connection_id, table, limit)
compare_schema_to_slod(schema_id)
```

### Safety gates

| Tool type | Auto-run? | Approval? |
|---|---:|---:|
| read/search | yes | no |
| run build/check | yes, if sandboxed | maybe |
| write draft | no | yes |
| create branch/PR | no | yes |
| database schema read | yes, if allowlisted | no/yes depending source |
| database data read | no by default | yes |
| delete/mutate | no | always |

## A2A position

A2A is not needed yet.

Use A2A only when there are multiple independently deployed agents that must communicate across framework/runtime boundaries. Until then, direct Agentor graph nodes are simpler and more debuggable.
