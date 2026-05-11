# ADR-0001: Keep Conexus Python/FastAPI for v1 and make it contract-first

## Status

Accepted.

## Context

Conexus is the LLM router/gateway. Agentor and Athanor are .NET systems. It is tempting to rebuild Conexus in .NET to align the stack, but doing so before v1 would duplicate work and slow delivery.

The gateway layer is where provider SDKs, model APIs, routing rules, eval hooks, fallback behavior, prompt formats, streaming behavior, and inference-specific libraries change rapidly. Python remains the lower-friction environment for this layer.

## Decision

Conexus remains implemented in Python/FastAPI for v1.

The boundary between Conexus and .NET systems is defined by OpenAPI and JSON Schema contracts checked into this repository under `contracts/`.

A typed .NET client (`src/dotnet/Conexus.Client`) tracks the **implemented** public gateway surface (health + OpenAI-compatible chat). It intentionally does not pretend unsupported endpoints exist.

## Consequences

Positive:

- Faster path to working v1.
- No duplicate gateway logic.
- Provider churn is isolated in one service.
- .NET systems get typed ergonomics for the stable subset.
- Contract tests can protect the boundary.

Negative:

- One additional runtime must be deployed.
- Some cross-repo coordination is required.
- DTO drift must be controlled through contract-first discipline.

## Revisit criteria

Reconsider a .NET Conexus only if:

- v1 is stable and deployed;
- the API contract is boring and stable;
- Python ops become a proven burden;
- gateway performance bottlenecks are proven to be Python-related;
- enterprise deployment requires single-runtime .NET.
