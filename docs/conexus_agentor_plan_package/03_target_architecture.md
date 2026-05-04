# 03 — Target Architecture

## System boundary diagram

```text
+-------------------+        +--------------------+        +----------------------+
| Client Apps       |        | Conexus API         |        | Provider APIs         |
| - KGB             | -----> | - auth              | -----> | - OpenAI              |
| - Agentor         |        | - model routing     |        | - Anthropic           |
| - Ontogony tools  |        | - fallback          |        | - local later         |
| - CMS workflows   |        | - usage/cost logs   |        +----------------------+
+-------------------+        | - BO/admin          |
                             +--------------------+
                                      ^
                                      |
                                      v
                             +--------------------+
                             | PostgreSQL          |
                             | - projects          |
                             | - API keys          |
                             | - providers         |
                             | - requests          |
                             | - usage events      |
                             +--------------------+

+-------------------+        +--------------------+        +----------------------+
| Agentor           | -----> | MCP Tool Servers    | -----> | External capabilities |
| - graph state     |        | - MCProToCall later |        | - GitHub/repos        |
| - node executor   |        | - Python tools now  |        | - Ontogony files      |
| - HITL            |        | - schema tools      |        | - SQL/schema          |
+-------------------+        +--------------------+        +----------------------+
```

## Conexus runtime flow

```text
POST /v1/chat/completions
  ↓
Authenticate project API key
  ↓
Validate request
  ↓
Resolve model alias / routing profile
  ↓
Create gateway_requests row: started
  ↓
Call primary provider adapter
  ↓
If retryable provider error, call fallback provider
  ↓
Normalize response / error
  ↓
Calculate tokens and estimated cost
  ↓
Update gateway_requests row
  ↓
Insert usage_events row
  ↓
Return OpenAI-compatible response
```

## Conexus layers

### API layer

Owns HTTP shape only:

- request validation
- API key auth dependency
- response serialization
- admin routes

### Service layer

Owns business flow:

- route resolution
- gateway request lifecycle
- provider selection
- fallback handling
- usage recording

### Adapter layer

Owns provider-specific SDKs:

- OpenAI request/response mapping
- Anthropic request/response mapping
- provider error classification
- streaming setup later

### Persistence layer

Owns relational facts:

- project identity
- key hash/revocation
- provider config
- request log
- usage event
- audit event

## Agentor boundary

Agentor should not know provider keys, provider pricing, or fallback rules. It should call:

```text
ConexusClient.chat(messages, model_alias="conexus-fast")
```

Agentor owns:

- workflow state
- graph nodes
- tool calls
- human approval
- content/code review loops

## MCP boundary

MCP servers own executable tools and external resources.

Examples:

```text
read_ontogony_file(path)
write_draft_file(path, content)
run_ontogony_build()
extract_sql_schema(connection_id)
search_repo(query)
create_github_pr(branch, title, body)
```

MCP tools should be permissioned and audited. Destructive tools should require human approval.

## First real product slice

```text
Ontogony CMS page generation/review
```

Flow:

```text
User brief
  ↓
Agentor planner
  ↓
MCP source reader
  ↓
Conexus writer call
  ↓
Conexus critic call
  ↓
CMS formatter
  ↓
Human approval
  ↓
MCP write draft / create PR
```
