# 00 — Start Here

This is the practical build guide for Conexus.

## Product

Conexus is an LLM gateway with a back-office.

It should handle:

```text
projects
API keys
LLM providers
model routing
request logs
usage/cost tracking
provider errors
basic monitoring
```

## First implementation path

Use KGB as the source of existing LLM code.

KGB already has:

- a base LLM router interface
- OpenAI router
- Anthropic router
- Conexus router with failover
- pricing helper
- provider selection via `make_router()`
- telemetry/circuit-breaker ideas

The new repo should turn those into a clean standalone service.

## Stack recommendation

Because KGB’s reusable code is Python, the fastest v1 is:

```text
Backend: FastAPI
Frontend BO: Next.js
Database: PostgreSQL
Deployment: Docker + managed Postgres
Monitoring: structured logs first, OpenTelemetry next
```

A .NET rewrite is possible later, but it would throw away useful KGB code now.

## Done means

A milestone is done when it:

- runs locally
- is deployed
- has a smoke test
- logs useful information
- is visible in the BO when relevant
