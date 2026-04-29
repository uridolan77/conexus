# 01 — KGB Reuse Plan

Conexus should start by extracting and simplifying the existing KGB LLM layer.

## Source repo

```text
uridolan77/KGB
```

## Copy/refactor first

| KGB path | Use in Conexus |
|---|---|
| `backend/app/llm/base.py` | Starting point for provider/router interface |
| `backend/app/llm/conexus_router.py` | Main source for failover gateway behavior |
| `backend/app/llm/openai_router.py` | Source for OpenAI calls, retries, usage mapping |
| `backend/app/llm/router.py` | Source for Anthropic calls, retries, cost/token handling |
| `backend/app/llm/pricing.py` | Source for model cost calculation |
| `backend/app/llm/__init__.py` | Source idea for `make_router()` provider factory |
| `docs/specs/CONEXUS.md` | Source spec for Anthropic → OpenAI failover |

## Rewrite while extracting

KGB code is pipeline-oriented. Conexus is gateway-oriented.

Translate:

```text
stage_name              → routing_profile / model_alias
system + user           → OpenAI-compatible messages
BudgetContext           → later budget module
KG pipeline telemetry   → gateway request telemetry
pipeline cost estimate  → request usage/cost record
```

## Keep from KGB

- async provider clients
- retry/failover behavior
- normalized token usage
- pricing helper
- provider factory pattern
- circuit breaker concept
- stream setup ideas
- tests around fallback behavior

## Simplify for v1

For the first deployed gateway:

- one non-streaming endpoint
- OpenAI provider first
- Anthropic second
- request logging before caching
- BO visibility before advanced routing
- database-backed provider config before complex heuristics

## Avoid importing KGB assumptions

Do not bring over:

```text
corpus
chunk
ontology
stage extraction
KG nodes/edges
DAG orchestrator
Celery worker assumptions
semantic cache
Agentor loop
```

Those belong outside the first Conexus core.

## Extraction task

Before coding, create `docs/KGB_EXTRACTION_AUDIT.md` with this table:

| Source file | Functions/classes to reuse | Change needed | New Conexus file |
|---|---|---|---|
