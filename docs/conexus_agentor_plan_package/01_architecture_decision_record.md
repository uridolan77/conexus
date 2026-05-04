# 01 — Architecture Decision Record

## ADR-001 — Conexus is the first product foundation

**Status:** Accepted

**Decision:** Build Conexus before Agentor/MCP integration.

**Reason:** Conexus has the smallest deployable product surface and already has clear docs. A working gateway gives every later system a stable LLM boundary.

**Consequence:** Agentor, MCP, Aigent, and adaptation orchestration wait until Conexus can serve real requests and record usage.

---

## ADR-002 — Use Python/FastAPI for Conexus v1

**Status:** Accepted

**Decision:** Implement Conexus v1 in Python/FastAPI.

**Reason:** KGB already contains Python LLM routers, failover, pricing, typed contracts, and tests. A .NET rewrite would discard the most reusable code.

**Consequence:** Older .NET LLMGateway informs design but is not the implementation base.

---

## ADR-003 — Extract KGB behavior, not KGB architecture

**Status:** Accepted

**Decision:** Extract provider adapters, pricing, normalized usage, errors, and tests from KGB. Do not import KG pipeline concepts.

**Keep:**

```text
provider calls
provider adapters
fallback behavior
typed messages/usage
pricing
streaming setup
error taxonomy
tests
```

**Reject:**

```text
corpus
chunk
ontology
stage extraction
KG nodes/edges
DAG orchestrator
KGB semantic cache
KGB BudgetContext
KGB Celery assumptions
```

---

## ADR-004 — Conexus owns provider calls

**Status:** Accepted

**Decision:** No Agentor node should call OpenAI/Anthropic directly. Agentor calls Conexus.

**Reason:** Provider keys, usage, cost, fallback, routing, and audit logs must be centralized.

---

## ADR-005 — MCP is a tool boundary, not the LLM gateway

**Status:** Accepted

**Decision:** MCP servers expose tools/resources/prompts. Conexus remains the LLM provider gateway.

**Reason:** MCP is a capability protocol. LLM gateway concerns are different: auth, model routing, provider fallback, cost, logs, billing.

---

## ADR-006 — MCProToCall is useful later, not now

**Status:** Accepted

**Decision:** Keep MCProToCall for future .NET MCP servers, especially ProgressPlay/schema/database tools. Do not wire it into Conexus v1.

---

## ADR-007 — Agentor v0 is minimal

**Status:** Accepted

**Decision:** Rebuild Agentor as a small orchestrator once Conexus works.

Minimal Agentor v0 should include:

```text
GraphState
NodeExecutor
ConexusClient
McpToolClient
HumanApprovalCheckpoint
RunLog
```

Not included in v0:

```text
RL agents
large memory systems
multi-agent market/consensus algorithms
A2A
self-adaptation
semantic layer generation
```

---

## ADR-008 — First integration target is Ontogony CMS

**Status:** Accepted

**Decision:** The first Agentor workflow should produce/review Astro/Tina-compatible Ontogony CMS content.

**Reason:** It is personal, useful, publishable, and already has a real repo with build/audit scripts.
