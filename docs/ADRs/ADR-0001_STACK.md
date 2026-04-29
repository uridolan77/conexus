# ADR-0001 — Stack Choice

## Status

Proposed

## Decision

Use Python/FastAPI for Conexus v1 backend because KGB already contains reusable Python LLM gateway code.

Use Next.js for the BO.

Use PostgreSQL for the database.

## Reason

The fastest path to a working deployed Conexus is to extract/refactor KGB’s existing LLM layer:

```text
BaseLLMRouter
ConexusRouter
OpenAIRouter
Anthropic router
pricing helper
provider factory
fallback behavior
```

A .NET rewrite may be considered later, but it should not block the first working gateway.

## Consequence

Conexus v1 prioritizes speed, reuse, and deployment over stack familiarity.
