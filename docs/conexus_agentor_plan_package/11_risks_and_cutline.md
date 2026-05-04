# 11 — Risks and Cutline

## Highest risks

### 1. Framework accumulation

The repo ecosystem already has several partial frameworks: Agentor, Aigent, LLMGateway, MCPServer, MCProToCall, Conexus.Adaptation. The danger is combining all of them before anything ships.

Mitigation:

```text
Conexus first
one endpoint first
one BO view first
one Agentor workflow first
```

### 2. Importing KGB pipeline assumptions

KGB's LLM layer is valuable, but much of it is tied to corpus/chunk/ontology/stage extraction concerns.

Mitigation:

```text
extract provider behavior only
replace stage_name with model_alias/routing_profile
ban imports from app.pipeline/app.corpus/app.ontology
```

### 3. Stack thrash

There are Python and .NET versions of similar ideas. Switching Conexus to .NET would slow v1 because KGB's reusable LLM code is Python.

Mitigation:

```text
Conexus v1 = Python/FastAPI
MCProToCall = .NET tool server later
LLMGateway = design reference only
```

### 4. MCP too early

MCP is useful, but adding it before Conexus works creates protocol overhead with no stable LLM boundary.

Mitigation:

```text
Conexus M0-M6 first
then Agentor v0
then MCP tools
```

### 5. BO postponed too long

If BO visibility comes too late, the gateway becomes hard to debug and less product-like.

Mitigation:

```text
Requests table by M6
Request detail early
Provider/test pages soon after
```

## Hard cutline: not in Conexus v1

```text
semantic cache
prompt registry
adaptation profiles
A2A
multi-agent marketplace
agent memory
RL/PPO/DQN agents
full MCP registry
full billing
multi-tenant org complexity beyond simple org/project
streaming, unless non-streaming works first
```

## Hard cutline: not from KGB

```text
corpus
chunk
ontology
KG nodes/edges
DAG extraction pipeline
stage extraction names as core concepts
KGB semantic cache
KGB BudgetContext
KGB Celery workers
node mutation services
```

## Hard cutline: not from Aigent/Agentor

```text
BDI runtime
learning agents
utility/market/consensus systems
large memory systems
complex plugin lifecycle
message bus until needed
```

## What success looks like in two weeks of focused work

```text
Conexus backend boots
OpenAI/Anthropic adapters tested
pricing works
fallback service tested
/v1/chat/completions works with mock provider
request logging designed or partially implemented
```

## What success looks like after first full vertical slice

```text
curl calls Conexus
Conexus calls real provider
request appears in BO
usage/cost visible
Agentor calls Conexus for one Ontogony draft workflow
human approves before writing
Ontogony build/check runs
```
