# 04 — Milestones and Backlog

## Milestone policy

Each milestone must be deployable or at least locally runnable. Do not start a broad framework feature until the current vertical slice works.

## M0 — Conexus repo boots

### Deliverables

```text
FastAPI backend
/health
/health/ready
basic config
pytest setup
ruff/mypy config
Dockerfile
docker-compose with Postgres
```

### Acceptance

```text
backend starts locally
GET /health returns ok
GET /health/ready checks DB or reports degraded cleanly
pytest passes
```

---

## M1 — Extract typed LLM core

### Deliverables

```text
llm/types.py
llm/pricing.py
static_config/pricing.yaml
core/errors.py
unit tests for pricing and errors
```

### Acceptance

```text
pricing YAML loads
pricing override works
unknown model falls back conservatively
GatewayError serializes to stable envelope
```

---

## M2 — Provider adapters

### Deliverables

```text
BaseProviderAdapter
OpenAIAdapter
AnthropicAdapter
ProviderRequest
ProviderResponse
ProviderError
```

### Acceptance

```text
mock OpenAI response maps to ProviderResponse
mock Anthropic response maps to ProviderResponse
token usage normalized
client close methods are called
provider errors are classified
```

---

## M3 — Fallback gateway service

### Deliverables

```text
GatewayService
FallbackPolicy
ProviderFactory
RoutingProfile config
```

### Acceptance

```text
primary success returns without fallback
primary retryable failure falls back
non-retryable validation error does not fall back
both fail raises GatewayError
fallback_used is tracked in service result
```

---

## M4 — `/v1/chat/completions`

### Deliverables

```text
OpenAI-compatible request schema
OpenAI-compatible response schema
POST /v1/chat/completions
simple bearer API key placeholder
```

### Acceptance

```text
curl returns model response via mocked provider or real provider when key exists
invalid messages return 422
provider failure returns sanitized 502
```

---

## M5 — Persistence and project API keys

### Deliverables

```text
projects
project_api_keys
llm_providers
llm_models/gateway_model_aliases
gateway_requests
usage_events
audit_logs
API key generation/hash/revoke
```

### Acceptance

```text
project API key authenticates request
revoked key fails
request log exists on success
request log exists on failure
usage/cost stored
```

---

## M6 — BO shell and request visibility

### Deliverables

```text
Next.js shell
Login placeholder/admin auth
Dashboard
Requests table
Request detail
Providers page stub
Projects page stub
```

### Acceptance

```text
BO loads
requests visible after API call
request detail shows provider/model/tokens/cost/status/fallback/error
```

---

## M7 — Provider management

### Deliverables

```text
add provider key
encrypt provider secret
test provider
enable/disable provider
rotate key later placeholder
```

### Acceptance

```text
saved key is never returned
provider test result visible
provider can be disabled
```

---

## M8 — Agentor minimal runtime

Only after M0-M6 are working.

### Deliverables

```text
AgentRun model
GraphState
NodeExecutor
ConexusClient
McpClient abstraction
HumanApprovalCheckpoint
RunLog
```

### Acceptance

```text
one hardcoded 3-node workflow executes
writer node calls Conexus
critic node calls Conexus
human approval can stop before write
```

---

## M9 — Ontogony CMS workflow

### Deliverables

```text
Ontogony source reader tool
Page planner node
Writer node
Critic node
CMS formatter node
Build/audit runner tool
Draft/PR output
```

### Acceptance

```text
given a topic, workflow produces CMS-ready content
critic score is shown
no file is written without approval
ontogony build/check command is run before PR/write
```

---

## M10 — MCP tool layer

### Deliverables

```text
MCP server for repo/filesystem tools
later MCProToCall .NET MCP server for database/schema tools
permissions and audit logs
tool result schemas
```

### Acceptance

```text
Agentor can call at least read-only MCP tools
write/destructive tools require approval
all tool calls are logged
```

## Backlog categories

### Near-term

- streaming endpoint
- provider fallback policies in DB
- provider health checks
- request filters in BO
- request replay in BO
- cost dashboard

### Later

- model alias editor
- budget policies
- semantic cache
- prompt/template registry
- eval harness
- Agentor memory
- MCP registry
- A2A protocol
- Conexus.Adaptation profile lifecycle

### Explicitly postponed

- A2A
- full multi-agent marketplace/consensus
- RL agents
- self-training/adaptation
- complex vector memory
- broad enterprise platform features
