# ADR-0002: Conexus is the single LLM execution boundary

## Status

Accepted.

## Context

Agentor and Athanor both need LLM capabilities. If each service calls providers directly, the system loses control over costs, routing, policy, tracing, prompt versions, and fallback behavior.

## Decision

All normal LLM calls go through Conexus.

Agentor and Athanor must not call provider SDKs directly except in explicitly marked local test fixtures.

## Boundary

```text
Agentor -> Conexus.Client -> Conexus API -> Provider
Athanor -> Conexus.Client -> Conexus API -> Provider
```

## Conexus owns

- provider credentials
- provider adapters
- model aliases (see `backend/static_config/model_aliases.yaml` and gateway router)
- routing and failover between configured providers
- prompt/runtime metadata carried on gateway requests (within supported request shapes)
- request correlation via `X-Conexus-Request-Id` and gateway request logs
- usage and cost accounting (admin/BO surfaces today; public usage-by-id API is not implemented)
- provider error normalization for supported paths
- policy checks enforced in the gateway implementation

## Agentor owns

- task planning
- agent workflows
- tool execution
- human-in-the-loop transitions
- agent state

## Athanor owns

- canonical knowledge state
- provenance
- claim/entity/artifact semantics
- decision reconstruction
- state inspection dashboard

## Consequences

This creates a single source of truth for LLM execution and makes cross-system observability possible.
