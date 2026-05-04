# 00 — Repo Research Report

## Research method

The repos were inspected through the GitHub connector using repository metadata, commit history, known file fetches, and code/document snippets. I did not clone and execute the repositories locally. The conclusions below are based on accessible source files, commit diffs, README files, docs, and repo metadata.

## Repo role matrix

| Repo | Observed state | Best role | Build priority |
|---|---|---|---|
| `conexus` | Small, documentation-first repo; already defines a practical gateway+BO plan and says to extract KGB LLM code | Main product foundation | 1 |
| `KGB` | Mature Python/FastAPI-ish backend with LLM routers, provider failover, pricing, typed contracts, tests | Primary extraction source | 1 |
| `LLMGateway` | Older .NET gateway with auth, analytics, token usage, users, smart routers | Design reference for auth/BO/analytics, not code base | 2 |
| `agentor` | Python framework-style repo with broad memory/learning/routing/resilience/coordination claims | Concept archive; later minimal runtime extraction | 3 |
| `Aigent` | C# agent framework attempt with lifecycle, BDI, message bus, memory config, safety settings | Concept archive; not active foundation | 3 |
| `MCProToCall` | C# MCP implementation with Core/Server/Client/Extensions, JSON-RPC, TLS/JWT/RBAC/schema validation | Future .NET MCP/tool-layer asset | 4 |
| `MCPServer` | Older data-transfer/schema API, SQL schema extraction, mappings, migration/validation | Reuse ideas only; superseded by MCProToCall for MCP | 4 |
| `AutoResearch` | Agentic code-research scaffold: FastAPI, Celery, Git worktrees, proposer/judge, encrypted secrets | Reuse patterns later for evaluator/HITL/code-change loops | 5 |
| `ontogony-site` | Astro/TinaCMS site with build/audit scripts | First real Agentor workflow target | 2 |
| `conexus.adaptation` | Final specification for adapter-profile orchestration, drift, evals, security probes | v2/v3 roadmap, not v1 | Later |
| `al.floys` | Vite/React/TypeScript artificial-life playground | Separate product; avoid coupling | Separate |

## Major finding

The repo ecosystem already contains the correct architectural split, but it is scattered:

```text
Conexus = gateway / BO / providers / usage / keys
Agentor = workflow orchestration / agents / HITL / state
MCP/MCProToCall = tool boundary / external capabilities
KGB = current source of reusable gateway code
Ontogony-site = first practical product target
```

The mistake to avoid is merging everything into one giant framework. Conexus should not become Agentor, and Agentor should not own provider calls. MCP should not become the LLM gateway.

## Conexus

`conexus` is the cleanest repo direction. Its docs already say:

- Build Conexus as a small deployed product.
- Extract useful LLM gateway code from KGB.
- First checkpoint: `/v1/chat/completions → provider call → normalized response → DB log → visible in BO`.
- Use Python/FastAPI because KGB reusable code is Python.
- Use Next.js for BO and PostgreSQL for persistence.

Assessment: **correct strategic foundation**. The repo is small enough to build properly instead of refactoring a sprawling codebase.

## KGB

KGB contains the concrete implementation material Conexus needs:

- `backend/app/llm/base.py` — base async router/provider contract.
- `backend/app/llm/openai_router.py` — OpenAI async call, retry, usage mapping, streaming.
- `backend/app/llm/router.py` — Anthropic async call, retry, usage mapping, streaming.
- `backend/app/llm/conexus_router.py` — multi-provider failover gateway, token normalization, agent call support.
- `backend/app/llm/pricing.py` + `static_config/pricing.yaml` — centralized pricing.
- `backend/app/llm/conexus_types.py` — `Message`, `TokenUsage`, `ToolCall`, `AgentResponse`.
- `backend/app/llm/conexus_format.py` — OpenAI-format ↔ Anthropic-format conversion.
- `backend/app/api/errors.py` — stable domain error hierarchy.
- `backend/tests/unit/test_conexus_router_semantic.py` — useful behavior tests.

Assessment: **extract behavior, not KGB assumptions**. KGB is pipeline/KG-oriented; Conexus must become gateway-oriented.

## LLMGateway

The older `.NET LLMGateway` contains useful ideas:

- admin auth and JWT refresh-token pattern
- users/admin controllers
- token usage analytics
- routing abstractions such as cost/latency/content routing
- background reports and provider health checks

Assessment: **design reference only**. Do not restart Conexus in .NET now; that would discard reusable Python KGB code and slow the first deployable milestone.

## Agentor

`agentor` appears to be an ambitious Python agent framework with memory systems, RL/learning agents, routing, tools, resilience, caching, observability, and coordination patterns. It is conceptually rich but too broad for the immediate product.

Assessment: **do not revive as monolith**. Later extract a tiny orchestrator runtime:

```text
AgentRun
GraphState
NodeExecutor
ToolCall
HumanApprovalCheckpoint
ConexusClient
McpClient
```

## Aigent

`Aigent` is a C# agent framework attempt. It includes agent lifecycle, BDI vocabulary, action/result/environment abstractions, in-memory message bus, memory backend config, API/rate-limit config, and safety settings.

Assessment: **concept archive**. Useful for naming and domain concepts, not for implementation now. It overlaps with Agentor.

## MCProToCall

`MCProToCall` is a proper MCP candidate. It has a C# solution with Core/Server/Client/Extensions and BasicServer/BasicClient samples. It claims JSON-RPC 2.0, TLS, JWT, RBAC, schema validation, rate limiting, and structured logging.

Assessment: **future tool-server foundation**, especially for .NET/ProgressPlay/database tooling. It should not be embedded into Conexus core.

## MCPServer

`MCPServer` appears older and more application-specific. The inspected code around data transfer exposes controllers for connections, schema extraction, mappings, migrations, validation, and SQL Server schema reads.

Assessment: **reuse schema-extraction ideas only**. The actual MCP foundation should be MCProToCall or a modern SDK-based server.

## AutoResearch

`AutoResearch` has useful patterns:

- Git worktree per experiment
- proposer/judge model separation
- encrypted secret store
- evaluator abstraction
- FastAPI health
- Celery/Redis worker setup
- run/session/experiment models

Assessment: **future evaluator/HITL pattern source**, useful when Agentor begins editing code/content and needs review/approval loops.

## Ontogony-site

`ontogony-site` is the best first integration target. It uses Astro + TinaCMS and has audit/build scripts.

Assessment: **first Agentor product slice target**. Build Conexus first, then create an Agentor workflow that drafts/reviews/formats Ontogony CMS content.
